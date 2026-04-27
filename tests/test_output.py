from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from python_notes.output import (
    JsonFormatter,
    SearchHit,
    TextFormatter,
    UnknownFormatError,
    get_formatter,
)
from python_notes.storage import NoteRecord


def _record(
    *,
    note_id: int = 1,
    slug: str = "alpha",
    title: str = "Alpha",
    tags: list[str] | None = None,
    created: str = "2024-01-01_12_00_00",
) -> NoteRecord:
    return NoteRecord(
        id=note_id,
        title=title,
        safe_title=slug,
        tags=list(tags or []),
        creation_date=datetime(2024, 1, 1, 12, 0, 0),
        creation_date_as_str=created,
        metadata_path=Path(f"/tmp/{slug}_metadata"),
        data_path=Path(f"/tmp/{slug}_data.md"),
    )


# --------------------------------------------------------------- factory


def test_get_formatter_text():
    assert get_formatter("text").name == "text"


def test_get_formatter_json():
    assert get_formatter("json").name == "json"


def test_get_formatter_unknown_raises():
    with pytest.raises(UnknownFormatError) as exc_info:
        get_formatter("xml")
    assert "xml" in str(exc_info.value)
    assert "text" in str(exc_info.value)
    assert "json" in str(exc_info.value)


# ------------------------------------------------------------- text format


def test_text_record_list_empty():
    out = TextFormatter().format_record_list([])
    assert out == "No notes found"


def test_text_record_list_with_tags():
    out = TextFormatter().format_record_list(
        [_record(slug="alpha", tags=["a", "b"]), _record(slug="beta")]
    )
    assert out == "Notes:\n  alpha [a, b]\n  beta"


def test_text_tag_list_empty():
    assert TextFormatter().format_tag_list([]) == "No tags found"


def test_text_tag_list_sorted_unique():
    out = TextFormatter().format_tag_list(["b", "a", "a"])
    assert out == "All tags:\n  a\n  b"


def test_text_search_results_empty():
    out = TextFormatter().format_search_results([], query="zzz")
    assert out == "No notes found matching 'zzz'"


def test_text_search_results_with_hits():
    hit = SearchHit(record=_record(slug="alpha"), locations=["title", "body"])
    out = TextFormatter().format_search_results([hit], query="alpha")
    assert "Found 1 note(s) matching 'alpha':" in out
    assert "alpha" in out
    assert "(found in: title, body)" in out


# ------------------------------------------------------------- json format


def test_json_record_list_empty_is_array():
    out = JsonFormatter().format_record_list([])
    assert json.loads(out) == []


def test_json_record_list_shape():
    records = [_record(note_id=1, slug="alpha", title="Alpha", tags=["x"])]
    payload = json.loads(JsonFormatter().format_record_list(records))
    assert payload == [
        {
            "id": 1,
            "slug": "alpha",
            "title": "Alpha",
            "tags": ["x"],
            "created": "2024-01-01_12_00_00",
        }
    ]


def test_json_record_list_omits_filesystem_paths():
    """metadata_path and data_path are storage internals, not public API."""
    records = [_record(slug="alpha")]
    payload = json.loads(JsonFormatter().format_record_list(records))
    assert "metadata_path" not in payload[0]
    assert "data_path" not in payload[0]


def test_json_tag_list_is_sorted_array():
    out = JsonFormatter().format_tag_list(["b", "a", "a", "c"])
    assert json.loads(out) == ["a", "b", "c"]


def test_json_search_results_includes_matched_in():
    hit = SearchHit(record=_record(slug="alpha"), locations=["title", "tags"])
    payload = json.loads(JsonFormatter().format_search_results([hit], query="alpha"))
    assert payload[0]["matched_in"] == ["title", "tags"]
    assert payload[0]["slug"] == "alpha"


def test_json_handles_datetime_creation_date():
    """Even if a record carries a datetime, JSON serialization should not crash."""
    rec = _record()
    out = JsonFormatter().format_record_list([rec])
    payload = json.loads(out)
    assert payload[0]["created"] == "2024-01-01_12_00_00"
