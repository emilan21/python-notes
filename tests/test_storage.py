from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from python_notes.storage import (
    AmbiguousMatchError,
    NoteCorruptError,
    NoteNotFoundError,
    NoteRecord,
    NoteRepository,
)


@pytest.fixture
def repo(tmp_path):
    return NoteRepository(tmp_path / "notes")


def _make_record(repo: NoteRepository, *, slug: str, note_id: int, tags=None):
    when = datetime(2024, 1, 1, 12, 0, 0)
    metadata_path, data_path = NoteRepository.build_paths(
        repo.notes_dir, slug, note_id, when
    )
    return NoteRecord(
        id=note_id,
        title=slug.replace("-", " ").title(),
        safe_title=slug,
        tags=list(tags or []),
        creation_date=when,
        creation_date_as_str=when.strftime("%Y-%m-%d_%H_%M_%S"),
        metadata_path=metadata_path,
        data_path=data_path,
    )


def test_build_paths_uses_expected_naming(tmp_path):
    when = datetime(2024, 6, 1, 9, 30, 15)
    md, data = NoteRepository.build_paths(tmp_path, "hello-world", 42, when)
    assert md.name == "hello-world_42_metadata_2024-06-01_09_30_15"
    assert data.name == "hello-world_42_data_2024-06-01_09_30_15.md"


def test_save_creates_metadata_and_data_files(repo):
    record = _make_record(repo, slug="alpha", note_id=1)
    repo.save(record)
    assert record.metadata_path.exists()
    assert record.data_path.exists()


def test_save_then_load_roundtrip(repo):
    record = _make_record(repo, slug="alpha", note_id=1, tags=["a", "b"])
    repo.save(record)

    loaded = repo.find_by_id(1)
    assert loaded is not None
    assert loaded.id == 1
    assert loaded.safe_title == "alpha"
    assert loaded.tags == ["a", "b"]
    assert loaded.metadata_path == record.metadata_path
    assert loaded.data_path == record.data_path


def test_list_all_empty_when_dir_missing(tmp_path):
    repo = NoteRepository(tmp_path / "does-not-exist")
    assert repo.list_all() == []


def test_list_all_skips_corrupt_with_warning(repo, capsys):
    good = _make_record(repo, slug="good", note_id=1)
    repo.save(good)

    repo.ensure_dir()
    bad = repo.notes_dir / "bad_2_metadata_2024-01-01_00_00_00"
    bad.write_text("not: [valid: yaml")

    records = repo.list_all()
    assert len(records) == 1
    assert records[0].id == 1
    err = capsys.readouterr().err
    assert "warning" in err and "bad" in err


def test_load_rejects_non_mapping_yaml(repo):
    repo.ensure_dir()
    bad = repo.notes_dir / "x_1_metadata_2024-01-01_00_00_00"
    bad.write_text("- a\n- list\n")
    with pytest.raises(NoteCorruptError):
        repo._load_record(bad)


def test_load_rejects_missing_required_fields(repo):
    repo.ensure_dir()
    bad = repo.notes_dir / "x_1_metadata_2024-01-01_00_00_00"
    bad.write_text(yaml.safe_dump({"id": 1, "title": "t"}))
    with pytest.raises(NoteCorruptError) as exc_info:
        repo._load_record(bad)
    assert "missing required fields" in str(exc_info.value)


def test_find_by_slug_returns_all_matches(repo):
    repo.save(_make_record(repo, slug="dup", note_id=1))
    # Distinct id and timestamp so files don't collide
    second = _make_record(repo, slug="dup", note_id=2)
    second.metadata_path = repo.notes_dir / "dup_2_metadata_2024-02-02_00_00_00"
    second.data_path = repo.notes_dir / "dup_2_data_2024-02-02_00_00_00.md"
    repo.save(second)

    matches = repo.find_by_slug("dup")
    assert {r.id for r in matches} == {1, 2}


def test_resolve_one_by_id(repo):
    repo.save(_make_record(repo, slug="alpha", note_id=1))
    record = repo.resolve_one(note_id=1)
    assert record.id == 1


def test_resolve_one_by_slug_unique(repo):
    repo.save(_make_record(repo, slug="alpha", note_id=1))
    record = repo.resolve_one(slug="alpha")
    assert record.safe_title == "alpha"


def test_resolve_one_not_found(repo):
    with pytest.raises(NoteNotFoundError):
        repo.resolve_one(note_id=999)


def test_resolve_one_ambiguous_slug(repo):
    repo.save(_make_record(repo, slug="dup", note_id=1))
    second = _make_record(repo, slug="dup", note_id=2)
    second.metadata_path = repo.notes_dir / "dup_2_metadata_2024-02-02_00_00_00"
    second.data_path = repo.notes_dir / "dup_2_data_2024-02-02_00_00_00.md"
    repo.save(second)

    with pytest.raises(AmbiguousMatchError) as exc_info:
        repo.resolve_one(slug="dup")
    assert len(exc_info.value.candidates) == 2


def test_resolve_one_requires_an_argument(repo):
    with pytest.raises(ValueError):
        repo.resolve_one()


def test_delete_removes_both_files(repo):
    record = _make_record(repo, slug="alpha", note_id=1)
    repo.save(record)
    assert record.metadata_path.exists() and record.data_path.exists()

    repo.delete(record)
    assert not record.metadata_path.exists()
    assert not record.data_path.exists()


def test_update_tags_persists(repo):
    record = _make_record(repo, slug="alpha", note_id=1, tags=["x"])
    repo.save(record)

    repo.update_tags(record, ["x", "y", "z"])

    reloaded = repo.find_by_id(1)
    assert reloaded.tags == ["x", "y", "z"]


def test_record_read_body_returns_empty_when_missing(repo):
    record = _make_record(repo, slug="alpha", note_id=1)
    # data file does not yet exist
    assert record.read_body() == ""


def test_record_read_body_reads_file(repo):
    record = _make_record(repo, slug="alpha", note_id=1)
    repo.save(record)
    record.data_path.write_text("hello world")
    assert record.read_body() == "hello world"
