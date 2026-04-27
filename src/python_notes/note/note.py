from __future__ import annotations

import re
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class NoteMetaData:
    id: int
    title: str
    safe_title: str
    note_metadata_path: str
    note_data_path: str
    creation_date: datetime
    creation_date_as_str: str
    tags: list = field(default_factory=list)
    modified_date: datetime | None = None
    modified_date_as_str: str | None = None


class Note:
    def __init__(self, note_path: Path, editor: str, title: str, tags: list):
        self.note_path = note_path
        self.editor = editor

        note_path.mkdir(parents=True, exist_ok=True)

        safe = self._safe_title(title)
        creation_date = datetime.now()
        creation_str = creation_date.strftime("%Y-%m-%d_%H_%M_%S")
        note_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, safe))

        metadata_path = note_path / f"{safe}_{note_id}_metadata_{creation_str}"
        data_path = note_path / f"{safe}_{note_id}_data_{creation_str}.md"

        self.note_metadata = NoteMetaData(
            id=note_id,
            title=title,
            safe_title=safe,
            note_metadata_path=str(metadata_path),
            note_data_path=str(data_path),
            creation_date=creation_date,
            creation_date_as_str=creation_str,
            tags=list(tags),
        )

        print(f"Created new note called {safe}\n")
        self.open_in_editor(Path(self.note_metadata.note_data_path))
        self.save_note_meta_data_as_yml()

    def open_in_editor(self, note_data_path: Path) -> None:
        note_data_path.touch(exist_ok=True)
        try:
            subprocess.run([self.editor, str(note_data_path)])
        except FileNotFoundError:
            raise RuntimeError(f"Editor '{self.editor}' not found")

    def save_note_meta_data_as_yml(self) -> None:
        data = {
            "id": self.note_metadata.id,
            "title": self.note_metadata.title,
            "safe_title": self.note_metadata.safe_title,
            "tags": self.note_metadata.tags,
            "creation_date": self.note_metadata.creation_date,
            "creation_date_as_str": self.note_metadata.creation_date_as_str,
            "note_metadata_path": self.note_metadata.note_metadata_path,
            "note_data_path": self.note_metadata.note_data_path,
        }
        with open(self.note_metadata.note_metadata_path, "w") as file:
            yaml.safe_dump(data, file)

    @staticmethod
    def _safe_title(title: str) -> str:
        """Generate a slug-style safe filename: lowercase, hyphenated, ASCII-only."""
        slug = title.strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug or "untitled"
