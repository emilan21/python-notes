from __future__ import annotations

from pathlib import Path

import typer

from ..config.config import Settings
from ..editor import EditorError, launch_editor
from ..note.note import create_note, normalize_tags
from ..output import (
    Formatter,
    SearchHit,
    UnknownFormatError,
    get_formatter,
)
from ..storage import (
    AmbiguousMatchError,
    NoteNotFoundError,
    NoteRecord,
    NoteRepository,
)

app = typer.Typer(help="Manage notes.")


# --------------------------------------------------------------------- helpers


def _get_settings() -> Settings:
    try:
        return Settings.load()
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2)


def _get_repo() -> NoteRepository:
    return NoteRepository(_get_settings().notes_dir)


def _get_formatter(format_flag: str | None) -> Formatter:
    """Resolve format precedence: CLI flag > config default > 'text'."""
    name = format_flag or _get_settings().default_output or "text"
    try:
        return get_formatter(name)
    except UnknownFormatError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2)


def _resolve_or_exit(
    repo: NoteRepository,
    *,
    title: str = "",
    note_id: int = 0,
    slug: str = "",
) -> NoteRecord:
    if not (title or note_id or slug):
        typer.echo("Error: provide --title, --slug, or --id", err=True)
        raise typer.Exit(code=2)

    try:
        return repo.resolve_one(
            note_id=note_id or None,
            slug=slug or None,
            title=title or None,
        )
    except NoteNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    except AmbiguousMatchError as exc:
        typer.echo(str(exc), err=True)
        typer.echo("Re-run with --id to disambiguate.", err=True)
        raise typer.Exit(code=1)


# A single reusable Option so every command's --format help is identical.
FormatOption = typer.Option(
    None,
    "--format",
    "-F",
    help="Output format: text or json. Defaults to config 'default_output'.",
)


# -------------------------------------------------------------------- commands


@app.command()
def new(
    title: str = typer.Option(..., "--title", "-t", help="Title of the note"),
    tags: list[str] = typer.Option([], "--tag", "-g", help="Tags for the note"),
    no_editor: bool = typer.Option(
        False, "--no-editor", help="Create the note without launching an editor"
    ),
    output_format: str = FormatOption,
):
    """Create a new note."""
    settings = _get_settings()
    fmt = _get_formatter(output_format)
    editor = None if no_editor else settings.editor
    try:
        record = create_note(
            notes_dir=Path(settings.notes_dir),
            title=title,
            tags=tags,
            editor=editor,
        )
    except EditorError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    typer.echo(fmt.format_created(record))


@app.command(name="list")
def list_notes(
    sort_by: str = typer.Option(
        "title", "--sort", "-s", help="Sort by: title, created, id"
    ),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Reverse sort order"),
    tag: list[str] = typer.Option(
        [], "--tag", "-g", help="Filter by tag (may be repeated; AND semantics)"
    ),
    output_format: str = FormatOption,
):
    """List all notes."""
    repo = _get_repo()
    fmt = _get_formatter(output_format)
    records = repo.list_all()

    if tag:
        records = [r for r in records if all(t in r.tags for t in tag)]

    keys = {
        "title": lambda r: r.safe_title,
        "created": lambda r: r.creation_date_as_str,
        "id": lambda r: r.id,
    }
    if sort_by not in keys:
        typer.echo(
            f"Unknown sort key: {sort_by}. Valid: {', '.join(keys)}", err=True
        )
        raise typer.Exit(code=2)

    records.sort(key=keys[sort_by], reverse=reverse)
    typer.echo(fmt.format_record_list(records))


@app.command()
def show(
    title: str = typer.Option("", "--title", "-t", help="Note title to display"),
    slug: str = typer.Option("", "--slug", "-s", help="Note slug to display"),
    id: int = typer.Option(0, "--id", "-i", help="Note ID to display"),
    output_format: str = FormatOption,
):
    """Display the contents of a note."""
    record = _resolve_or_exit(_get_repo(), title=title, note_id=id, slug=slug)
    fmt = _get_formatter(output_format)
    if not record.data_path.exists():
        typer.echo("Note data file not found", err=True)
        raise typer.Exit(code=1)
    typer.echo(fmt.format_record_detail(record, record.read_body()))


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
    typer.echo(
        f"Deleted note: {record.safe_title} (id {record.id})", err=True
    )


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
        typer.echo("Note data file not found", err=True)
        raise typer.Exit(code=1)

    try:
        launch_editor(settings.editor, record.data_path)
    except EditorError as exc:
        typer.echo(str(exc), err=True)
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
    output_format: str = FormatOption,
):
    """List, filter, or modify tags."""
    repo = _get_repo()
    fmt = _get_formatter(output_format)
    records = repo.list_all()

    if not records:
        typer.echo(fmt.format_record_list([]))
        return

    if filter_by:
        matches = [r for r in records if all(t in r.tags for t in filter_by)]
        matches.sort(key=lambda r: r.safe_title)
        typer.echo(fmt.format_record_list(matches))
        return

    if add or remove:
        record = _resolve_or_exit(repo, title=title, note_id=id, slug=slug)
        adds = normalize_tags(add)
        rems = normalize_tags(remove)
        new_tags = list(record.tags)
        for t in adds:
            if t not in new_tags:
                new_tags.append(t)
        for t in rems:
            if t in new_tags:
                new_tags.remove(t)
        repo.update_tags(record, new_tags)
        action = "Added" if adds else "Removed"
        changed = adds or rems
        typer.echo(f"{action} tags {changed} on '{record.safe_title}'", err=True)
        typer.echo(f"Current tags: {new_tags}", err=True)
        return

    # Default + --list: show all unique tags
    all_tags: set[str] = set()
    for record in records:
        all_tags.update(record.tags)
    typer.echo(fmt.format_tag_list(all_tags))


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    in_title: bool = typer.Option(False, "--in-title", help="Search in titles only"),
    in_tags: bool = typer.Option(False, "--in-tags", help="Search in tags only"),
    in_body: bool = typer.Option(False, "--in-body", help="Search in body text only"),
    output_format: str = FormatOption,
):
    """Search notes by title, tags, or body."""
    repo = _get_repo()
    fmt = _get_formatter(output_format)
    records = repo.list_all()

    search_all = not (in_title or in_tags or in_body)
    needle = query.lower()
    hits: list[SearchHit] = []

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
            hits.append(SearchHit(record=record, locations=where))

    hits.sort(key=lambda h: h.record.safe_title)
    typer.echo(fmt.format_search_results(hits, query))
