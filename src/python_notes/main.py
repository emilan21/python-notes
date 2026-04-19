import typer
from pathlib import Path

from .cli import note
from .cli import config

app = typer.Typer()

app.add_typer(note.app, name="note")
app.add_typer(config.app, name="config")

if __name__ == "__main__":
    app()
