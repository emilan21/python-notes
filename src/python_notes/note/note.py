import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
import yaml

@dataclass
class NoteMetaData:
    id: int
    title: str
    note_metadata_path: str
    note_data_path: str
    creation_date: datetime
    creation_date_as_str: str
    modified_date: datetime
    modified_date_as_str: str
    tags: list

class Note:
    def __init__(self, note_path: Path, editor: str, title: str, tags: list):
        self.note_path = note_path
        self.editor = editor
        self.note_metadata = NoteMetaData
        self.note_metadata.title = title
        self.note_metadata.id = id(title)
        self.note_metadata.creation_date = datetime.now()
        self.note_metadata.creation_date_as_str = self.note_metadata.creation_date.strftime("%Y-%m-%d_%H_%M_%S")
        self.note_metadata.note_metadata_path = str(note_path / f"{self.note_metadata.title}_metadata_{self.note_metadata.creation_date_as_str}")
        self.note_metadata.note_data_path = str(note_path / f"{self.note_metadata.title}_data_{self.note_metadata.creation_date_as_str}.md")
        self.note_metadata.tags = tags
        print(self.note_metadata.note_metadata_path)
        print(self.note_metadata.note_data_path)

        print(f"Created new note called {self.note_metadata.title}\n")
        self.open_in_editor(Path(self.note_metadata.note_data_path))
        self.save_note_meta_data_as_yml()


    def open_in_editor(self, note_data_path: Path):
        # ensure file exists
        note_data_path.touch(exist_ok=True)

        editor = self.editor

        try:
            subprocess.run([editor, str(note_data_path)])
        except FileNotFoundError:
            raise RuntimeError(f"Editor '{editor}' not found")


    def save_note_meta_data_as_yml(self):
        data = {
            'id': self.note_metadata.id,
            'title': self.note_metadata.title,
            'tags': self.note_metadata.tags,
            'creation_date': self.note_metadata.creation_date,
            'creation_date_as_str': self.note_metadata.creation_date_as_str,
            'note_metadata_path': self.note_metadata.note_metadata_path,
            'note_data_path': self.note_metadata.note_data_path,
        }

        with open(self.note_metadata.note_metadata_path, 'w') as file:
            yaml.dump(data, file)
