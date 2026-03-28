"""Unit tests for mote configuration module."""

import stat
import tomlkit
import pytest
from pathlib import Path

from mote.config import (
    get_config_dir,
    get_config_path,
    ensure_config,
    load_config,
    set_config_value,
)


def test_config_path(mote_home):
    """get_config_path() returns path ending with .mote/config.toml and respects MOTE_HOME."""
    path = get_config_path()
    assert str(path).endswith("config.toml")
    assert str(mote_home) in str(path)


def test_default_config_created(mote_home):
    """ensure_config() creates config.toml when it does not exist."""
    path = ensure_config()
    assert path.exists()
    content = path.read_text()
    assert "[general]" in content
    assert "[transcription]" in content
    assert "[output]" in content


def test_default_config_language(mote_home):
    """Default config has general.language = 'sv'."""
    ensure_config()
    cfg = load_config()
    assert cfg["general"]["language"] == "sv"


def test_default_config_engine(mote_home):
    """Default config has transcription.engine = 'local'."""
    ensure_config()
    cfg = load_config()
    assert cfg["transcription"]["engine"] == "local"


def test_default_config_model(mote_home):
    """Default config has transcription.model = 'kb-whisper-medium'."""
    ensure_config()
    cfg = load_config()
    assert cfg["transcription"]["model"] == "kb-whisper-medium"


def test_default_config_output_format(mote_home):
    """Default config has output.format = ['markdown', 'txt']."""
    ensure_config()
    cfg = load_config()
    assert list(cfg["output"]["format"]) == ["markdown", "txt"]


def test_default_config_output_dir(mote_home):
    """Default config has output.dir containing 'Documents/mote'."""
    ensure_config()
    cfg = load_config()
    assert "Documents/mote" in cfg["output"]["dir"]


def test_config_permissions(mote_home):
    """Config file has mode 0o600 after creation."""
    path = ensure_config()
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600


def test_env_var_override_openai(mote_home, monkeypatch):
    """Set OPENAI_API_KEY env var, load_config() returns it at api_keys.openai."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    cfg = load_config()
    assert cfg["api_keys"]["openai"] == "sk-test-openai-key"


def test_env_var_override_mistral(mote_home, monkeypatch):
    """Set MISTRAL_API_KEY env var, load_config() returns it at api_keys.mistral."""
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral-key")
    cfg = load_config()
    assert cfg["api_keys"]["mistral"] == "test-mistral-key"


def test_env_var_does_not_persist_to_file(mote_home, monkeypatch):
    """After load_config() with env var set, re-reading file does NOT contain the env var value."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-written")
    load_config()
    # Re-read raw file
    path = get_config_path()
    with path.open() as f:
        raw = tomlkit.load(f)
    # api_keys section exists (with empty defaults) but env var value must not be written
    assert raw.get("api_keys", {}).get("openai", "") != "sk-should-not-be-written"


def test_set_config_value(mote_home):
    """set_config_value('general.language', 'en') changes the value in the file."""
    ensure_config()
    set_config_value("general.language", "en")
    cfg = load_config()
    assert cfg["general"]["language"] == "en"


def test_set_config_preserves_permissions(mote_home):
    """After set_config_value(), file still has mode 0o600."""
    ensure_config()
    set_config_value("general.language", "en")
    path = get_config_path()
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600
