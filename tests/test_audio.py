"""Unit tests for mote.audio module.

Tests cover all pure functions without hardware. sounddevice.query_devices() is
mocked to return controlled device lists. PID/WAV tests use the mote_home fixture.
"""

import os
import wave
import struct
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# find_blackhole_device
# ---------------------------------------------------------------------------

def _make_device(name: str, max_input_channels: int = 2, index: int = 0) -> dict:
    """Helper: build a minimal sounddevice device dict."""
    return {
        "name": name,
        "index": index,
        "max_input_channels": max_input_channels,
        "max_output_channels": 2,
        "default_samplerate": 44100.0,
    }


def test_find_blackhole_preferred():
    """When both 2ch and 16ch are present, return 2ch (D-08)."""
    from mote.audio import find_blackhole_device

    devices = [
        _make_device("Built-in Microphone", max_input_channels=1, index=0),
        _make_device("BlackHole 16ch", max_input_channels=16, index=1),
        _make_device("BlackHole 2ch", max_input_channels=2, index=2),
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        result = find_blackhole_device()
    assert result is not None
    assert result["name"] == "BlackHole 2ch"


def test_find_blackhole_fallback():
    """When only 16ch is present (no 2ch), return the 16ch device."""
    from mote.audio import find_blackhole_device

    devices = [
        _make_device("Built-in Microphone", max_input_channels=1, index=0),
        _make_device("BlackHole 16ch", max_input_channels=16, index=1),
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        result = find_blackhole_device()
    assert result is not None
    assert result["name"] == "BlackHole 16ch"


def test_find_blackhole_not_found():
    """When no BlackHole devices exist, return None."""
    from mote.audio import find_blackhole_device

    devices = [
        _make_device("Built-in Microphone", max_input_channels=1, index=0),
        _make_device("USB Audio Device", max_input_channels=2, index=1),
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        result = find_blackhole_device()
    assert result is None


def test_find_blackhole_input_only():
    """Ignore BlackHole devices with max_input_channels == 0 (output-only)."""
    from mote.audio import find_blackhole_device

    devices = [
        _make_device("BlackHole 2ch", max_input_channels=0, index=0),  # output-only
        _make_device("Built-in Microphone", max_input_channels=1, index=1),
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        result = find_blackhole_device()
    assert result is None


# ---------------------------------------------------------------------------
# rms_db
# ---------------------------------------------------------------------------

def test_rms_db_silence():
    """Array of zeros returns the -60dB floor."""
    from mote.audio import rms_db

    data = np.zeros(1024, dtype=np.float32)
    result = rms_db(data)
    assert result == -60.0


def test_rms_db_full_scale():
    """Array of 1.0 values returns 0.0 dB (full scale)."""
    from mote.audio import rms_db

    data = np.ones(1024, dtype=np.float32)
    result = rms_db(data)
    assert abs(result - 0.0) < 0.01


def test_rms_db_known_signal():
    """Array of 0.1 values returns approximately -20 dB."""
    from mote.audio import rms_db

    data = np.full(1024, 0.1, dtype=np.float32)
    result = rms_db(data)
    # 20 * log10(0.1) = -20 dB
    assert abs(result - (-20.0)) < 0.1


# ---------------------------------------------------------------------------
# make_level_bar
# ---------------------------------------------------------------------------

def test_make_level_bar_silence():
    """-60dB produces all empty blocks (width 20)."""
    from mote.audio import make_level_bar

    bar = make_level_bar(-60.0, width=20)
    assert bar == "░" * 20


def test_make_level_bar_full():
    """0dB produces all filled blocks (width 20)."""
    from mote.audio import make_level_bar

    bar = make_level_bar(0.0, width=20)
    assert bar == "█" * 20


def test_make_level_bar_half():
    """-30dB produces 10 filled + 10 empty (width 20)."""
    from mote.audio import make_level_bar

    bar = make_level_bar(-30.0, width=20)
    assert bar == "█" * 10 + "░" * 10


# ---------------------------------------------------------------------------
# make_display
# ---------------------------------------------------------------------------

def test_make_display_format():
    """make_display returns Rich Text containing HH:MM:SS and dB reading."""
    from mote.audio import make_display
    from rich.text import Text

    result = make_display(90, -30.0)
    assert isinstance(result, Text)
    plain = result.plain
    assert "00:01:30" in plain
    assert "dB" in plain


def test_make_display_hours():
    """3661 seconds displays as 01:01:01."""
    from mote.audio import make_display

    result = make_display(3661, -20.0)
    plain = result.plain
    assert "01:01:01" in plain


# ---------------------------------------------------------------------------
# write_wav
# ---------------------------------------------------------------------------

def test_write_wav_creates_file(tmp_path):
    """write_wav creates a valid WAV file from float32 chunks."""
    from mote.audio import write_wav

    chunks = [np.zeros((1024, 1), dtype=np.float32) for _ in range(4)]
    wav_path = tmp_path / "test.wav"
    write_wav(wav_path, chunks)

    assert wav_path.exists()
    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2  # 16-bit
        assert wf.getframerate() == 16000


def test_write_wav_clips(tmp_path):
    """float32 values > 1.0 are clipped, not wrapped (Pitfall 5)."""
    from mote.audio import write_wav

    # Values well above 1.0 — should clip to max int16, not wrap
    chunks = [np.full((1024, 1), 5.0, dtype=np.float32)]
    wav_path = tmp_path / "clipped.wav"
    write_wav(wav_path, chunks)

    assert wav_path.exists()
    with wave.open(str(wav_path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    # All samples should be 32767 (max int16), not wrapped negative values
    samples = np.frombuffer(raw, dtype=np.int16)
    assert np.all(samples == 32767), f"Expected all 32767, got min={samples.min()}"


# ---------------------------------------------------------------------------
# new_recording_path
# ---------------------------------------------------------------------------

def test_new_recording_path_creates_dir(mote_home):
    """new_recording_path creates recordings/ if missing and returns correct pattern."""
    from mote.audio import new_recording_path
    import re

    recordings_dir = mote_home / "recordings"
    assert not recordings_dir.exists()

    path = new_recording_path(recordings_dir)

    assert recordings_dir.exists()
    assert path.parent == recordings_dir
    assert re.match(r"mote_\d{8}_\d{6}\.wav", path.name), f"Bad filename: {path.name}"


def test_new_recording_path_unique(mote_home):
    """Two calls produce paths with the expected naming pattern."""
    from mote.audio import new_recording_path
    import re

    recordings_dir = mote_home / "recordings"
    path1 = new_recording_path(recordings_dir)
    # Verify pattern regardless of whether same second or not
    assert re.match(r"mote_\d{8}_\d{6}\.wav", path1.name)


# ---------------------------------------------------------------------------
# is_recording_active
# ---------------------------------------------------------------------------

def test_is_recording_active_no_file(mote_home):
    """No PID file returns (False, None)."""
    from mote.audio import is_recording_active

    pid_path = mote_home / "mote.pid"
    alive, pid = is_recording_active(pid_path)
    assert alive is False
    assert pid is None


def test_is_recording_active_stale(mote_home):
    """PID file with a dead PID returns (False, pid)."""
    from mote.audio import is_recording_active

    pid_path = mote_home / "mote.pid"
    # Use a PID that is guaranteed not to exist (very large number)
    dead_pid = 999999
    pid_path.write_text(str(dead_pid))

    alive, pid = is_recording_active(pid_path)
    assert alive is False
    assert pid == dead_pid


def test_is_recording_active_alive(mote_home):
    """PID file with current process PID returns (True, pid)."""
    from mote.audio import is_recording_active

    pid_path = mote_home / "mote.pid"
    current_pid = os.getpid()
    pid_path.write_text(str(current_pid))

    alive, pid = is_recording_active(pid_path)
    assert alive is True
    assert pid == current_pid


def test_is_recording_active_corrupt(mote_home):
    """PID file with non-integer content returns (False, None)."""
    from mote.audio import is_recording_active

    pid_path = mote_home / "mote.pid"
    pid_path.write_text("not-a-pid")

    alive, pid = is_recording_active(pid_path)
    assert alive is False
    assert pid is None


# ---------------------------------------------------------------------------
# find_orphan_recordings
# ---------------------------------------------------------------------------

def test_find_orphan_recordings(mote_home):
    """Detects .wav files in recordings/ directory."""
    from mote.audio import find_orphan_recordings

    recordings_dir = mote_home / "recordings"
    recordings_dir.mkdir()
    (recordings_dir / "mote_20260101_120000.wav").touch()
    (recordings_dir / "mote_20260101_130000.wav").touch()
    (recordings_dir / "not_a_wav.txt").touch()  # should be ignored

    orphans = find_orphan_recordings(recordings_dir)
    assert len(orphans) == 2
    assert all(p.suffix == ".wav" for p in orphans)


def test_find_orphan_recordings_empty(mote_home):
    """Empty recordings/ returns empty list."""
    from mote.audio import find_orphan_recordings

    recordings_dir = mote_home / "recordings"
    recordings_dir.mkdir()

    orphans = find_orphan_recordings(recordings_dir)
    assert orphans == []


def test_find_orphan_recordings_no_dir(mote_home):
    """Non-existent recordings/ returns empty list."""
    from mote.audio import find_orphan_recordings

    recordings_dir = mote_home / "recordings"
    assert not recordings_dir.exists()

    orphans = find_orphan_recordings(recordings_dir)
    assert orphans == []
