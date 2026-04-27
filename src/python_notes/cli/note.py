from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from ..config.config import Settings
from ..note.note import Note
from ..storage import (
    AmbiguousMatchError,
    NoteNotFoundError,
    NoteRecord,
    NoteRepository,
)

app = typer.Typer(help="Manage notes.")


# --------------------------------------------------------------------- helpers


def _get_settings() -> Settings:
    return Settings.load()


def _get_repo() -> NoteRepository:
    return NoteRepository(_get_settings().notes_dir)


def _resolve_or_exit(
    repo: NoteRepository,
    *,
    title: str = "",
    note_id: int = 0,
    slug: str = "",
) -> NoteRecord:
    """Resolve a single note or exit with a helpful CLI message."""
    if not (title or note_id or slug):
        typer.echo("Error: provide --title, --slug, or --id")
        raise typer.Exit(code=2)

    try:
        return repo.resolve_one(
            note_id=note_id or None,
            slug=slug or None,
            title=title or None,
        )
    except NoteNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    except AmbiguousMatchError as exc:
        typer.echo(str(exc))
        typer.echo("Re-run with --id to disambiguate.")
        raise typer.Exit(code=1)


def _format_record(record: NoteRecord) -> str:
    tags_str = f" [{', '.join(record.tags)}]" if record.tags else ""
    return f"  {record.safe_title}{tags_str}"


# -------------------------------------------------------------------- commands


@app.command()
def new(
    title: str = typer.Option(..., "--title", "-t", help="Title of the note"),
    tags: list[str] = typer.Option([], "--tag", "-g", help="Tags for the note"),
):
    """Create a new note with the given title."""
    settings = _get_settings()
    Note(
        note_path=Path(settings.notes_dir),
        editor=settings.editor,
        title=title,
        tags=tags,
    )


@app.command(name="list")
def list_notes(
    sort_by: str = typer.Option(
        "title", "--sort", "-s", help="Sort by: title, created, id"
    ),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Reverse sort order"),
    tag: list[str] = typer.Option(
        [], "--tag", "-g", help="Filter by tag (may be repeated; AND semantics)"
    ),
):
    """List all notes."""
    repo = _get_repo()
    records = repo.list_all()

    if tag:
        records = [r for r in records if all(t in r.tags for t in tag)]

    keys = {
        "title": lambda r: r.safe_title,
        "created": lambda r: r.creation_date_as_str,
        "id": lambda r: r.id,
    }
    if sort_by not in keys:
        typer.echo(f"Unknown sort key: {sort_by}. Valid: {', '.join(keys)}")
        raise typer.Exit(code=2)

    records.sort(key=keys[sort_by], reverse=reverse)

    if not records:
        typer.echo("No notes found")
        return
    typer.echo("Notes:")
    for record in records:
        typer.echo(_format_record(record))


@app.command()
def show(
    title: str = typer.Option("", "--title", "-t", help="Note title to display"),
    slug: str = typer.Option("", "--slug", "-s", help="Note slug to display"),
    id: int = typer.Option(0, "--id", "-i", help="Note ID to display"),
):
    """Display the contents of a note."""
    record = _resolve_or_exit(_get_repo(), title=title, note_id=id, slug=slug)

    if not record.data_path.exists():
        typer.echo("Note data file not found")
        raise typer.Exit(code=1)

    typer.echo(record.read_body())


@app.command()
def delete(
    title: str = typer.Option("", "--title", "-t", help="Note title to delete"),
    slug: str = typer.Option("", "--slug", "-s", help="Note slug to delete"),
    id: int = typer.Option(0, "--id", "-i", help="Note ID to delete"),
):
    """Delete a note."""
    repo = _get_repo()
    record = _resolve_or_exit(repo, title=title, note_id=id, slug=slug)
    repo.delete(record)
    typer.echo(f"Deleted note: {record.safe_title} (id {record.id})")


