import typer

from ..note.note import Note

app = typer.Typer()

def get_note() -> Note:
    return Note(note_path = "data/")


@app.command()
def new(title: str):
    note = get_note()
    note.new(title)
