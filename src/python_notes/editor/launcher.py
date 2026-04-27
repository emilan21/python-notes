"""Editor invocation, factored out so creation and editing share one path."""

from __future__ import annotations

import subprocess
from pathlib import Path


class EditorError(RuntimeError):
    """Raised when an editor cannot be launched or exits non-zero."""


def launch_editor(editor: str, path: Path, *, check: bool = True) -> None:
    """Open ``path`` in ``editor``.

    Always touches the file first so the editor sees an existing path.
    Raises EditorError on missing-binary or non-zero exit (when check=True).
    """
    path.touch(exist_ok=True)
    try:
        subprocess.run([editor, str(path)], check=check)
    except FileNotFoundError as exc:
        raise EditorError(f"editor {editor!r} not found") from exc
    except subprocess.CalledProcessError as exc:
        raise EditorError(f"editor {editor!r} exited with status {exc.returncode}") from exc
