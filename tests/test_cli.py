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
