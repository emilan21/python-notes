class Note:
    def __init__(self, note_path: str):
        self.note_path = note_path


    def new(self, title: str):
        print(f"Created new note called {title}")


    def delete(self, title: str):
        print(f"Deleting note called {title}")


    def list(self):
        print(f"Listing all notes")


    def search(self, title: str):
        print(f"Searching for note called {title}")


    def show(self, title: str):
        print(f"Show note called {title}")
