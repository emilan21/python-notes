from __future__ import annotations

from pathlib import Path

import pytest

from python_notes.note.note import (
    SLUG_MAX_LEN,
    create_note,
    normalize_tags,
    safe_title,
)
from python_notes.storage import NoteRepository


# ----------------------------------------------------------------- safe_title


def test_safe_title_lowercases_and_hyphenates():
    assert safe_title("Hello World") == "hello-world"


def test_safe_title_collapses_runs_of_punctuation():
    assert safe_title("foo!!!  bar??") == "foo-bar"


def test_safe_title_falls_back_for_empty():
    assert safe_title("") == "untitled"
    assert safe_title("   ") == "untitled"
    assert safe_title("!!!") == "untitled"


def test_safe_title_truncates_long_titles():
    long_title = "a" * 500
    out = safe_title(long_title)
    assert len(out) <= SLUG_MAX_LEN
    assert out == "a" * SLUG_MAX_LEN


def test_safe_title_truncation_does_not_leave_trailing_hyphen():
    # Crafted so the cut would land on a hyphen
    title = "a" * (SLUG_MAX_LEN - 1) + " b" * 5
    out = safe_title(title)
    assert not out.endswith("-")


# -------------------------------------------------------------- normalize_tags


def test_normalize_tags_trims_and_dedupes():
    assert normalize_tags(["foo", " foo ", "bar", "", "baz", "bar"]) == [
        "foo",
        "bar",
        "baz",
    ]


def test_normalize_tags_is_case_sensitive():
    # Two tags differing only by case are kept as-is — that's a deliberate
    # choice. Update this test if we ever case-fold.
    assert normalize_tags(["Foo", "foo"]) == ["Foo", "foo"]


def test_normalize_tags_drops_whitespace_only():
    assert normalize_tags(["   ", "\t", "x"]) == ["x"]


# ----------------------------------------------------------------- create_note


def test_create_note_persists_without_editor(tmp_path):
    notes_dir = tmp_path / "notes"
    record = create_note(
        notes_dir=notes_dir, title="Hello World", tags=["a"], editor=None
    )
    assert record.metadata_path.exists()
    assert record.data_path.exists()
    assert record.safe_title == "hello-world"
    assert record.tags == ["a"]


def test_create_note_normalizes_tags(tmp_path):
    record = create_note(
        notes_dir=tmp_path / "notes",
        title="x",
        tags=[" foo ", "foo", "bar"],
        editor=None,
    )
    assert record.tags == ["foo", "bar"]


def test_create_note_avoids_id_collision_for_same_title(tmp_path):
    notes_dir = tmp_path / "notes"
    a = create_note(notes_dir=notes_dir, title="todo", tags=[], editor=None)
    b = create_note(notes_dir=notes_dir, title="todo", tags=[], editor=None)
    assert a.id != b.id

    repo = NoteRepository(notes_dir)
    matches = repo.find_by_slug("todo")
    assert len(matches) == 2
    assert {m.id for m in matches} == {a.id, b.id}


def test_create_note_invokes_editor_when_provided(tmp_path, monkeypatch):
    calls: list[Path] = []

    def fake_launch(editor: str, path: Path, **_: object) -> None:
        calls.append(path)

    # Patch the symbol used inside note.note (imported at module level)
    monkeypatch.setattr("python_notes.note.note.launch_editor", fake_launch)

    record = create_note(
        notes_dir=tmp_path / "notes", title="foo", tags=[], editor="vi"
    )
    assert calls == [record.data_path]


def test_create_note_skips_editor_when_none(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("editor must not be launched")

    monkeypatch.setattr("python_notes.note.note.launch_editor", boom)
    create_note(notes_dir=tmp_path / "notes", title="foo", tags=[], editor=None)


def test_create_note_persists_before_editor(tmp_path, monkeypatch):
    """If the editor crashes, the note should still be on disk."""
    paths_seen_at_editor_time: dict[str, bool] = {}

    def fake_launch(editor: str, path: Path, **_: object) -> None:
        paths_seen_at_editor_time["metadata_existed"] = path.with_name(
            path.stem.replace("_data_", "_metadata_").rsplit(".", 1)[0]
        ).exists() or any(
            p.exists()
            for p in path.parent.iterdir()
            if "_metadata_" in p.name
        )
        raise RuntimeError("simulated editor crash")

    monkeypatch.setattr("python_notes.note.note.launch_editor", fake_launch)
    with pytest.raises(RuntimeError):
        create_note(
            notes_dir=tmp_path / "notes", title="foo", tags=[], editor="vi"
        )
    assert paths_seen_at_editor_time["metadata_existed"] is True
