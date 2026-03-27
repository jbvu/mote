"""CLI smoke tests for mote entry point."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from mote.cli import cli


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
