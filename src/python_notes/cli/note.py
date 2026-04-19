import typer
from pathlib import Path

from ..note.note import Note

app = typer.Typer()

def get_note() -> Note:
    path = Path("data")
    return Note(note_path = path, editor="nvim")


@app.command()
def new(title: str):
    note = get_note()
    note.new(title)

@app.command()
def delete(title: str):
    note = get_note()
    note.delete(title)

@app.command()
def list():
    note = get_note()
    note.list()
