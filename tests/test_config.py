from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from python_notes.config.config import (
    APP_NAME,
    CONFIG_FILENAME,
    Settings,
    config_path,
)


@pytest.fixture
def isolated_xdg(tmp_path, monkeypatch):
    """Point XDG_CONFIG_HOME and XDG_DATA_HOME at temp dirs, clear editor env."""
    cfg = tmp_path / "config"
    data = tmp_path / "data"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    return cfg, data


def test_config_path_uses_xdg(isolated_xdg):
    cfg, _ = isolated_xdg
    assert config_path() == cfg / APP_NAME / CONFIG_FILENAME


def test_config_path_falls_back_to_home(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    expected = tmp_path / ".config" / APP_NAME / CONFIG_FILENAME
    assert config_path() == expected


def test_default_settings(isolated_xdg):
    _, data = isolated_xdg
    s = Settings.default()
    assert s.notes_dir == data / APP_NAME / "notes"
    assert s.editor == "vi"
    assert s.default_output == "text"


def test_default_editor_prefers_visual_over_editor(isolated_xdg, monkeypatch):
    monkeypatch.setenv("EDITOR", "nano")
    monkeypatch.setenv("VISUAL", "code")
    assert Settings.default().editor == "code"


def test_default_editor_uses_editor_when_no_visual(isolated_xdg, monkeypatch):
    monkeypatch.setenv("EDITOR", "nano")
    assert Settings.default().editor == "nano"


def test_load_returns_defaults_when_missing(isolated_xdg):
    s = Settings.load()
    assert s == Settings.default()


def test_save_then_load_roundtrip(isolated_xdg, tmp_path):
    notes_dir = tmp_path / "my-notes"
    original = Settings(
        notes_dir=notes_dir, editor="hx", default_output="json"
    )
    written = original.save()
    assert written.exists()

    loaded = Settings.load()
    assert loaded == original


def test_load_merges_partial_config_with_defaults(isolated_xdg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"editor": "hx"}))

    s = Settings.load()
    defaults = Settings.default()
    assert s.editor == "hx"
    assert s.notes_dir == defaults.notes_dir
    assert s.default_output == defaults.default_output


def test_load_expands_user_in_notes_dir(isolated_xdg, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"notes_dir": "~/custom-notes"}))

    s = Settings.load()
    assert s.notes_dir == tmp_path / "custom-notes"


def test_load_rejects_non_mapping_yaml(isolated_xdg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("- just\n- a\n- list\n")

    with pytest.raises(ValueError):
        Settings.load()


def test_with_replaces_fields(isolated_xdg):
    s = Settings.default()
    s2 = s.with_(editor="hx")
    assert s2.editor == "hx"
    assert s2.notes_dir == s.notes_dir
    assert s is not s2  # frozen, replace returns a new instance


def test_settings_is_frozen(isolated_xdg):
    s = Settings.default()
    with pytest.raises(Exception):
        s.editor = "nope"  # type: ignore[misc]


def test_load_rejects_invalid_default_output(isolated_xdg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"default_output": "xml"}))
    with pytest.raises(ValueError) as exc_info:
        Settings.load()
    assert "xml" in str(exc_info.value)