@app.command()
def edit(
    title: str = typer.Option("", "--title", "-t", help="Note title to edit"),
    slug: str = typer.Option("", "--slug", "-s", help="Note slug to edit"),
    id: int = typer.Option(0, "--id", "-i", help="Note ID to edit"),
):
    """Edit an existing note in the configured editor."""
    settings = _get_settings()
    repo = NoteRepository(settings.notes_dir)
    record = _resolve_or_exit(repo, title=title, note_id=id, slug=slug)

    if not record.data_path.exists():
        typer.echo("Note data file not found")
        raise typer.Exit(code=1)

    try:
        subprocess.run([settings.editor, str(record.data_path)], check=True)
    except FileNotFoundError:
        raise RuntimeError(f"Editor '{settings.editor}' not found")
    except subprocess.CalledProcessError as exc:
        typer.echo(f"Editor exited with error: {exc}")
        raise typer.Exit(code=1)


@app.command()
def tags(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all tags"),
    filter_by: list[str] = typer.Option(
        [], "--filter", "-f", help="Filter notes by tags"
    ),
    add: list[str] = typer.Option([], "--add", "-a", help="Add tags to a note"),
    remove: list[str] = typer.Option(
        [], "--remove", "-r", help="Remove tags from a note"
    ),
    title: str = typer.Option("", "--title", "-t", help="Note title for add/remove"),
    slug: str = typer.Option("", "--slug", "-s", help="Note slug for add/remove"),
    id: int = typer.Option(0, "--id", "-i", help="Note ID for add/remove"),
):
    """List, filter, or modify tags."""
    repo = _get_repo()
    records = repo.list_all()

    if not records:
        typer.echo("No notes found")
        return

    if filter_by:
        matches = [r for r in records if all(t in r.tags for t in filter_by)]
        typer.echo(f"Notes with tags {filter_by}:")
        if not matches:
            typer.echo("  No notes found with those tags")
            return
        for record in sorted(matches, key=lambda r: r.safe_title):
            typer.echo(_format_record(record))
        return

    if add or remove:
        record = _resolve_or_exit(repo, title=title, note_id=id, slug=slug)
        new_tags = list(record.tags)
        for t in add:
            if t not in new_tags:
                new_tags.append(t)
        for t in remove:
            if t in new_tags:
                new_tags.remove(t)
        repo.update_tags(record, new_tags)
        action = "Added" if add else "Removed"
        changed = add or remove
        typer.echo(f"{action} tags {list(changed)} on '{record.safe_title}'")
        typer.echo(f"Current tags: {new_tags}")
        return

    # Default + --list: show all unique tags
    all_tags: set[str] = set()
    for record in records:
        all_tags.update(record.tags)

    if not all_tags:
        typer.echo("No tags found")
        return
    typer.echo("All tags:")
    for t in sorted(all_tags):
        typer.echo(f"  {t}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    in_title: bool = typer.Option(False, "--in-title", help="Search in titles only"),
    in_tags: bool = typer.Option(False, "--in-tags", help="Search in tags only"),
    in_body: bool = typer.Option(False, "--in-body", help="Search in body text only"),
):
    """Search notes by title, tags, or body."""
    repo = _get_repo()
    records = repo.list_all()
    if not records:
        typer.echo("No notes found")
        return

    search_all = not (in_title or in_tags or in_body)
    needle = query.lower()
    results: list[tuple[NoteRecord, list[str]]] = []

    for record in records:
        where: list[str] = []
        if (search_all or in_title) and (
            needle in record.title.lower() or needle in record.safe_title.lower()
        ):
            where.append("title")
        if (search_all or in_tags) and any(needle in t.lower() for t in record.tags):
            where.append("tags")
        if search_all or in_body:
            try:
                if needle in record.read_body().lower():
                    where.append("body")
            except OSError:
                pass
        if where:
            results.append((record, where))

    if not results:
        typer.echo(f"No notes found matching '{query}'")
        return

    typer.echo(f"Found {len(results)} note(s) matching '{query}':")
    for record, where in sorted(results, key=lambda x: x[0].safe_title):
        loc = f" (found in: {', '.join(where)})"
        typer.echo(f"{_format_record(record)}{loc}")
