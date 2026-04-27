from __future__ import annotations

from pathlib import Path

import typer

from ..config.config import Settings, VALID_OUTPUT_FORMATS, config_path

app = typer.Typer(help="Manage python-notes configuration.")


@app.command()
def init(
    notes_dir: Path = typer.Option(
        None, "--notes-dir", "-n", help="Directory where notes are stored"
    ),
    editor: str = typer.Option(
        None, "--editor", "-e", help="Editor command for opening notes"
    ),
    default_output: str = typer.Option(
        None, "--default-output", "-o", help="Default output format (text/json)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite an existing config file"
    ),
):
    """Create a config file with the given (or default) values."""
    path = config_path()
    if path.exists() and not force:
        typer.echo(f"Config already exists at {path}. Use --force to overwrite.")
        raise typer.Exit(code=1)

    defaults = Settings.default()
    if default_output is not None and default_output not in VALID_OUTPUT_FORMATS:
        valid = ", ".join(VALID_OUTPUT_FORMATS)
        typer.echo(
            f"Invalid --default-output {default_output!r}; valid: {valid}", err=True
        )
        raise typer.Exit(code=2)

    settings = Settings(
        notes_dir=notes_dir.expanduser() if notes_dir else defaults.notes_dir,
        editor=editor or defaults.editor,
        default_output=default_output or defaults.default_output,
    )
    written = settings.save(path)
    settings.notes_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Wrote config to {written}")
    typer.echo(f"  notes_dir:      {settings.notes_dir}")
    typer.echo(f"  editor:         {settings.editor}")
    typer.echo(f"  default_output: {settings.default_output}")


@app.command()
def show():
    """Display the currently loaded configuration."""
    try:
        settings = Settings.load()
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2)
    path = config_path()
    source = str(path) if path.exists() else "(defaults — no config file found)"
    typer.echo(f"Config source: {source}")
    typer.echo(f"  notes_dir:      {settings.notes_dir}")
    typer.echo(f"  editor:         {settings.editor}")
    typer.echo(f"  default_output: {settings.default_output}")


@app.command()
def path():
    """Print the config file path."""
    typer.echo(str(config_path()))
