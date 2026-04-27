import typer
import yaml
from typing import List
from pathlib import Path
import subprocess

from ..note.note import Note

app = typer.Typer()

def get_note_path() -> Path:
    return Path("data")


@app.command()
def new(title: str, tags: List[str] = typer.Option([], "--tag", "-t")):
    """Create a new note with the given title."""
    note = Note(note_path=get_note_path(), editor="nvim", title=title, tags=tags)


@app.command()
def delete(title: str):
    """Delete a note by title."""
    
    note_path = get_note_path()
    # Look for metadata files that match the title pattern
    matching_files = [f for f in note_path.glob(f"{title}_metadata_*")]
    
    if not matching_files:
        print(f"Note '{title}' not found")
        return
    
    # Use the most recent file if multiple exist
    metadata_file = sorted(matching_files)[-1]
    
    # Load metadata to get the data file path
    with open(metadata_file, 'r') as f:
        metadata = yaml.safe_load(f)
    
    # Delete both metadata and data files
    data_file = Path(metadata['note_data_path'])
    if data_file.exists():
        data_file.unlink()
    metadata_file.unlink()
    
    print(f"Deleted note: {title}")


@app.command()
def list():
    """List all notes in the notes directory."""
    
    note_path = get_note_path()
    if not note_path.exists():
        print("Notes directory does not exist")
        return
    
    # Find all metadata files
    metadata_files = [f for f in note_path.iterdir() if f.is_file() and "_metadata_" in f.name]
    if not metadata_files:
        print("No notes found")
        return
    
    print("Notes:")
    for metadata_file in sorted(metadata_files):
        with open(metadata_file, 'r') as f:
            metadata = yaml.safe_load(f)
        title = metadata.get('title', metadata_file.stem)
        tags = metadata.get('tags', [])
        tags_str = f" [{', '.join(tags)}]" if tags else ""
        print(f"  {title}{tags_str}")


@app.command()
def show(title: str = typer.Option("", '--title'), id: int = typer.Option(0, '--id')):
    """Display the contents of a note."""
    
    note_path = get_note_path()
    matching_files = []
    
    if title:
        # Look for metadata files that match the title pattern
        matching_files = [f for f in note_path.glob(f"{title}_metadata_*")]
    elif id:
        # Look for metadata files that match the id
        all_metadata_files = [f for f in note_path.iterdir() if f.is_file() and "_metadata_" in f.name]
        for metadata_file in all_metadata_files:
            with open(metadata_file, 'r') as f:
                metadata = yaml.safe_load(f)
            if metadata.get('id') == id:
                matching_files.append(metadata_file)
                break
    
    if not matching_files:
        search_term = f"title '{title}'" if title else f"id {id}"
        print(f"Note with {search_term} not found")
        return
    
    # Use the most recent file if multiple exist
    metadata_file = sorted(matching_files)[-1]
    
    # Load metadata to get the data file path
    with open(metadata_file, 'r') as f:
        metadata = yaml.safe_load(f)
    
    data_file = Path(metadata['note_data_path'])
    
    if not data_file.exists():
        print(f"Note data file not found")
        return
    
    try:
        subprocess.run(["cat", str(data_file)], check=True)
    except subprocess.CalledProcessError:
        print(f"Error displaying note")


@app.command()
def edit(title: str):
    """Edit an existing note in the configured editor."""
    
    note_path = get_note_path()
    editor = "nvim"
    
    # Look for metadata files that match the title pattern
    matching_files = [f for f in note_path.glob(f"{title}_metadata_*")]
    
    if not matching_files:
        print(f"Note '{title}' not found")
        return
    
    # Use the most recent file if multiple exist
    metadata_file = sorted(matching_files)[-1]
    
    # Load metadata to get the data file path
    with open(metadata_file, 'r') as f:
        metadata = yaml.safe_load(f)
    
    data_file = Path(metadata['note_data_path'])
    
    if not data_file.exists():
        print(f"Note data file not found")
        return
    
    try:
        subprocess.run([editor, str(data_file)], check=True)
    except FileNotFoundError:
        raise RuntimeError(f"Editor '{editor}' not found")
    except subprocess.CalledProcessError:
        print(f"Error editing note")
