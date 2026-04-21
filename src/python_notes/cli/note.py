
import typer
from pathlib import Path

from ..note.note import Note

app = typer.Typer()

def get_note_path() -> Path:
    return Path("data")


@app.command()
def new(title: str):
    """Create a new note with the given title."""
    note = Note(note_path=get_note_path(), editor="nvim", title=title)


@app.command()
def delete(title: str):
    """Delete a note by title."""
    note_path = get_note_path()
    # Look for files that match the title pattern
    matching_files = [f for f in note_path.glob(f"{title}*.md")]
    
    if not matching_files:
        print(f"Note '{title}' not found")
        return
    
    # Use the most recent file if multiple exist
    file_path = sorted(matching_files)[-1]
    
    file_path.unlink()
    print(f"Deleted note: {title}")


@app.command()
def list():
    """List all notes in the notes directory."""
    note_path = get_note_path()
    if not note_path.exists():
        print("Notes directory does not exist")
        return
    
    files = [f for f in note_path.iterdir() if f.is_file() and f.suffix == ".md"]
    if not files:
        print("No notes found")
        return
    
    print("Notes:")
    for file in sorted(files):
        print(f"  {file.stem}")


@app.command()
def show(title: str):
    """Display the contents of a note."""
    import subprocess
    
    note_path = get_note_path()
    # Look for files that match the title pattern
    matching_files = [f for f in note_path.glob(f"{title}*.md")]
    
    if not matching_files:
        print(f"Note '{title}' not found")
        return
    
    # Use the most recent file if multiple exist
    file_path = sorted(matching_files)[-1]
    
    try:
        subprocess.run(["cat", str(file_path)], check=True)
    except subprocess.CalledProcessError:
        print(f"Error displaying note")


@app.command()
def edit(title: str):
    """Edit an existing note in the configured editor."""
    import subprocess
    
    note_path = get_note_path()
    editor = "nvim"
    
    # Look for files that match the title pattern
    matching_files = [f for f in note_path.glob(f"{title}*.md")]
    
    if not matching_files:
        print(f"Note '{title}' not found")
        return
    
    # Use the most recent file if multiple exist
    file_path = sorted(matching_files)[-1]
    
    try:
        subprocess.run([editor, str(file_path)], check=True)
    except FileNotFoundError:
        raise RuntimeError(f"Editor '{editor}' not found")
    except subprocess.CalledProcessError:
        print(f"Error editing note")
