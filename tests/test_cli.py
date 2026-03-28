"""CLI smoke tests for mote entry point."""

import os
import wave as wave_mod
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from mote.cli import cli


def _make_test_wav(path: Path) -> Path:
    """Create a minimal valid WAV file for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = 16000  # 1 second
    with wave_mod.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * n_frames)
    return path


def test_help():
    """mote --help exits 0 and shows description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Mote" in result.output


def test_version():
    """mote --version exits 0 and shows version string."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_config_group_help():
    """mote config --help exits 0 and shows config description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "View and edit" in result.output


def test_config_show(mote_home):
    """mote config show prints config contents with default values."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert "language" in result.output
    assert "sv" in result.output
    assert "engine" in result.output


def test_config_set(mote_home):
    """mote config set updates a value in the config file."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "set", "general.language", "en"],
                           env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert "Set general.language = en" in result.output
    # Verify the value was actually written
    show = runner.invoke(cli, ["config", "show"], env={"MOTE_HOME": str(mote_home)})
    assert 'language = "en"' in show.output


def test_config_set_invalid_key(mote_home):
    """mote config set with invalid key shows error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "set", "nonexistent.key", "val"],
                           env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code != 0


def test_config_path(mote_home):
    """mote config path prints the config file path."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "path"],
                           env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert str(mote_home) in result.output
    assert "config.toml" in result.output


# ---------------------------------------------------------------------------
# record and status command tests
# ---------------------------------------------------------------------------

def test_record_help():
    """mote record --help exits 0 and output contains Start recording."""
    runner = CliRunner()
    result = runner.invoke(cli, ["record", "--help"])
    assert result.exit_code == 0
    assert "Start recording" in result.output


def test_status_help():
    """mote status --help exits 0 and output mentions status or Show."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0
    assert "Show" in result.output or "status" in result.output.lower()


def test_status_idle(mote_home):
    """mote status with no PID file reports Idle."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert "Idle" in result.output


def test_status_recording(mote_home):
    """mote status with PID file containing current PID reports Recording in progress."""
    pid_path = mote_home / "mote.pid"
    pid_path.write_text(str(os.getpid()))
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert "Recording in progress" in result.output


def test_status_stale_pid(mote_home):
    """mote status with stale PID (dead process) reports Idle and cleans up."""
    pid_path = mote_home / "mote.pid"
    pid_path.write_text("99999999")
    runner = CliRunner()
    result = runner.invoke(cli, ["status"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert "Idle" in result.output
    # Stale PID file should be removed
    assert not pid_path.exists()


def test_record_no_blackhole(mote_home):
    """mote record with no BlackHole device exits non-zero with install instructions."""
    runner = CliRunner()
    with patch("mote.cli.find_blackhole_device", return_value=None):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code != 0
    assert "BlackHole" in result.output
    assert "brew install blackhole-2ch" in result.output


def test_record_already_active(mote_home):
    """mote record when recording already active exits non-zero with clear message."""
    pid_path = mote_home / "mote.pid"
    pid_path.write_text(str(os.getpid()))
    runner = CliRunner()
    result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code != 0
    assert "already" in result.output.lower() or "in progress" in result.output.lower()


def test_record_stale_pid_allows_start(mote_home):
    """mote record with stale PID cleans it up and proceeds to record."""
    pid_path = mote_home / "mote.pid"
    pid_path.write_text("99999999")
    fake_device = {"name": "BlackHole 2ch", "index": 0, "max_input_channels": 2}
    fake_wav = mote_home / "recordings" / "mote_20260327_000000.wav"
    runner = CliRunner()
    with patch("mote.cli.find_blackhole_device", return_value=fake_device), \
         patch("mote.cli.record_session", return_value=fake_wav) as mock_rec:
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})
    # Stale PID warning should be shown
    assert "stale" in result.output.lower() or "dead" in result.output.lower()
    # record_session should have been called
    mock_rec.assert_called_once()


def test_models_group_help():
    """mote models --help exits 0 and mentions transcription models."""
    runner = CliRunner()
    result = runner.invoke(cli, ["models", "--help"])
    assert result.exit_code == 0
    assert "Manage" in result.output or "transcription" in result.output.lower() or "model" in result.output.lower()


def test_record_orphan_warning(mote_home):
    """mote record with existing WAV files warns about orphaned recordings."""
    recordings_dir = mote_home / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    orphan = recordings_dir / "mote_20260101_120000.wav"
    orphan.write_bytes(b"RIFF" + b"\x00" * 100)  # minimal fake WAV content
    fake_device = {"name": "BlackHole 2ch", "index": 0, "max_input_channels": 2}
    fake_wav = recordings_dir / "mote_20260327_000000.wav"
    runner = CliRunner()
    with patch("mote.cli.find_blackhole_device", return_value=fake_device), \
         patch("mote.cli.record_session", return_value=fake_wav):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})
    # Orphan warning should mention the WAV file or use "Found" / "orphan"
    combined = result.output.lower()
    assert "found" in combined or "orphan" in combined or "mote_20260101_120000.wav" in result.output


# ---------------------------------------------------------------------------
# Auto-transcription CLI tests (Plan 02)
# ---------------------------------------------------------------------------


def test_record_auto_transcribes(mote_home):
    """After recording, transcribe_file is called with engine/language from config defaults."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world") as mock_tx:
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_tx.assert_called_once()
    # First positional arg is wav_path, second is engine
    call_args = mock_tx.call_args[0]
    assert call_args[1] == "local"   # default engine
    assert call_args[2] == "sv"      # default language
    assert "Transcription complete" in result.output


def test_record_engine_flag(mote_home):
    """--engine openai overrides config's default local engine."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.get_wav_duration", return_value=30.0), \
         patch("mote.cli.transcribe_file", return_value="hej världen") as mock_tx:
        result = runner.invoke(cli, ["record", "--engine", "openai"],
                               env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_tx.assert_called_once()
    call_args = mock_tx.call_args[0]
    assert call_args[1] == "openai"


def test_record_language_flag(mote_home):
    """--language en overrides config's default sv language."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.get_wav_duration", return_value=30.0), \
         patch("mote.cli.transcribe_file", return_value="hello world") as mock_tx:
        result = runner.invoke(cli, ["record", "--language", "en"],
                               env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_tx.assert_called_once()
    call_args = mock_tx.call_args[0]
    assert call_args[2] == "en"


def test_record_no_transcribe_flag(mote_home):
    """--no-transcribe skips transcribe_file call entirely, WAV file kept."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.transcribe_file") as mock_tx:
        result = runner.invoke(cli, ["record", "--no-transcribe"],
                               env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_tx.assert_not_called()
    assert wav.exists()


def test_record_deletes_wav_on_success(mote_home):
    """After successful transcription, the WAV file is deleted."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.get_wav_duration", return_value=90.0), \
         patch("mote.cli.transcribe_file", return_value="transcript text"):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert not wav.exists()


def test_record_keeps_wav_on_failure(mote_home):
    """When transcribe_file raises Exception, WAV file is kept on disk."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.get_wav_duration", return_value=45.0), \
         patch("mote.cli.transcribe_file", side_effect=Exception("network error")):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    assert wav.exists()
    assert "WAV kept at" in result.output
