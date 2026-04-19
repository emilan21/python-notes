import typer
from pathlib import Path

from ..config.config import Settings

app = typer.Typer()

def get_config(notes_dir: Path, editor: str, default_output: str) -> Settings:
    return Settings(notes_dir=notes_dir, editor=editor, default_output=default_output)


@app.command()
def init(notes_dir: Path, editor: str, default_output: str):
    config = get_config(notes_dir=notes_dir, editor=editor, default_output=default_output)
    print(config.notes_dir)
    print(config.editor)
    print(config.default_output)
