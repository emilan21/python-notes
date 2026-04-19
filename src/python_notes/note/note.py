import os
import subprocess
from pathlib import Path

class Note:
    def __init__(self, note_path: Path, editor: str):
        self.note_path = note_path
        self.editor = editor


    def new(self, title: str):
        print(f"Created new note called {title}\n")
        self.open_in_editor(title)


    def delete(self, title: str):
        print(f"Deleting note called {title}")
        file_path = self.note_path / f"{title}"
        file_path.unlink(missing_ok=True)


    def list(self):
        print(f"Listing all notes\n")
        files = [f for f in self.note_path.iterdir() if f.is_file()]
        for file in files:
            print(file.name)


    def search(self, title: str):
        print(f"Searching for note called {title}\n")


    def show(self, title: str):
        print(f"Showing note called {title}\n")
        self.display_note(title)


    def edit(self, title: str):
        print(f"Edit note called {title}")
        self.open_in_editor(title)

    def open_in_editor(self, title: str):
        file_path = self.note_path / f"{title}"

        # ensure file exists
        file_path.touch(exist_ok=True)

        editor = self.editor

        try:
            subprocess.run([editor, str(file_path)])
        except FileNotFoundError:
            raise RuntimeError(f"Editor '{editor}' not found")

    def display_note(self, title: str):
        file_path = self.note_path / f"{title}"

        if file_path.exists():
            try:
                subprocess.run(["cat", str(file_path)])
            except FileNotFoundError:
                raise RuntimeError(f"File '{file_path}' not found")
        else:
            print(f"{title} does not exist")
