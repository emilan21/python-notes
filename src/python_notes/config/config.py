from __future__ import annotations

import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import yaml

APP_NAME = "python-notes"
CONFIG_FILENAME = "config.yaml"
VALID_OUTPUT_FORMATS = ("text", "json")


@dataclass(frozen=True)
class Settings:
    notes_dir: Path
    editor: str
    default_output: str

    @classmethod
    def default(cls) -> "Settings":
        return cls(
            notes_dir=_default_notes_dir(),
            editor=_default_editor(),
            default_output="text",
        )

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        """Load settings from disk, falling back to defaults for missing keys.

        If the config file does not exist, defaults are returned silently.
        Side-effect free: does not create directories or files.
        """
        path = path or config_path()
        defaults = cls.default()
        if not path.exists():
            return defaults

        with path.open("r") as f:
            raw = yaml.safe_load(f) or {}

        if not isinstance(raw, dict):
            raise ValueError(f"Config file {path} is not a YAML mapping")

        notes_dir = raw.get("notes_dir")
        notes_dir_path = (
            Path(os.path.expandvars(str(notes_dir))).expanduser()
            if notes_dir
            else defaults.notes_dir
        )

        default_output = raw.get("default_output", defaults.default_output)
        if default_output not in VALID_OUTPUT_FORMATS:
            valid = ", ".join(VALID_OUTPUT_FORMATS)
            raise ValueError(
                f"Config file {path}: invalid default_output {default_output!r}; "
                f"valid: {valid}"
            )

        return cls(
            notes_dir=notes_dir_path,
            editor=raw.get("editor", defaults.editor),
            default_output=default_output,
        )

    def save(self, path: Path | None = None) -> Path:
        """Serialize settings to YAML on disk. Returns the path written."""
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        # Path is not YAML-serializable as-is; store as string
        data["notes_dir"] = str(self.notes_dir)

        with path.open("w") as f:
            yaml.safe_dump(data, f, sort_keys=True)
        return path

    def with_(self, **changes) -> "Settings":
        """Return a new Settings with the given fields replaced."""
        return replace(self, **changes)


def config_path() -> Path:
    """Return the canonical config file path, respecting $XDG_CONFIG_HOME."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME / CONFIG_FILENAME


def _default_notes_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(base) / APP_NAME / "notes"


def _default_editor() -> str:
    """Editor lookup order: $VISUAL, $EDITOR, then "vi"."""
    return os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
