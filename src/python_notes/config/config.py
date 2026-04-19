from dataclasses import dataclass
from pathlib import Path

class Settings:
    def __init__(self, notes_dir: Path, editor: str, default_output: str):
        self.notes_dir = notes_dir
        self.editor = editor
        self.default_output = default_output

        self.notes_dir.mkdir(parents=True, exist_ok=True)
