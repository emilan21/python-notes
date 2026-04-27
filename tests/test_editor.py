from __future__ import annotations

import pytest

from python_notes.editor import EditorError, launch_editor


def test_launch_editor_touches_file(tmp_path):
    target = tmp_path / "note.md"
    assert not target.exists()
    launch_editor("true", target)  # /usr/bin/true exits 0 immediately
    assert target.exists()


def test_launch_editor_missing_binary_raises(tmp_path):
    target = tmp_path / "note.md"
    with pytest.raises(EditorError) as exc_info:
        launch_editor("definitely-not-a-real-editor-binary", target)
    assert "not found" in str(exc_info.value)


def test_launch_editor_nonzero_exit_raises(tmp_path):
    target = tmp_path / "note.md"
    with pytest.raises(EditorError) as exc_info:
        launch_editor("false", target)  # /usr/bin/false exits 1
    assert "exited with status" in str(exc_info.value)


def test_launch_editor_check_false_swallows_nonzero(tmp_path):
    target = tmp_path / "note.md"
    launch_editor("false", target, check=False)  # no exception
    assert target.exists()
