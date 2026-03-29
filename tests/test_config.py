"""Unit tests for mote configuration module."""

import os
import stat
import time
import tomlkit
import pytest
from pathlib import Path
from unittest.mock import patch

from mote.config import (
    get_config_dir,
    get_config_path,
    ensure_config,
    load_config,
    set_config_value,
    validate_config,
    cleanup_old_wavs,
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


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def _valid_cfg(tmp_path):
    """Build a minimal valid config dict for tests."""
    return {
        "transcription": {
            "engine": "local",
            "model": "kb-whisper-medium",
        },
        "output": {
            "dir": str(tmp_path / "transcripts"),
        },
        "api_keys": {
            "openai": "",
        },
    }


def test_validate_config_valid(tmp_path):
    """Valid config returns ([], []) — no errors, no warnings."""
    cfg = _valid_cfg(tmp_path)
    with (
        patch("mote.config.config_value_to_alias", return_value="medium"),
        patch("mote.config.is_model_downloaded", return_value=True),
    ):
        errors, warnings = validate_config(cfg)
    assert errors == []
    assert warnings == []


def test_validate_config_invalid_engine(tmp_path):
    """engine='invalid' returns error containing 'Invalid engine'."""
    cfg = _valid_cfg(tmp_path)
    cfg["transcription"]["engine"] = "invalid"
    with (
        patch("mote.config.config_value_to_alias", return_value="medium"),
        patch("mote.config.is_model_downloaded", return_value=True),
    ):
        errors, warnings = validate_config(cfg)
    assert any("Invalid engine" in e for e in errors)


def test_validate_config_missing_model(tmp_path):
    """engine=local with undownloaded model returns error containing 'not downloaded'."""
    cfg = _valid_cfg(tmp_path)
    with (
        patch("mote.config.config_value_to_alias", return_value="medium"),
        patch("mote.config.is_model_downloaded", return_value=False),
    ):
        errors, warnings = validate_config(cfg)
    assert any("not downloaded" in e for e in errors)


def test_validate_config_openai_no_key_warning(tmp_path):
    """engine=openai with no API key returns warning (not error) containing 'no api_keys.openai'."""
    cfg = _valid_cfg(tmp_path)
    cfg["transcription"]["engine"] = "openai"
    cfg["api_keys"]["openai"] = ""
    errors, warnings = validate_config(cfg)
    assert errors == []
    assert any("no api_keys.openai" in w for w in warnings)


def test_validate_config_v1_compat(tmp_path):
    """Config dict with no [cleanup] section returns no errors (D-06)."""
    cfg = _valid_cfg(tmp_path)
    # No cleanup section — v1 config
    with (
        patch("mote.config.config_value_to_alias", return_value="medium"),
        patch("mote.config.is_model_downloaded", return_value=True),
    ):
        errors, warnings = validate_config(cfg)
    assert errors == []


def test_validate_config_bad_output_dir(tmp_path):
    """Output dir is a file (not dir) returns error containing 'not a directory'."""
    cfg = _valid_cfg(tmp_path)
    # Create a file where output dir should be
    bad_path = tmp_path / "output_is_a_file"
    bad_path.write_text("I am a file")
    cfg["output"]["dir"] = str(bad_path)
    with (
        patch("mote.config.config_value_to_alias", return_value="medium"),
        patch("mote.config.is_model_downloaded", return_value=True),
    ):
        errors, warnings = validate_config(cfg)
    assert any("not a directory" in e for e in errors)


# ---------------------------------------------------------------------------
# cleanup_old_wavs
# ---------------------------------------------------------------------------


def test_cleanup_old_wavs_deletes_expired(tmp_path):
    """WAV older than retention_days is deleted."""
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    old_wav = recordings_dir / "old.wav"
    old_wav.write_bytes(b"RIFF")
    # Set mtime to 10 days ago
    old_time = time.time() - (10 * 86400)
    os.utime(old_wav, (old_time, old_time))

    deleted = cleanup_old_wavs(recordings_dir, retention_days=7)
    assert old_wav in deleted
    assert not old_wav.exists()


def test_cleanup_old_wavs_keeps_recent(tmp_path):
    """WAV newer than retention_days is kept."""
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    recent_wav = recordings_dir / "recent.wav"
    recent_wav.write_bytes(b"RIFF")
    # Leave mtime as-is (just created = very recent)

    deleted = cleanup_old_wavs(recordings_dir, retention_days=7)
    assert deleted == []
    assert recent_wav.exists()


def test_cleanup_old_wavs_empty_dir(tmp_path):
    """Nonexistent dir returns empty list."""
    nonexistent = tmp_path / "no_such_dir"
    deleted = cleanup_old_wavs(nonexistent, retention_days=7)
    assert deleted == []


# ---------------------------------------------------------------------------
# Default config has [cleanup] section
# ---------------------------------------------------------------------------


def test_default_config_has_cleanup_section(mote_home):
    """ensure_config() creates config with [cleanup] and wav_retention_days = 7."""
    ensure_config()
    cfg = load_config()
    assert "cleanup" in cfg
    assert cfg["cleanup"]["wav_retention_days"] == 7
