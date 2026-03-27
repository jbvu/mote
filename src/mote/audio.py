"""Audio capture via BlackHole.

Provides all building blocks for the CLI recording commands:
- BlackHole device detection (prefers 2ch per D-08)
- Queue-based InputStream recording engine
- WAV file writing (16kHz mono 16-bit per D-06)
- PID file management (D-10, D-11, D-12)
- Rich display helpers (D-01, D-02, D-03)
- Orphan recording detection (D-05)
"""

import datetime
import os
import queue
import signal
import threading
import time
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from rich.live import Live
from rich.text import Text

from mote.config import get_config_dir

# Recording constants
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 1024  # ~64ms per callback at 16kHz


def find_blackhole_device() -> Optional[dict]:
    """Return the preferred BlackHole input device dict, or None if not installed.

    Prefers "BlackHole 2ch" (D-08). Falls back to any BlackHole variant with
    input channels. Ignores output-only BlackHole devices.

    The returned dict includes an "index" key with the numeric sounddevice
    device index required by sd.InputStream(device=...).
    """
    devices = sd.query_devices()
    preferred: Optional[dict] = None
    fallback: Optional[dict] = None
    for i, d in enumerate(devices):
        if "BlackHole" in d["name"] and d["max_input_channels"] > 0:
            device_with_index = dict(d)
            device_with_index["index"] = i
            if "2ch" in d["name"] and preferred is None:
                preferred = device_with_index
            elif fallback is None:
                fallback = device_with_index
    return preferred or fallback


def rms_db(data: np.ndarray) -> float:
    """Return dB full-scale from float32 audio block. Floor at -60dB.

    Args:
        data: float32 audio samples where ±1.0 = full scale.

    Returns:
        dB value in range [-60.0, 0.0].
    """
    rms = float(np.sqrt(np.mean(data ** 2)))
    db = 20.0 * np.log10(max(rms, 1e-9))
    return max(-60.0, db)


def make_level_bar(db: float, width: int = 20) -> str:
    """Map -60dB..0dB to an ASCII block bar of given width.

    Args:
        db: dB value (clamped to -60..0 range).
        width: total bar width in characters.

    Returns:
        String of filled (█) and empty (░) block characters.
    """
    level = max(0.0, min(1.0, (db + 60.0) / 60.0))
    filled = int(level * width)
    return "█" * filled + "░" * (width - filled)


def make_display(elapsed_s: int, db: float) -> Text:
    """Build Rich Text for the live recording display (D-01).

    Shows: "Recording  HH:MM:SS  {level bar}  {db}dB"

    Args:
        elapsed_s: recording duration in seconds.
        db: current audio level in dB.

    Returns:
        Rich Text object with styled components.
    """
    hours, rem = divmod(elapsed_s, 3600)
    mm, ss = divmod(rem, 60)
    bar = make_level_bar(db)
    t = Text()
    t.append("Recording  ")
    t.append(f"{hours:02d}:{mm:02d}:{ss:02d}", style="bold cyan")
    t.append(f"  {bar}", style="green")
    t.append(f"  {db:.0f}dB", style="dim")
    return t


def write_wav(path: Path, chunks: list, samplerate: int = 16000) -> None:
    """Write accumulated float32 chunks to a 16kHz mono 16-bit WAV file (D-06).

    Clips float32 values to ±1.0 before int16 conversion to prevent wrapping
    distortion (Pitfall 5).

    Args:
        path: destination WAV file path.
        chunks: list of float32 numpy arrays (shape: (N, 1) or (N,)).
        samplerate: output sample rate in Hz.
    """
    audio = np.concatenate(chunks, axis=0)
    audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(samplerate)
        wf.writeframes(audio_int16.tobytes())


def new_recording_path(recordings_dir: Path) -> Path:
    """Create recordings directory if needed and return a unique WAV path (D-04).

    Filename format: mote_YYYYMMDD_HHMMSS.wav

    Args:
        recordings_dir: directory to store recordings (e.g. ~/.mote/recordings/).

    Returns:
        Path for the new WAV file (not yet created).
    """
    recordings_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return recordings_dir / f"mote_{ts}.wav"


def is_recording_active(pid_path: Path) -> tuple:
    """Check whether a recording process is currently active (D-10, D-11, D-12).

    Args:
        pid_path: path to the PID file (e.g. ~/.mote/mote.pid).

    Returns:
        (is_alive, pid) where is_alive is True if process exists and is running.
        Returns (False, None) if no PID file or corrupt content.
        Returns (False, pid) if PID file exists but process is dead (stale).
    """
    if not pid_path.exists():
        return False, None
    try:
        pid = int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return False, None
    try:
        os.kill(pid, 0)  # signal 0 = probe only, no actual kill
        return True, pid
    except ProcessLookupError:
        return False, pid  # stale PID — process is dead
    except PermissionError:
        return True, pid  # process alive, owned by different user


def find_orphan_recordings(recordings_dir: Path) -> list:
    """Return sorted list of WAV files in the recordings directory (D-05).

    Used at `mote record` startup to detect recordings left from crashes.

    Args:
        recordings_dir: path to recordings directory.

    Returns:
        Sorted list of Path objects for *.wav files, or empty list if dir absent.
    """
    if not recordings_dir.exists():
        return []
    return sorted(recordings_dir.glob("*.wav"))


def record_session(device_index: int, recordings_dir: Path, pid_path: Path) -> Path:
    """Record audio from a BlackHole device until SIGINT (Ctrl+C).

    Architecture: PortAudio callback → queue → main thread drain.
    Uses threading.Event for stop signal (set by SIGINT handler on main thread).
    Writes PID file on start, removes it on exit (try/finally per Pitfall 4).

    Args:
        device_index: sounddevice device index for BlackHole input.
        recordings_dir: directory to store the WAV file.
        pid_path: path for PID tracking file.

    Returns:
        Path to the written WAV file.
    """
    audio_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    chunks: list = []

    def _audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        """Called on PortAudio thread. Must be fast — only enqueue."""
        audio_queue.put(indata.copy())

    # SIGINT handler must be set on main thread (Python requirement)
    signal.signal(signal.SIGINT, lambda s, f: stop_event.set())

    wav_path = new_recording_path(recordings_dir)

    # Get device name for startup message (D-02)
    devices = sd.query_devices()
    device_name = devices[device_index]["name"] if device_index < len(devices) else f"device {device_index}"

    # Write PID file (D-10)
    pid_path.write_text(str(os.getpid()))

    try:
        print(f"Recording from {device_name} (16kHz mono)")
        print("[dim]Ctrl+C to stop[/dim]")

        start = time.monotonic()
        current_db = -60.0

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=BLOCKSIZE,
            device=device_index,
            callback=_audio_callback,
        ):
            with Live(make_display(0, -60.0), refresh_per_second=4) as live:
                while not stop_event.is_set():
                    try:
                        chunk = audio_queue.get(timeout=0.1)  # Pitfall 6: always use timeout
                        chunks.append(chunk)
                        current_db = rms_db(chunk)
                    except queue.Empty:
                        pass  # just check stop_event again
                    elapsed = int(time.monotonic() - start)
                    live.update(make_display(elapsed, current_db))

    finally:
        # Always clean up PID file (Pitfall 4)
        if pid_path.exists():
            pid_path.unlink()
        # Write WAV if any audio was captured
        if chunks:
            write_wav(wav_path, chunks)

    return wav_path
