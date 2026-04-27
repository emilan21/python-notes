from __future__ import annotations

import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from ..storage import NoteRecord, NoteRepository


class Note:
    """High-level workflow for creating a new note: build, edit, persist."""

    def __init__(self, note_path: Path, editor: str, title: str, tags: list):
        self.editor = editor
        self.repo = NoteRepository(note_path)
        self.repo.ensure_dir()

        slug = self._safe_title(title)
        creation_date = datetime.now()
        note_id = int(uuid.uuid5(uuid.NAMESPACE_DNS, slug))
        metadata_path, data_path = NoteRepository.build_paths(
            note_path, slug, note_id, creation_date
        )

        self.record = NoteRecord(
            id=note_id,
            title=title,
            safe_title=slug,
            tags=list(tags),
            creation_date=creation_date,
            creation_date_as_str=creation_date.strftime("%Y-%m-%d_%H_%M_%S"),
            metadata_path=metadata_path,
            data_path=data_path,
        )

        print(f"Created new note called {slug}\n")
        self._open_in_editor(self.record.data_path)
        self.repo.save(self.record)

    def _open_in_editor(self, path: Path) -> None:
        path.touch(exist_ok=True)
        try:
            subprocess.run([self.editor, str(path)])
        except FileNotFoundError:
            raise RuntimeError(f"Editor '{self.editor}' not found")

    @staticmethod
    def _safe_title(title: str) -> str:
        """Lowercase hyphenated ASCII slug. Falls back to 'untitled'."""
        slug = title.strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug or "untitled"
