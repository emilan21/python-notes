"""Output formatters: convert domain objects to renderable strings.

Formatters do not print. They return strings. The CLI layer is responsible
for emitting them. This keeps formatters pure and trivially testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol

from ..storage import NoteRecord


@dataclass(frozen=True)
class SearchHit:
    """A search match: the record plus where the query was found."""

    record: NoteRecord
    locations: list[str]  # subset of {"title", "tags", "body"}


class UnknownFormatError(ValueError):
    """The requested format name is not registered."""


class Formatter(Protocol):
    name: str

    def format_record_list(self, records: Iterable[NoteRecord]) -> str: ...
    def format_tag_list(self, tags: Iterable[str]) -> str: ...
    def format_search_results(self, hits: Iterable[SearchHit], query: str) -> str: ...


# ---------------------------------------------------------------- text format


class TextFormatter:
    name = "text"

    def format_record_list(self, records: Iterable[NoteRecord]) -> str:
        records = list(records)
        if not records:
            return "No notes found"
        lines = ["Notes:"]
        for r in records:
            lines.append(self._record_line(r))
        return "\n".join(lines)

    def format_tag_list(self, tags: Iterable[str]) -> str:
        tags = sorted(set(tags))
        if not tags:
            return "No tags found"
        lines = ["All tags:"]
        for t in tags:
            lines.append(f"  {t}")
        return "\n".join(lines)

    def format_search_results(
        self, hits: Iterable[SearchHit], query: str
    ) -> str:
        hits = list(hits)
        if not hits:
            return f"No notes found matching '{query}'"
        lines = [f"Found {len(hits)} note(s) matching '{query}':"]
        for hit in hits:
            loc = f" (found in: {', '.join(hit.locations)})"
            lines.append(f"{self._record_line(hit.record)}{loc}")
        return "\n".join(lines)

    @staticmethod
    def _record_line(record: NoteRecord) -> str:
        tags = f" [{', '.join(record.tags)}]" if record.tags else ""
        return f"  {record.safe_title}{tags}"


# ---------------------------------------------------------------- json format


class JsonFormatter:
    name = "json"

    def format_record_list(self, records: Iterable[NoteRecord]) -> str:
        return json.dumps(
            [self._record_to_dict(r) for r in records],
            indent=2,
            default=_json_default,
        )

    def format_tag_list(self, tags: Iterable[str]) -> str:
        return json.dumps(sorted(set(tags)), indent=2)

    def format_search_results(
        self, hits: Iterable[SearchHit], query: str
    ) -> str:
        payload = [
            {
                **self._record_to_dict(hit.record),
                "matched_in": list(hit.locations),
            }
            for hit in hits
        ]
        return json.dumps(payload, indent=2, default=_json_default)

    @staticmethod
    def _record_to_dict(record: NoteRecord) -> dict:
        # Filesystem paths are storage internals, not part of the public API.
        return {
            "id": record.id,
            "slug": record.safe_title,
            "title": record.title,
            "tags": list(record.tags),
            "created": record.creation_date_as_str,
        }


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"object of type {type(value).__name__} is not JSON-serializable")


# ----------------------------------------------------------------- factory


_REGISTRY: dict[str, type[Formatter]] = {
    TextFormatter.name: TextFormatter,
    JsonFormatter.name: JsonFormatter,
}


def get_formatter(name: str) -> Formatter:
    """Return a formatter instance by name. Raises UnknownFormatError if unknown."""
    try:
        cls = _REGISTRY[name]
    except KeyError as exc:
        valid = ", ".join(sorted(_REGISTRY))
        raise UnknownFormatError(
            f"unknown format {name!r}; valid formats: {valid}"
        ) from exc
    return cls()
