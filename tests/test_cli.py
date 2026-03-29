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
    with patch("mote.cli.find_blackhole_device", return_value=None), \
         patch("mote.cli.validate_config", return_value=([], [])):
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
         patch("mote.cli.record_session", return_value=fake_wav) as mock_rec, \
         patch("mote.cli.validate_config", return_value=([], [])):
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
    """mote record with existing WAV files warns about orphaned recordings and points to mote transcribe."""
    recordings_dir = mote_home / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    orphan = recordings_dir / "mote_20260101_120000.wav"
    orphan.write_bytes(b"RIFF" + b"\x00" * 100)  # minimal fake WAV content
    fake_device = {"name": "BlackHole 2ch", "index": 0, "max_input_channels": 2}
    fake_wav = recordings_dir / "mote_20260327_000000.wav"
    runner = CliRunner()
    with patch("mote.cli.find_blackhole_device", return_value=fake_device), \
         patch("mote.cli.record_session", return_value=fake_wav), \
         patch("mote.cli.validate_config", return_value=([], [])):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})
    # Orphan warning should mention the WAV file or use "Found" / "orphan"
    combined = result.output.lower()
    assert "found" in combined or "orphan" in combined or "mote_20260101_120000.wav" in result.output
    # D-02: orphan warning must include pointer to mote transcribe command
    assert "mote transcribe" in result.output


# ---------------------------------------------------------------------------
# Auto-transcription CLI tests (Plan 02)
# ---------------------------------------------------------------------------


def test_record_auto_transcribes(mote_home):
    """After recording, transcribe_file is called with engine/language from config defaults."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md", out_dir / "2026-01-01_0000.txt"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world") as mock_tx, \
         patch("mote.cli.write_transcript", return_value=fake_written):
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
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=30.0), \
         patch("mote.cli.transcribe_file", return_value="hej världen") as mock_tx, \
         patch("mote.cli.write_transcript", return_value=fake_written):
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
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=30.0), \
         patch("mote.cli.transcribe_file", return_value="hello world") as mock_tx, \
         patch("mote.cli.write_transcript", return_value=fake_written):
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
         patch("mote.cli.validate_config", return_value=([], [])), \
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
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=90.0), \
         patch("mote.cli.transcribe_file", return_value="transcript text"), \
         patch("mote.cli.write_transcript", return_value=fake_written):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert not wav.exists()


def test_record_keeps_wav_on_failure(mote_home):
    """When transcribe_file raises Exception, WAV file is kept on disk."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=45.0), \
         patch("mote.cli.transcribe_file", side_effect=Exception("network error")):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)},
                               input="n\n")

    assert result.exit_code != 0
    assert wav.exists()
    assert "WAV kept at" in result.output


# ---------------------------------------------------------------------------
# Output write wiring and list command tests (Plan 02)
# ---------------------------------------------------------------------------


def test_record_writes_output_files(mote_home):
    """After transcription, write_transcript is called and output files are produced."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write real files so we can assert their existence
    md_file = out_dir / "2026-03-28_1000.md"
    txt_file = out_dir / "2026-03-28_1000.txt"
    md_file.write_text("---\ndate: 2026-03-28T10:00:00\nduration: 322\nwords: 2\nengine: local\nlanguage: sv\nmodel: medium\n---\n\nhello world", encoding="utf-8")
    txt_file.write_text("hello world", encoding="utf-8")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=322.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", return_value=[md_file, txt_file]) as mock_write:
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_write.assert_called_once()
    assert md_file.exists()
    assert txt_file.exists()
    # Summary line should contain arrow and filenames
    assert "\u2192" in result.output
    assert "2026-03-28_1000.md" in result.output


def test_record_name_flag(mote_home):
    """--name standup produces output filenames containing 'standup'."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    named_file = out_dir / "2026-03-28_1000_standup.md"

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", return_value=[named_file]) as mock_write:
        result = runner.invoke(cli, ["record", "--name", "standup"],
                               env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_write.assert_called_once()
    # The name passed to write_transcript should be the sanitized form
    call_kwargs = mock_write.call_args
    # name is the 8th positional arg (index 7) or keyword arg
    call_args = call_kwargs[0]
    assert call_args[7] == "standup"  # sanitized name
    # Summary line contains the named file
    assert "standup" in result.output


def test_record_deletes_wav_after_write(mote_home):
    """WAV file is deleted only after write_transcript() succeeds."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_file = out_dir / "2026-03-28_1000.md"

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=90.0), \
         patch("mote.cli.transcribe_file", return_value="transcript text"), \
         patch("mote.cli.write_transcript", return_value=[fake_file]):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert not wav.exists(), "WAV should be deleted after successful write"


def test_record_keeps_wav_on_write_failure(mote_home):
    """WAV file is kept on disk if write_transcript() raises an exception."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", side_effect=OSError("disk full")):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)},
                               input="n\n")

    assert result.exit_code != 0 or "WAV kept at" in result.output
    assert wav.exists(), "WAV must be kept when write_transcript raises"


