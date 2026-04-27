"""Filesystem-backed storage for notes.

Layout (per note, in ``notes_dir``):
  - ``{slug}_{id}_metadata_{timestamp}``     -- YAML metadata sidecar
  - ``{slug}_{id}_data_{timestamp}.md``      -- Markdown body

This module is the single source of truth for these conventions; nothing
else in the codebase should construct or parse those filenames directly.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

METADATA_MARKER = "_metadata_"
REQUIRED_FIELDS = {
    "id",
    "title",
    "safe_title",
    "tags",
    "creation_date_as_str",
    "note_data_path",
}


class NoteRepositoryError(Exception):
    """Base class for repository errors."""


class NoteNotFoundError(NoteRepositoryError):
    """No note matched the given query."""


class AmbiguousMatchError(NoteRepositoryError):
    """More than one note matched a query that should have been unique."""

    def __init__(self, query: str, candidates: list["NoteRecord"]):
        self.query = query
        self.candidates = candidates
        ids = ", ".join(str(c.id) for c in candidates)
        super().__init__(f"Multiple notes matched {query!r}; candidate ids: {ids}")


class NoteCorruptError(NoteRepositoryError):
    """A metadata file could not be parsed or was missing required keys."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


@dataclass
class NoteRecord:
    """A note loaded from disk."""

    id: int
    title: str
    safe_title: str
    tags: list[str]
    creation_date_as_str: str
    metadata_path: Path
    data_path: Path
    creation_date: datetime | None = None

    def read_body(self) -> str:
        if not self.data_path.exists():
            return ""
        return self.data_path.read_text()

    def to_yaml_dict(self) -> dict:
        """Serialize to the on-disk metadata schema."""
        return {
            "id": self.id,
            "title": self.title,
            "safe_title": self.safe_title,
            "tags": list(self.tags),
            "creation_date": self.creation_date,
            "creation_date_as_str": self.creation_date_as_str,
            "note_metadata_path": str(self.metadata_path),
            "note_data_path": str(self.data_path),
        }


class NoteRepository:
    """Filesystem-backed note repository."""

    def __init__(self, notes_dir: Path):
        self.notes_dir = Path(notes_dir)

    # ------------------------------------------------------------------ paths

    @staticmethod
    def build_paths(
        notes_dir: Path, slug: str, note_id: int, when: datetime
    ) -> tuple[Path, Path]:
        """Return ``(metadata_path, data_path)`` for a new note."""
        ts = when.strftime("%Y-%m-%d_%H_%M_%S")
        metadata_path = notes_dir / f"{slug}_{note_id}{METADATA_MARKER}{ts}"
        data_path = notes_dir / f"{slug}_{note_id}_data_{ts}.md"
        return metadata_path, data_path

    def ensure_dir(self) -> None:
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------- loading

    def _iter_metadata_files(self) -> list[Path]:
        if not self.notes_dir.exists():
            return []
        return sorted(
            f
            for f in self.notes_dir.iterdir()
            if f.is_file() and METADATA_MARKER in f.name
        )

    def _load_record(self, metadata_path: Path) -> NoteRecord:
        try:
            with metadata_path.open("r") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise NoteCorruptError(metadata_path, f"invalid YAML: {exc}") from exc

        if not isinstance(raw, dict):
            raise NoteCorruptError(metadata_path, "metadata is not a YAML mapping")

        missing = REQUIRED_FIELDS - raw.keys()
        if missing:
            raise NoteCorruptError(
                metadata_path, f"missing required fields: {sorted(missing)}"
            )

        return NoteRecord(
            id=raw["id"],
            title=raw["title"],
            safe_title=raw["safe_title"],
            tags=list(raw.get("tags") or []),
            creation_date_as_str=raw["creation_date_as_str"],
            creation_date=raw.get("creation_date"),
            metadata_path=metadata_path,
            data_path=Path(raw["note_data_path"]),
        )

    # ----------------------------------------------------------------- queries

    def list_all(self) -> list[NoteRecord]:
        """Return every readable note. Corrupt notes are skipped with a warning."""
        records: list[NoteRecord] = []
        for path in self._iter_metadata_files():
            try:
                records.append(self._load_record(path))
            except NoteCorruptError as exc:
                print(f"warning: skipping {exc}", file=sys.stderr)
        return records

    def find_by_id(self, note_id: int) -> NoteRecord | None:
        for record in self.list_all():
            if record.id == note_id:
                return record
        return None

    def find_by_slug(self, slug: str) -> list[NoteRecord]:
        return [r for r in self.list_all() if r.safe_title == slug]

    def find_by_title(self, title: str) -> list[NoteRecord]:
        return [r for r in self.list_all() if r.title == title]

    def resolve_one(
        self,
        *,
        note_id: int | None = None,
        slug: str | None = None,
        title: str | None = None,
    ) -> NoteRecord:
        """Resolve a single note by id, slug, or title.

        Raises NoteNotFoundError if nothing matches and AmbiguousMatchError if
        slug/title matches more than one note.
        """
        if note_id:
            found = self.find_by_id(note_id)
            if not found:
                raise NoteNotFoundError(f"no note with id {note_id}")
            return found

        if slug:
            matches = self.find_by_slug(slug)
            if not matches:
                raise NoteNotFoundError(f"no note with slug {slug!r}")
            if len(matches) > 1:
                raise AmbiguousMatchError(slug, matches)
            return matches[0]

        if title:
            matches = self.find_by_title(title)
            if not matches:
                raise NoteNotFoundError(f"no note with title {title!r}")
            if len(matches) > 1:
                raise AmbiguousMatchError(title, matches)
            return matches[0]

        raise ValueError("resolve_one requires note_id, slug, or title")

    # --------------------------------------------------------------- mutations

    def save(self, record: NoteRecord) -> None:
        """Write the metadata file. Body file is touched if missing."""
        self.ensure_dir()
        record.data_path.touch(exist_ok=True)
        with record.metadata_path.open("w") as f:
            yaml.safe_dump(record.to_yaml_dict(), f)

    def delete(self, record: NoteRecord) -> None:
        """Remove both the metadata and data files."""
        if record.data_path.exists():
            record.data_path.unlink()
        if record.metadata_path.exists():
            record.metadata_path.unlink()

    def update_tags(self, record: NoteRecord, tags: list[str]) -> NoteRecord:
        """Persist a new tag list onto the given record."""
        record.tags = list(tags)
        self.save(record)
        return record
