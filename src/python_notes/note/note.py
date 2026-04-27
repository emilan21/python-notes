"""Note creation workflow: build a record, optionally open the editor, persist."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

from ..editor import launch_editor
from ..storage import NoteRecord, NoteRepository

SLUG_MAX_LEN = 80
UUID_NAMESPACE = uuid.NAMESPACE_DNS


def safe_title(title: str) -> str:
    """Lowercase hyphenated ASCII slug, capped at SLUG_MAX_LEN. Falls back to 'untitled'."""
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        return "untitled"
    if len(slug) > SLUG_MAX_LEN:
        slug = slug[:SLUG_MAX_LEN].rstrip("-") or "untitled"
    return slug


def normalize_tags(tags: list[str]) -> list[str]:
    """Trim, drop empty, and dedupe (case-sensitive) while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        t = raw.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


def _generate_id(slug: str, when: datetime) -> int:
    """Generate a stable-ish, collision-resistant note id.

    Seeds the UUID with slug + timestamp + a random component so two notes
    with the same title at different times don't collide, and two notes
    created in the same second still differ.
    """
    seed = f"{slug}|{when.isoformat()}|{uuid.uuid4().hex}"
    return int(uuid.uuid5(UUID_NAMESPACE, seed))


def create_note(
    *,
    notes_dir: Path,
    title: str,
    tags: list[str],
    editor: str | None = None,
) -> NoteRecord:
    """Build, optionally edit, and persist a new note. Returns the saved record.

    If ``editor`` is None, the note is saved without invoking an editor.
    """
    repo = NoteRepository(notes_dir)
    repo.ensure_dir()

    slug = safe_title(title)
    when = datetime.now()
    note_id = _generate_id(slug, when)
    metadata_path, data_path = NoteRepository.build_paths(notes_dir, slug, note_id, when)

    record = NoteRecord(
        id=note_id,
        title=title,
        safe_title=slug,
        tags=normalize_tags(tags),
        creation_date=when,
        creation_date_as_str=when.strftime("%Y-%m-%d_%H_%M_%S"),
        metadata_path=metadata_path,
        data_path=data_path,
    )

    # Touch + persist before optionally launching the editor: if the editor
    # crashes we still have a real note on disk.
    repo.save(record)
    if editor:
        launch_editor(editor, record.data_path)

    return record


# Backward-compat shim: old callers still construct Note(...). Keep the class
# but make it a thin wrapper over create_note so behavior is identical.
class Note:
    """Deprecated. Use ``create_note`` instead."""

    def __init__(self, note_path: Path, editor: str, title: str, tags: list):
        self.record = create_note(
            notes_dir=note_path,
            title=title,
            tags=tags,
            editor=editor,
        )