def test_list_command(mote_home):
    """mote list shows a Rich table with transcript metadata."""
    from mote.output import write_transcript
    from datetime import datetime

    runner = CliRunner()
    out_dir = mote_home / "transcripts"

    # Create 2 .md files via write_transcript
    write_transcript(
        "transcript one", out_dir, ["markdown"], 120.0, "local", "sv", "medium",
        name="meeting-one", timestamp=datetime(2026, 3, 28, 10, 0, 0),
    )
    write_transcript(
        "transcript two three", out_dir, ["markdown"], 300.0, "openai", "en", "medium",
        name="meeting-two", timestamp=datetime(2026, 3, 28, 11, 0, 0),
    )

    # Point output.dir at our tmp dir
    with patch("mote.cli.load_config", return_value={"output": {"dir": str(out_dir), "format": ["markdown"]}}):
        result = runner.invoke(cli, ["list"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "Recent Transcripts" in result.output
    # Rich may truncate long filenames; check for partial match of distinct parts
    assert "meeting-o" in result.output  # meeting-one (possibly truncated)
    assert "meeting-t" in result.output  # meeting-two (possibly truncated)


def test_list_command_empty(mote_home):
    """mote list with empty output dir shows 'No transcripts found.'"""
    runner = CliRunner()
    out_dir = mote_home / "transcripts"

    with patch("mote.cli.load_config", return_value={"output": {"dir": str(out_dir), "format": ["markdown"]}}):
        result = runner.invoke(cli, ["list"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "No transcripts found." in result.output


def test_list_command_all_flag(mote_home):
    """mote list without --all shows max 20 entries; with --all shows all 25."""
    from mote.output import write_transcript
    from datetime import datetime, timedelta

    runner = CliRunner()
    out_dir = mote_home / "transcripts"

    # Create 25 .md files with distinct timestamps (1 minute apart)
    base = datetime(2026, 3, 1, 0, 0, 0)
    for i in range(25):
        ts = base + timedelta(minutes=i)
        write_transcript(
            f"text {i}", out_dir, ["markdown"], 60.0, "local", "sv", "medium",
            name=f"m{i:02d}", timestamp=ts,
        )

    with patch("mote.cli.load_config", return_value={"output": {"dir": str(out_dir), "format": ["markdown"]}}):
        result_limited = runner.invoke(cli, ["list"], env={"MOTE_HOME": str(mote_home)})
        result_all = runner.invoke(cli, ["list", "--all"], env={"MOTE_HOME": str(mote_home)})

    assert result_limited.exit_code == 0
    assert result_all.exit_code == 0

    # Count table rows by counting occurrences of ".md" in the output
    # Each row contains the filename which ends in .md
    all_count = result_all.output.count(".md")
    limited_count = result_limited.output.count(".md")

    assert all_count == 25, f"Expected 25 rows in --all output, got {all_count}"
    assert limited_count == 20, f"Expected 20 rows in limited output, got {limited_count}"


# ---------------------------------------------------------------------------
# _run_transcription() helper tests (Plan 06-02, Task 1)
# ---------------------------------------------------------------------------


def test_run_transcription_calls_pipeline(mote_home, tmp_path):
    """_run_transcription calls get_wav_duration, transcribe_file, write_transcript, wav.unlink in order."""
    from mote.cli import _run_transcription

    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = tmp_path / "out"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.get_wav_duration", return_value=60.0) as mock_dur, \
         patch("mote.cli.transcribe_file", return_value="hello world") as mock_tx, \
         patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        result_paths = _run_transcription(
            wav, "local", "sv", "medium", None, out_dir, ["markdown"], None,
        )

    mock_dur.assert_called_once_with(wav)
    mock_tx.assert_called_once_with(wav, "local", "sv", "medium", None)
    mock_write.assert_called_once()
    # WAV should be deleted (delete_wav=True by default)
    assert not wav.exists()
    assert result_paths == fake_written


def test_run_transcription_passes_formats(mote_home, tmp_path):
    """_run_transcription passes the formats list to write_transcript."""
    from mote.cli import _run_transcription

    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = tmp_path / "out"
    fake_written = [out_dir / "2026-01-01_0000.md", out_dir / "2026-01-01_0000.json"]

    with patch("mote.cli.get_wav_duration", return_value=30.0), \
         patch("mote.cli.transcribe_file", return_value="transcript"), \
         patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        _run_transcription(
            wav, "local", "sv", "medium", None, out_dir, ["markdown", "json"], None,
        )

    call_args = mock_write.call_args[0]
    # formats is the 3rd positional arg (index 2)
    assert "json" in call_args[2]
    assert "markdown" in call_args[2]


def test_record_with_output_format_json(mote_home):
    """mote record --output-format json includes 'json' in formats passed to write_transcript."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="transcript"), \
         patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        result = runner.invoke(
            cli, ["record", "--output-format", "json"],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    mock_write.assert_called_once()
    call_args = mock_write.call_args[0]
    # formats is the 3rd positional arg (index 2)
    assert "json" in call_args[2]


# ---------------------------------------------------------------------------
# mote transcribe command tests (Plan 06-02, Task 2)
# ---------------------------------------------------------------------------


def test_transcribe_command(mote_home, tmp_path):
    """mote transcribe <wav> produces transcript output and prints completion message."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hej världen"), \
         patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        result = runner.invoke(
            cli, ["transcribe", str(wav)],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    mock_write.assert_called_once()
    assert "Transcription complete" in result.output


def test_transcribe_flags(mote_home, tmp_path):
    """--engine, --language, --name flags are passed through to _run_transcription."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000_standup.md"]

    with patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=30.0), \
         patch("mote.cli.transcribe_file", return_value="text") as mock_tx, \
         patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        result = runner.invoke(
            cli,
            ["transcribe", str(wav), "--engine", "openai", "--language", "en", "--name", "standup"],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    tx_args = mock_tx.call_args[0]
    assert tx_args[1] == "openai"
    assert tx_args[2] == "en"
    write_args = mock_write.call_args[0]
    assert write_args[7] == "standup"


def test_transcribe_output_format_json(mote_home, tmp_path):
    """--output-format json includes 'json' in formats passed to write_transcript."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md", out_dir / "2026-01-01_0000.json"]

    with patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        result = runner.invoke(
            cli, ["transcribe", str(wav), "--output-format", "json"],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    call_args = mock_write.call_args[0]
    assert "json" in call_args[2]


def test_transcribe_nonexistent_file(mote_home):
    """mote transcribe nonexistent.wav exits with error."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["transcribe", "/tmp/does_not_exist_ever.wav"],
        env={"MOTE_HOME": str(mote_home)},
    )
    assert result.exit_code != 0


def test_transcribe_overwrite_prompt(mote_home, tmp_path):
    """When output file exists, prompts user; answering no aborts."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Predict the output filename using WAV mtime
    from datetime import datetime
    from mote.output import _build_filename
    ts = datetime.fromtimestamp(wav.stat().st_mtime)
    existing_file = out_dir / _build_filename(ts, None, "md")
    existing_file.write_text("existing content", encoding="utf-8")

    with patch("mote.cli.load_config", return_value={
        "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
        "output": {"dir": str(out_dir), "format": ["markdown"]},
        "api_keys": {},
    }), patch("mote.cli.validate_config", return_value=([], [])), \
       patch("mote.cli.get_wav_duration", return_value=60.0), \
       patch("mote.cli.transcribe_file", return_value="text"), \
       patch("mote.cli.write_transcript", return_value=[existing_file]):
        result = runner.invoke(
            cli, ["transcribe", str(wav)],
            env={"MOTE_HOME": str(mote_home)},
            input="n\n",  # answer no to overwrite prompt
        )

    assert result.exit_code != 0
    assert "existing" in result.output.lower() or "overwrite" in result.output.lower() or "Aborted" in result.output


def test_transcribe_uses_wav_mtime(mote_home, tmp_path):
    """Timestamp passed to write_transcript comes from WAV file mtime, not datetime.now()."""
    import os
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    # Set a known old mtime on the WAV file
    old_mtime = 1700000000.0  # 2023-11-14
    os.utime(wav, (old_mtime, old_mtime))

    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2023-11-14_0933.md"]

    from datetime import datetime
    with patch("mote.cli.load_config", return_value={
        "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
        "output": {"dir": str(out_dir), "format": ["markdown"]},
        "api_keys": {},
    }), patch("mote.cli.validate_config", return_value=([], [])), \
       patch("mote.cli.get_wav_duration", return_value=60.0), \
       patch("mote.cli.transcribe_file", return_value="text"), \
       patch("mote.cli.write_transcript", return_value=fake_written) as mock_write:
        result = runner.invoke(
            cli, ["transcribe", str(wav)],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    # The timestamp keyword arg passed to write_transcript should match WAV mtime
    call_kwargs = mock_write.call_args[1]
    ts = call_kwargs.get("timestamp")
    assert ts is not None
    expected_ts = datetime.fromtimestamp(old_mtime)
    assert ts == expected_ts


# ---------------------------------------------------------------------------
# Plan 06-03, Task 1: Retry loop, validation wiring, orphan enhancement, auto-cleanup
# ---------------------------------------------------------------------------


def test_transcribe_retry_yes(mote_home, tmp_path):
    """On transcription failure, user answers yes -> retranscription succeeds."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("API timeout")
        return "transcript text"

    with patch("mote.cli.load_config", return_value={
        "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
        "output": {"dir": str(out_dir), "format": ["markdown"]},
        "api_keys": {},
    }), patch("mote.cli.validate_config", return_value=([], [])), \
       patch("mote.cli.get_wav_duration", return_value=60.0), \
       patch("mote.cli.transcribe_file", side_effect=side_effect), \
       patch("mote.cli.write_transcript", return_value=fake_written):
        result = runner.invoke(
            cli, ["transcribe", str(wav)],
            env={"MOTE_HOME": str(mote_home)},
            input="y\n",
        )

    assert result.exit_code == 0, result.output
    assert "Transcription complete" in result.output
    assert call_count["n"] == 2


def test_transcribe_retry_no(mote_home, tmp_path):
    """On transcription failure, user answers no -> exits with WAV kept at message."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"

    with patch("mote.cli.load_config", return_value={
        "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
        "output": {"dir": str(out_dir), "format": ["markdown"]},
        "api_keys": {},
    }), patch("mote.cli.validate_config", return_value=([], [])), \
       patch("mote.cli.get_wav_duration", return_value=60.0), \
       patch("mote.cli.transcribe_file", side_effect=RuntimeError("API timeout")):
        result = runner.invoke(
            cli, ["transcribe", str(wav)],
            env={"MOTE_HOME": str(mote_home)},
            input="n\n",
        )

    assert result.exit_code != 0
    assert "WAV kept at" in result.output


def test_record_retry_yes(mote_home):
    """On transcription failure during record, user answers yes -> retranscription succeeds."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("API timeout")
        return "transcript text"

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", side_effect=side_effect), \
         patch("mote.cli.write_transcript", return_value=fake_written):
        result = runner.invoke(
            cli, ["record"],
            env={"MOTE_HOME": str(mote_home)},
            input="y\n",
        )

    assert result.exit_code == 0, result.output
    assert "Transcription complete" in result.output
    assert call_count["n"] == 2


def test_record_validates_engine(mote_home):
    """mote record with invalid engine in config exits before any recording."""
    import tomlkit
    # Write a config with an invalid engine
    config_path = mote_home / "config.toml"
    doc = tomlkit.document()
    transcription = tomlkit.table()
    transcription.add("engine", "invalid")
    transcription.add("language", "sv")
    transcription.add("model", "kb-whisper-medium")
    doc.add("transcription", transcription)
    config_path.write_text(tomlkit.dumps(doc))
    config_path.chmod(0o600)

    runner = CliRunner()
    with patch("mote.cli.find_blackhole_device") as mock_bh, \
         patch("mote.cli.record_session") as mock_rec:
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    combined = result.output.lower()
    assert "invalid engine" in combined or "invalid" in combined
    mock_bh.assert_not_called()
    mock_rec.assert_not_called()


def test_record_validates_model(mote_home):
    """mote record with engine=local and undownloaded model exits before recording."""
    runner = CliRunner()
    # Default config uses engine=local; model won't be downloaded in CI
    with patch("mote.cli.find_blackhole_device") as mock_bh, \
         patch("mote.cli.record_session") as mock_rec, \
         patch("mote.cli.is_model_downloaded", return_value=False):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    assert "not downloaded" in result.output.lower() or "model" in result.output.lower()
    mock_bh.assert_not_called()
    mock_rec.assert_not_called()


def test_transcribe_validates_engine(mote_home, tmp_path):
    """mote transcribe with invalid engine in config exits with error before transcription."""
    import tomlkit
    # Write a config with an invalid engine
    config_path = mote_home / "config.toml"
    doc = tomlkit.document()
    transcription = tomlkit.table()
    transcription.add("engine", "invalid")
    transcription.add("language", "sv")
    transcription.add("model", "kb-whisper-medium")
    doc.add("transcription", transcription)
    config_path.write_text(tomlkit.dumps(doc))
    config_path.chmod(0o600)

    wav = _make_test_wav(tmp_path / "test.wav")
    runner = CliRunner()
    with patch("mote.cli.transcribe_file") as mock_tx:
        result = runner.invoke(
            cli, ["transcribe", str(wav)],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code != 0
    combined = result.output.lower()
    assert "invalid engine" in combined or "invalid" in combined
    mock_tx.assert_not_called()


def test_record_auto_cleanup(mote_home):
    """mote record startup silently runs cleanup_old_wavs before orphan check."""
    import os
    import time
    recordings_dir = mote_home / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    old_wav = recordings_dir / "mote_20200101_120000.wav"
    old_wav.write_bytes(b"RIFF" + b"\x00" * 100)
    # Set mtime to 30 days ago
    old_mtime = time.time() - (30 * 86400)
    os.utime(old_wav, (old_mtime, old_mtime))

    fake_wav = recordings_dir / "mote_20260327_000000.wav"
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=fake_wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written):
        result = runner_invoke = CliRunner().invoke(
            cli, ["record"],
            env={"MOTE_HOME": str(mote_home)},
        )

    # The old WAV should have been deleted by auto-cleanup
    assert not old_wav.exists(), "Auto-cleanup should have deleted expired WAV"


# ---------------------------------------------------------------------------
# Plan 06-03, Task 2: mote config validate and mote cleanup commands
# ---------------------------------------------------------------------------


def test_config_validate_command_clean(mote_home):
    """mote config validate with valid config (mocked) prints 'Configuration OK' and exits 0."""
    runner = CliRunner()
    with patch("mote.cli.validate_config", return_value=([], [])):
        result = runner.invoke(cli, ["config", "validate"],
                               env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0, result.output
    assert "Configuration OK" in result.output


def test_config_validate_command_errors(mote_home):
    """mote config validate with invalid engine prints error and exits non-zero."""
    runner = CliRunner()
    with patch("mote.cli.validate_config", return_value=(["Invalid engine 'bad'"], [])):
        result = runner.invoke(cli, ["config", "validate"],
                               env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code != 0
    assert "Invalid engine" in result.output or "error" in result.output.lower()


def test_config_validate_command_warnings(mote_home):
    """mote config validate with openai engine and no key prints warning but exits 0."""
    runner = CliRunner()
    with patch("mote.cli.validate_config", return_value=([], ["engine=openai but no api_keys.openai set."])):
        result = runner.invoke(cli, ["config", "validate"],
                               env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0, result.output
    assert "Warning" in result.output or "warning" in result.output.lower()
    assert "Configuration OK" in result.output


def test_cleanup_command_deletes(mote_home):
    """mote cleanup with expired WAVs prints 'Deleted N file(s)'."""
    import os
    import time
    recordings_dir = mote_home / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    old_wav = recordings_dir / "old_recording.wav"
    old_wav.write_bytes(b"RIFF" + b"\x00" * 100)
    # Set mtime to 30 days ago (way beyond default 7-day retention)
    old_mtime = time.time() - (30 * 86400)
    os.utime(old_wav, (old_mtime, old_mtime))

    runner = CliRunner()
    result = runner.invoke(cli, ["cleanup"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "Deleted" in result.output
    assert not old_wav.exists()


def test_cleanup_command_nothing(mote_home):
    """mote cleanup with no expired WAVs prints 'No expired WAV files found'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["cleanup"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0, result.output
    assert "No expired WAV files found" in result.output


def test_cleanup_command_retention_zero(mote_home):
    """mote cleanup with wav_retention_days=0 prints 'WAV retention disabled'."""
    import tomlkit
    config_path = mote_home / "config.toml"
    doc = tomlkit.document()
    cleanup_table = tomlkit.table()
    cleanup_table.add("wav_retention_days", 0)
    doc.add("cleanup", cleanup_table)
    config_path.write_text(tomlkit.dumps(doc))
    config_path.chmod(0o600)

    runner = CliRunner()
    result = runner.invoke(cli, ["cleanup"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0, result.output
    assert "retention disabled" in result.output.lower() or "disabled" in result.output.lower()


# ---------------------------------------------------------------------------
# Plan 07-02, Task 1: SwitchAudioSource helpers and audio_restore.json lifecycle
# ---------------------------------------------------------------------------


def test_detect_switch_audio_source_found():
    """_detect_switch_audio_source returns True when shutil.which finds SwitchAudioSource."""
    from mote.cli import _detect_switch_audio_source
    with patch("mote.cli.shutil.which", return_value="/usr/local/bin/SwitchAudioSource"):
        assert _detect_switch_audio_source() is True


def test_detect_switch_audio_source_not_found():
    """_detect_switch_audio_source returns False when shutil.which returns None."""
    from mote.cli import _detect_switch_audio_source
    with patch("mote.cli.shutil.which", return_value=None):
        assert _detect_switch_audio_source() is False


def test_get_current_output_device_returns_name():
    """_get_current_output_device returns device name string from subprocess stdout."""
    from mote.cli import _get_current_output_device
    mock_result = MagicMock()
    mock_result.stdout = "MacBook Pro Speakers\n"
    with patch("mote.cli.subprocess.run", return_value=mock_result):
        assert _get_current_output_device() == "MacBook Pro Speakers"


def test_get_current_output_device_timeout():
    """_get_current_output_device returns None on subprocess timeout."""
    import subprocess
    from mote.cli import _get_current_output_device
    with patch("mote.cli.subprocess.run", side_effect=subprocess.TimeoutExpired("SwitchAudioSource", 5)):
        assert _get_current_output_device() is None


def test_get_current_output_device_empty_stdout():
    """_get_current_output_device returns None on empty stdout."""
    from mote.cli import _get_current_output_device
    mock_result = MagicMock()
    mock_result.stdout = "   "
    with patch("mote.cli.subprocess.run", return_value=mock_result):
        assert _get_current_output_device() is None


def test_set_output_device_success():
    """_set_output_device returns True when subprocess returns returncode 0."""
    from mote.cli import _set_output_device
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("mote.cli.subprocess.run", return_value=mock_result):
        assert _set_output_device("MacBook Pro Speakers") is True


def test_set_output_device_failure():
    """_set_output_device returns False when subprocess returns non-zero returncode."""
    from mote.cli import _set_output_device
    mock_result = MagicMock()
    mock_result.returncode = 1
    with patch("mote.cli.subprocess.run", return_value=mock_result):
        assert _set_output_device("Unknown Device") is False


def test_set_output_device_timeout():
    """_set_output_device returns False on subprocess timeout."""
    import subprocess
    from mote.cli import _set_output_device
    with patch("mote.cli.subprocess.run", side_effect=subprocess.TimeoutExpired("SwitchAudioSource", 5)):
        assert _set_output_device("MacBook Pro Speakers") is False


def test_write_audio_restore_creates_json(tmp_path):
    """_write_audio_restore creates JSON file with device name."""
    from mote.cli import _write_audio_restore, AUDIO_RESTORE_FILE
    import json
    _write_audio_restore(tmp_path, "MacBook Pro Speakers")
    restore_path = tmp_path / AUDIO_RESTORE_FILE
    assert restore_path.exists()
    data = json.loads(restore_path.read_text())
    assert data == {"device": "MacBook Pro Speakers"}


def test_read_audio_restore_returns_device(tmp_path):
    """_read_audio_restore returns device name from existing JSON file."""
    from mote.cli import _read_audio_restore, AUDIO_RESTORE_FILE
    (tmp_path / AUDIO_RESTORE_FILE).write_text('{"device": "MacBook Pro Speakers"}')
    assert _read_audio_restore(tmp_path) == "MacBook Pro Speakers"


def test_read_audio_restore_missing_file(tmp_path):
    """_read_audio_restore returns None when file does not exist."""
    from mote.cli import _read_audio_restore
    assert _read_audio_restore(tmp_path) is None


def test_read_audio_restore_malformed_json(tmp_path):
    """_read_audio_restore returns None on malformed JSON."""
    from mote.cli import _read_audio_restore, AUDIO_RESTORE_FILE
    (tmp_path / AUDIO_RESTORE_FILE).write_text("not json at all {{{")
    assert _read_audio_restore(tmp_path) is None


def test_delete_audio_restore_removes_file(tmp_path):
    """_delete_audio_restore removes file when it exists."""
    from mote.cli import _delete_audio_restore, AUDIO_RESTORE_FILE
    restore_path = tmp_path / AUDIO_RESTORE_FILE
    restore_path.write_text('{"device": "Test"}')
    _delete_audio_restore(tmp_path)
    assert not restore_path.exists()


def test_delete_audio_restore_no_error_if_missing(tmp_path):
    """_delete_audio_restore does not raise when file is missing."""
    from mote.cli import _delete_audio_restore
    _delete_audio_restore(tmp_path)  # Should not raise


def test_write_read_delete_audio_restore_cycle(tmp_path):
    """Full lifecycle: write -> read -> delete -> read returns None."""
    from mote.cli import _write_audio_restore, _read_audio_restore, _delete_audio_restore
    _write_audio_restore(tmp_path, "MacBook Pro Speakers")
    assert _read_audio_restore(tmp_path) == "MacBook Pro Speakers"
    _delete_audio_restore(tmp_path)
    assert _read_audio_restore(tmp_path) is None


# ---------------------------------------------------------------------------
# Plan 07-02, Task 2: Audio switching wired into record_command + audio restore command
# ---------------------------------------------------------------------------


def test_record_switches_audio_to_blackhole(mote_home):
    """record_command with SwitchAudioSource available prints switch message per D-03."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._get_current_output_device", return_value="MacBook Pro Speakers"), \
         patch("mote.cli._set_output_device", return_value=True):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "Switched audio output to BlackHole 2ch (was: MacBook Pro Speakers)" in result.output


def test_record_restores_audio_after_recording(mote_home):
    """record_command restores audio output after recording stops per D-03."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._get_current_output_device", return_value="MacBook Pro Speakers"), \
         patch("mote.cli._set_output_device", return_value=True):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "Restored audio output to MacBook Pro Speakers" in result.output


def test_record_advisory_when_no_switch_audio_source(mote_home):
    """record_command without SwitchAudioSource prints advisory with brew install instructions per D-01."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=False):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "brew install switchaudio-osx" in result.output


def test_record_crash_recovery_restores_audio(mote_home):
    """record_command with audio_restore.json present prints crash recovery message per D-09."""
    import json
    # Pre-create crash recovery file
    restore_file = mote_home / "audio_restore.json"
    restore_file.write_text(json.dumps({"device": "MacBook Pro Speakers"}))

    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._get_current_output_device", return_value="BlackHole 2ch"), \
         patch("mote.cli._set_output_device", return_value=True):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "from previous crash" in result.output


def test_record_crash_recovery_deletes_restore_file(mote_home):
    """record_command deletes audio_restore.json after successful crash recovery."""
    import json
    restore_file = mote_home / "audio_restore.json"
    restore_file.write_text(json.dumps({"device": "MacBook Pro Speakers"}))

    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._get_current_output_device", return_value="BlackHole 2ch"), \
         patch("mote.cli._set_output_device", return_value=True):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert not restore_file.exists(), "audio_restore.json should be deleted after crash recovery"


def test_record_audio_restore_file_deleted_after_success(mote_home):
    """audio_restore.json is deleted in the finally block after successful recording."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]
    restore_file = mote_home / "audio_restore.json"

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._get_current_output_device", return_value="MacBook Pro Speakers"), \
         patch("mote.cli._set_output_device", return_value=True):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert not restore_file.exists(), "audio_restore.json should be deleted after successful recording"


def test_record_failed_switch_deletes_restore_file(mote_home):
    """If switch to BlackHole fails, audio_restore.json is deleted and no restore is attempted."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]
    restore_file = mote_home / "audio_restore.json"

    set_calls = []

    def mock_set_device(name):
        set_calls.append(name)
        return False  # switch always fails

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BlackHole 2ch", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._get_current_output_device", return_value="MacBook Pro Speakers"), \
         patch("mote.cli._set_output_device", side_effect=mock_set_device):
        result = runner.invoke(cli, ["record"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert not restore_file.exists(), "audio_restore.json should be deleted when switch fails"
    # The restore should not be attempted on stop (only one call to switch — the failed one)
    assert len(set_calls) == 1


def test_audio_restore_command_no_file(mote_home):
    """mote audio restore with no file prints 'No audio restore file found'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["audio", "restore"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0, result.output
    assert "No audio restore file found" in result.output


def test_audio_restore_command_with_file(mote_home):
    """mote audio restore with file restores device and deletes file."""
    import json
    restore_file = mote_home / "audio_restore.json"
    restore_file.write_text(json.dumps({"device": "MacBook Pro Speakers"}))

    runner = CliRunner()
    with patch("mote.cli._detect_switch_audio_source", return_value=True), \
         patch("mote.cli._set_output_device", return_value=True):
        result = runner.invoke(cli, ["audio", "restore"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    assert "Restored audio output to MacBook Pro Speakers" in result.output
    assert not restore_file.exists()


def test_audio_restore_command_without_switch_audio_source(mote_home):
    """mote audio restore without SwitchAudioSource raises error mentioning brew install."""
    import json
    restore_file = mote_home / "audio_restore.json"
    restore_file.write_text(json.dumps({"device": "MacBook Pro Speakers"}))

    runner = CliRunner()
    with patch("mote.cli._detect_switch_audio_source", return_value=False):
        result = runner.invoke(cli, ["audio", "restore"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    assert "brew install switchaudio-osx" in result.output


def test_audio_group_help():
    """mote audio --help shows 'Audio device management'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["audio", "--help"])
    assert result.exit_code == 0
    assert "Audio device management" in result.output


# ---------------------------------------------------------------------------
# Plan 08-02, Task 1: auth google, upload command, --destination flag
# ---------------------------------------------------------------------------


def test_auth_google_first_time(mote_home):
    """mote auth google with no existing token calls run_auth_flow and prints success."""
    runner = CliRunner()
    mock_creds = MagicMock()
    mock_creds.token = "fake_token"

    with patch("mote.drive.get_credentials", return_value=None), \
         patch("mote.drive.run_auth_flow", return_value=mock_creds) as mock_flow, \
         patch("mote.drive.get_token_path", return_value=mote_home / "google_token.json"):
        result = runner.invoke(cli, ["auth", "google"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_flow.assert_called_once()
    assert "Authenticated" in result.output


def test_auth_google_already_authed_decline(mote_home):
    """mote auth google with valid token shows status; declining re-auth does not call run_auth_flow."""
    runner = CliRunner()
    mock_creds = MagicMock()

    with patch("mote.drive.get_credentials", return_value=mock_creds), \
         patch("mote.drive.run_auth_flow") as mock_flow, \
         patch("mote.drive.get_token_path", return_value=mote_home / "google_token.json"):
        result = runner.invoke(
            cli, ["auth", "google"],
            env={"MOTE_HOME": str(mote_home)},
            input="n\n",  # decline re-auth
        )

    assert result.exit_code == 0, result.output
    mock_flow.assert_not_called()
    # Should show status
    assert "Google Drive" in result.output or "Authenticated" in result.output


def test_auth_google_already_authed_accept(mote_home):
    """mote auth google with valid token, accepting re-auth, calls run_auth_flow."""
    runner = CliRunner()
    mock_creds = MagicMock()
    new_creds = MagicMock()

    with patch("mote.drive.get_credentials", return_value=mock_creds), \
         patch("mote.drive.run_auth_flow", return_value=new_creds) as mock_flow, \
         patch("mote.drive.get_token_path", return_value=mote_home / "google_token.json"):
        result = runner.invoke(
            cli, ["auth", "google"],
            env={"MOTE_HOME": str(mote_home)},
            input="y\n",  # accept re-auth
        )

    assert result.exit_code == 0, result.output
    mock_flow.assert_called_once()


def test_upload_command_with_file(mote_home, tmp_path):
    """mote upload <file> calls upload_transcripts with that file and configured folder_name."""
    transcript_file = tmp_path / "transcript.md"
    transcript_file.write_text("# Transcript\nhello world", encoding="utf-8")

    runner = CliRunner()
    with patch("mote.drive.upload_transcripts") as mock_upload, \
         patch("mote.cli.load_config", return_value={
             "destinations": {"drive": {"folder_name": "Mote Transcripts"}, "active": ["local"]},
             "output": {"dir": str(tmp_path), "format": ["markdown"]},
         }):
        result = runner.invoke(
            cli, ["upload", str(transcript_file)],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    mock_upload.assert_called_once()
    assert "Uploaded" in result.output


def test_upload_command_not_authed(mote_home, tmp_path):
    """mote upload raises ClickException when upload_transcripts raises RuntimeError (not authenticated)."""
    transcript_file = tmp_path / "transcript.md"
    transcript_file.write_text("# Transcript", encoding="utf-8")

    runner = CliRunner()
    with patch("mote.drive.upload_transcripts", side_effect=RuntimeError("Not authenticated with Google Drive. Run: mote auth google")), \
         patch("mote.cli.load_config", return_value={
             "destinations": {"drive": {"folder_name": "Mote Transcripts"}, "active": ["local"]},
             "output": {"dir": str(tmp_path), "format": ["markdown"]},
         }):
        result = runner.invoke(
            cli, ["upload", str(transcript_file)],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code != 0
    assert "mote auth google" in result.output or "Not authenticated" in result.output


def test_upload_command_no_args(mote_home):
    """mote upload without file or --last shows error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["upload"], env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code != 0


def test_destination_flag_drive_triggers_upload(mote_home):
    """mote record --destination drive calls upload_transcripts after transcription."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.drive.upload_transcripts") as mock_upload, \
         patch("mote.cli.load_config", return_value={
             "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
             "output": {"dir": str(out_dir), "format": ["markdown"]},
             "api_keys": {},
             "cleanup": {"wav_retention_days": 7},
             "destinations": {"active": ["local"], "drive": {"folder_name": "Mote Transcripts"}},
         }):
        result = runner.invoke(
            cli, ["record", "--destination", "drive"],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    mock_upload.assert_called_once()


def test_destination_local_only_no_upload(mote_home):
    """mote record --destination local does not call upload_transcripts even when config has drive active."""
    runner = CliRunner()
    wav = _make_test_wav(mote_home / "recordings" / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.find_blackhole_device", return_value={"name": "BH", "index": 0}), \
         patch("mote.cli.record_session", return_value=wav), \
         patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.drive.upload_transcripts") as mock_upload, \
         patch("mote.cli.load_config", return_value={
             "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
             "output": {"dir": str(out_dir), "format": ["markdown"]},
             "api_keys": {},
             "cleanup": {"wav_retention_days": 7},
             "destinations": {"active": ["local", "drive"], "drive": {"folder_name": "Mote Transcripts"}},
         }):
        result = runner.invoke(
            cli, ["record", "--destination", "local"],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    mock_upload.assert_not_called()


def test_drive_upload_failure_is_warning(mote_home, tmp_path):
    """_run_transcription with drive destination catches upload exception and prints warning."""
    from mote.cli import _run_transcription

    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = tmp_path / "out"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.drive.upload_transcripts", side_effect=Exception("network error")):
        import click
        from click.testing import CliRunner as _Runner

        @click.command()
        def _test_cmd():
            _run_transcription(
                wav, "local", "sv", "medium", None, out_dir, ["markdown"], None,
                destinations=["local", "drive"],
                config_dir=tmp_path,
                cfg={"destinations": {"drive": {"folder_name": "Mote Transcripts"}}},
            )

        result = _Runner().invoke(_test_cmd, [])

    assert result.exit_code == 0, result.output
    assert "Warning: Drive upload failed" in result.output
    assert "mote upload" in result.output


def test_drive_upload_no_upload_without_drive_destination(mote_home, tmp_path):
    """_run_transcription without drive in destinations does not call upload_transcripts."""
    from mote.cli import _run_transcription

    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = tmp_path / "out"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hello world"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.drive.upload_transcripts") as mock_upload:
        import click
        from click.testing import CliRunner as _Runner

        @click.command()
        def _test_cmd():
            _run_transcription(
                wav, "local", "sv", "medium", None, out_dir, ["markdown"], None,
                destinations=["local"],
            )

        _Runner().invoke(_test_cmd, [])

    mock_upload.assert_not_called()


def test_transcribe_destination_flag_drive(mote_home, tmp_path):
    """mote transcribe <wav> --destination drive triggers Drive upload."""
    runner = CliRunner()
    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = mote_home / "transcripts"
    fake_written = [out_dir / "2026-01-01_0000.md"]

    with patch("mote.cli.validate_config", return_value=([], [])), \
         patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="hej världen"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.drive.upload_transcripts") as mock_upload, \
         patch("mote.cli.load_config", return_value={
             "transcription": {"engine": "local", "language": "sv", "model": "kb-whisper-medium"},
             "output": {"dir": str(out_dir), "format": ["markdown"]},
             "api_keys": {},
             "destinations": {"active": ["local"], "drive": {"folder_name": "Mote Transcripts"}},
         }):
        result = runner.invoke(
            cli, ["transcribe", str(wav), "--destination", "drive"],
            env={"MOTE_HOME": str(mote_home)},
        )

    assert result.exit_code == 0, result.output
    mock_upload.assert_called_once()


def test_record_help_shows_destination_flag(mote_home):
    """mote record --help shows --destination option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["record", "--help"])
    assert result.exit_code == 0
    assert "--destination" in result.output


def test_transcribe_help_shows_destination_flag(mote_home):
    """mote transcribe --help shows --destination option."""
    runner = CliRunner()
    wav_path = "/tmp/fake.wav"
    result = runner.invoke(cli, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "--destination" in result.output


def test_auth_group_help():
    """mote auth --help shows 'Manage third-party service authentication'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "--help"])
    assert result.exit_code == 0
    assert "Manage" in result.output or "authentication" in result.output.lower()


def test_upload_command_help():
    """mote upload --help exits 0 and mentions --last."""
    runner = CliRunner()
    result = runner.invoke(cli, ["upload", "--help"])
    assert result.exit_code == 0
    assert "--last" in result.output


# ---------------------------------------------------------------------------
# NotebookLM integration tests
# ---------------------------------------------------------------------------


def test_auth_notebooklm_new_session(mote_home):
    """mote auth notebooklm calls run_login when no session exists (Playwright check passing)."""
    runner = CliRunner()

    mock_check_result = MagicMock()
    mock_check_result.returncode = 0

    with patch("mote.cli.shutil.which", return_value="/usr/bin/playwright"), \
         patch("mote.cli.subprocess.run", return_value=mock_check_result), \
         patch("mote.notebooklm.run_login") as mock_login:
        result = runner.invoke(cli, ["auth", "notebooklm"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code == 0, result.output
    mock_login.assert_called_once()
    assert "NotebookLM session stored" in result.output


def test_auth_notebooklm_already_authenticated(mote_home):
    """mote auth notebooklm with existing session shows path, asks to re-authenticate, returns if declined."""
    session_file = mote_home / "notebooklm_session.json"
    session_file.write_text('{"cookies": []}')

    runner = CliRunner()

    mock_check_result = MagicMock()
    mock_check_result.returncode = 0

    with patch("mote.cli.shutil.which", return_value="/usr/bin/playwright"), \
         patch("mote.cli.subprocess.run", return_value=mock_check_result), \
         patch("mote.notebooklm.run_login") as mock_login:
        result = runner.invoke(
            cli, ["auth", "notebooklm"],
            env={"MOTE_HOME": str(mote_home)},
            input="n\n",  # decline re-auth
        )

    assert result.exit_code == 0, result.output
    assert "session file exists" in result.output
    mock_login.assert_not_called()


def test_auth_notebooklm_login_failure(mote_home):
    """mote auth notebooklm raises ClickException when run_login raises RuntimeError."""
    runner = CliRunner()

    mock_check_result = MagicMock()
    mock_check_result.returncode = 0

    with patch("mote.cli.shutil.which", return_value="/usr/bin/playwright"), \
         patch("mote.cli.subprocess.run", return_value=mock_check_result), \
         patch("mote.notebooklm.run_login", side_effect=RuntimeError("login failed")):
        result = runner.invoke(cli, ["auth", "notebooklm"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    assert "login failed" in result.output


def test_auth_notebooklm_no_playwright(mote_home):
    """mote auth notebooklm when playwright not found prints install hint and aborts."""
    runner = CliRunner()

    with patch("mote.cli.shutil.which", return_value=None):
        result = runner.invoke(cli, ["auth", "notebooklm"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    assert "Playwright not found" in result.output
    assert "playwright install chromium" in result.output


def test_auth_notebooklm_no_chromium(mote_home):
    """mote auth notebooklm when playwright found but chromium not installed prints hint and aborts."""
    runner = CliRunner()

    mock_check_result = MagicMock()
    mock_check_result.returncode = 1  # chromium check fails

    with patch("mote.cli.shutil.which", return_value="/usr/bin/playwright"), \
         patch("mote.cli.subprocess.run", return_value=mock_check_result):
        result = runner.invoke(cli, ["auth", "notebooklm"], env={"MOTE_HOME": str(mote_home)})

    assert result.exit_code != 0
    assert "Playwright Chromium browser not found" in result.output
    assert "playwright install chromium" in result.output


def test_run_transcription_notebooklm_destination(mote_home, tmp_path):
    """_run_transcription with notebooklm destination calls upload_transcript with correct args."""
    from mote.cli import _run_transcription

    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = tmp_path / "out"
    fake_md = out_dir / "test.md"
    fake_written = [fake_md]

    with patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="transcript text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.notebooklm.upload_transcript") as mock_upload:
        import click
        from click.testing import CliRunner as _Runner

        @click.command()
        def _test_cmd():
            _run_transcription(
                wav, "local", "sv", "medium", None, out_dir, ["markdown"], None,
                destinations=["notebooklm"],
                config_dir=tmp_path,
                cfg={"destinations": {"notebooklm": {"notebook_name": "Mote Transcripts"}}},
            )

        _Runner().invoke(_test_cmd, [])

    mock_upload.assert_called_once_with(tmp_path, fake_written, "Mote Transcripts")


def test_run_transcription_notebooklm_failure_is_warning(mote_home, tmp_path):
    """_run_transcription with notebooklm destination catches exception and prints warning."""
    from mote.cli import _run_transcription

    wav = _make_test_wav(tmp_path / "test.wav")
    out_dir = tmp_path / "out"
    fake_written = [out_dir / "test.md"]

    with patch("mote.cli.get_wav_duration", return_value=60.0), \
         patch("mote.cli.transcribe_file", return_value="transcript text"), \
         patch("mote.cli.write_transcript", return_value=fake_written), \
         patch("mote.notebooklm.upload_transcript", side_effect=Exception("session expired")):
        import click
        from click.testing import CliRunner as _Runner

        @click.command()
        def _test_cmd():
            _run_transcription(
                wav, "local", "sv", "medium", None, out_dir, ["markdown"], None,
                destinations=["notebooklm"],
                config_dir=tmp_path,
                cfg={},
            )

        result = _Runner().invoke(_test_cmd, [])

    assert result.exit_code == 0, result.output
    assert "Warning: NotebookLM upload failed" in result.output
    assert "mote auth notebooklm" in result.output


def test_destination_choice_includes_notebooklm():
    """--destination notebooklm is accepted by record and transcribe --help output."""
    runner = CliRunner()

    record_result = runner.invoke(cli, ["record", "--help"])
    assert record_result.exit_code == 0
    assert "notebooklm" in record_result.output

    transcribe_result = runner.invoke(cli, ["transcribe", "--help"])
    assert transcribe_result.exit_code == 0
    assert "notebooklm" in transcribe_result.output
