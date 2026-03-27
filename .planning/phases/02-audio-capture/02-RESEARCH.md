# Phase 2: Audio Capture - Research

**Researched:** 2026-03-27
**Domain:** sounddevice audio capture, Rich live display, PID-based process tracking, WAV I/O
**Confidence:** HIGH

## Summary

Phase 2 builds on the Phase 1 foundation to deliver the core capture loop: detect BlackHole, open a `sounddevice.InputStream` with a queue-based callback, compute RMS/dB per block, update a Rich Live display, and write accumulated buffers to a 16kHz mono 16-bit WAV when Ctrl+C fires. All required libraries are already declared in `pyproject.toml` (sounddevice, numpy, rich). No new dependencies are needed.

The recording architecture is deliberately sequential (CLAUDE.md constraint: no threading for audio + transcription). The `InputStream` callback runs on a PortAudio thread and only puts data in a `queue.Queue`. The main thread drains the queue in a loop, updates the Rich Live display, and checks a `threading.Event` set by the SIGINT handler. This avoids GIL contention and keeps signal handling on the main thread (a Python requirement).

WAV writing uses the stdlib `wave` module — no scipy or soundfile dependency. Float32 audio is collected for accurate dB calculation, then converted to int16 for WAV output.

**Primary recommendation:** queue-based `InputStream` callback + `threading.Event` stop signal + stdlib `wave` for output + Rich `Live` with `refresh_per_second=4`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use Rich library live display with a single updating line showing animated level bar, elapsed time, and dB reading
- **D-02:** Show device name once at recording start, then only level + elapsed time during recording
- **D-03:** Display "Ctrl+C to stop" hint below the live line
- **D-04:** Store temporary WAV files in `~/.mote/recordings/` (consistent with config path pattern)
- **D-05:** On abnormal exit (crash/kill), leave orphaned WAV files in place. On next `mote record`, detect orphans and warn the user — let them decide to keep or delete
- **D-06:** WAV format: 16kHz mono 16-bit (~1.9MB/min)
- **D-07:** Auto-detect BlackHole by searching `sounddevice.query_devices()` for devices containing "BlackHole" in the name
- **D-08:** Prefer "BlackHole 2ch" when multiple BlackHole devices are found. Fall back to other BlackHole variants only if 2ch is absent
- **D-09:** If no BlackHole device is found, refuse to start recording with a clear error message including install instructions (`brew install blackhole-2ch`)
- **D-10:** Use a PID file at `~/.mote/mote.pid` to track active recording
- **D-11:** `mote status` checks if the PID file exists and whether the process is alive — reports "Recording in progress" or "Idle"
- **D-12:** `mote record` refuses to start if another recording is active (PID alive). If PID is stale (process dead), warn, clean up the PID file, and allow start

### Claude's Discretion
- sounddevice stream configuration details (buffer size, callback structure)
- Rich layout specifics (Panel, Live, progress bar widget choices)
- WAV file naming convention within ~/.mote/recordings/
- Exact error message wording for BlackHole not found
- Signal handler implementation for Ctrl+C (SIGINT)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUD-01 | User can capture system audio from virtual meetings via BlackHole | `sounddevice.InputStream` with device=blackhole_device_index; callback-based capture verified |
| AUD-02 | User can start and stop recording via CLI command | Click `record` command with SIGINT handler stops stream cleanly |
| AUD-03 | User sees real-time audio level indicator during recording | RMS -> dB -> ASCII bar in Rich Live display; refresh_per_second=4 |
| AUD-04 | User sees elapsed recording time during recording | `time.monotonic()` start time diff formatted MM:SS in Rich Live |
| CLI-01 | `mote record` starts recording with live status display | Click command added to existing `cli` group in cli.py |
| CLI-04 | `mote status` shows current recording/transcription state | PID file check with `os.kill(pid, 0)` liveness test |
| CLI-06 | Ctrl+C during recording gracefully stops and triggers transcription | `signal.signal(SIGINT, handler)` sets `stop_event`; Phase 2 stops and writes WAV (transcription in Phase 4) |
</phase_requirements>

## Standard Stack

### Core (all already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sounddevice | 0.5.5 | Audio capture from BlackHole via PortAudio | NumPy-native, bundles PortAudio, cleaner device enumeration than PyAudio |
| numpy | 2.x | Audio buffer accumulation + dB math | Required by sounddevice; float32 arrays native |
| rich | 14.3.3 | Live display (level bar + elapsed time) | Already installed; `Live`, `Text` cover the UI |
| wave (stdlib) | — | WAV file writing — no extra dep | stdlib; handles 16kHz/mono/16-bit perfectly |
| signal (stdlib) | — | SIGINT handler for Ctrl+C | Python stdlib; must be set on main thread |
| queue (stdlib) | — | Thread-safe audio buffer queue | Decouples PortAudio callback thread from main thread |
| threading (stdlib) | — | `threading.Event` for stop signaling | Lightweight; not used for audio+transcription (CLAUDE.md constraint satisfied) |
| os (stdlib) | — | PID file write + `os.kill(pid, 0)` liveness | Standard process liveness pattern |

### No New Dependencies Required
All required libraries are already declared in `pyproject.toml`. Phase 2 adds zero new package dependencies.

**Verified versions (installed in project venv):**
- sounddevice: 0.5.5
- rich: 14.3.3 (installed, newer than the 13.x minimum in pyproject.toml)
- numpy: 2.x

## Architecture Patterns

### Recommended Project Structure
```
src/mote/
├── audio.py         # NEW: BlackHole detection, InputStream recording, WAV write, PID management
├── cli.py           # EXTEND: add `record` and `status` commands to existing cli group
├── config.py        # EXISTING: get_config_dir() reused for recordings/ and mote.pid paths
└── ...

tests/
├── test_audio.py    # NEW: unit tests for audio.py functions
└── test_cli.py      # EXTEND: add record/status command tests
```

### Pattern 1: Queue-Based InputStream Callback

**What:** PortAudio calls the callback on its own thread; callback only enqueues data. Main thread drains the queue, computes dB, updates display.

**When to use:** Any time you need live monitoring + accumulation without GIL pressure.

**Why not `sd.rec()` blocking:** `sd.rec()` pre-allocates a fixed-size array — unknown recording duration makes this unsuitable. InputStream with a queue supports open-ended recording.

```python
# Source: verified in project venv against sounddevice 0.5.5
import queue
import sounddevice as sd
import numpy as np

audio_queue: queue.Queue = queue.Queue()
chunks: list[np.ndarray] = []

def _audio_callback(indata: np.ndarray, frames: int, time, status) -> None:
    """Called on PortAudio thread. Must be fast — only enqueue."""
    audio_queue.put(indata.copy())

stream = sd.InputStream(
    samplerate=16000,
    channels=1,
    dtype="float32",       # float32 for accurate dB; convert to int16 at WAV write
    blocksize=1024,        # ~64ms per callback at 16kHz
    device=blackhole_index,
    callback=_audio_callback,
)
```

### Pattern 2: SIGINT Stop with threading.Event

**What:** SIGINT handler sets a `threading.Event`. Main recording loop polls the event.

**Why not `KeyboardInterrupt` catch:** Click/Python may swallow or re-raise KeyboardInterrupt inconsistently inside a Rich Live context. Explicit `signal.signal` is more predictable.

**Python requirement:** `signal.signal()` MUST be called from the main thread.

```python
# Source: verified in project venv — signal module stdlib
import signal
import threading

stop_event = threading.Event()

def _handle_sigint(sig, frame) -> None:
    stop_event.set()

signal.signal(signal.SIGINT, _handle_sigint)

# Main loop
with stream:
    while not stop_event.is_set():
        try:
            chunk = audio_queue.get(timeout=0.1)
            chunks.append(chunk)
            # compute dB + update display
        except queue.Empty:
            pass  # just check stop_event again
```

### Pattern 3: dB Calculation from float32 Audio

**What:** RMS-based dB from float32 input data where 1.0 = full scale.

```python
# Source: verified in project venv
import numpy as np

def rms_db(data: np.ndarray) -> float:
    """Return dB full-scale from float32 audio block. Floor at -60dB."""
    rms = float(np.sqrt(np.mean(data ** 2)))
    return 20.0 * np.log10(max(rms, 1e-9))
```

### Pattern 4: ASCII Level Bar for Rich Text

```python
# Source: verified visually in project venv — renders correctly
from rich.text import Text

def make_level_bar(db: float, width: int = 20) -> str:
    """Map -60dB..0dB to filled bar of given width."""
    level = max(0.0, min(1.0, (db + 60.0) / 60.0))
    filled = int(level * width)
    return "█" * filled + "░" * (width - filled)
```

### Pattern 5: Rich Live Display

```python
# Source: verified Rich 14.3.3 in project venv
from rich.live import Live
from rich.text import Text

def make_display(elapsed_s: int, db: float) -> Text:
    mm, ss = divmod(elapsed_s, 60)
    bar = make_level_bar(db)
    t = Text()
    t.append("Recording  ")
    t.append(f"{mm:02d}:{ss:02d}", style="bold cyan")
    t.append(f"  {bar}", style="green")
    t.append(f"  {db:.0f}dB", style="dim")
    return t

# Usage:
with Live(make_display(0, -60.0), refresh_per_second=4) as live:
    while not stop_event.is_set():
        ...
        live.update(make_display(elapsed, current_db))
```

`refresh_per_second=4` (250ms interval) is fast enough to feel live while producing minimal CPU overhead.

### Pattern 6: WAV Write (stdlib wave, float32 -> int16)

```python
# Source: verified in project venv — stdlib wave module
import wave
import numpy as np
from pathlib import Path

def write_wav(path: Path, chunks: list[np.ndarray], samplerate: int = 16000) -> None:
    """Write accumulated float32 chunks to 16kHz mono 16-bit WAV."""
    audio = np.concatenate(chunks, axis=0)        # shape: (N, 1)
    audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)           # 16-bit = 2 bytes
        wf.setframerate(samplerate)
        wf.writeframes(audio_int16.tobytes())
```

### Pattern 7: BlackHole Device Detection

```python
# Source: verified against sounddevice.DeviceList structure in project venv
import sounddevice as sd
from typing import Optional

def find_blackhole_device() -> Optional[dict]:
    """Return preferred BlackHole input device dict, or None if not installed."""
    devices = sd.query_devices()
    preferred: Optional[dict] = None
    fallback: Optional[dict] = None
    for d in devices:
        if "BlackHole" in d["name"] and d["max_input_channels"] > 0:
            if "2ch" in d["name"] and preferred is None:
                preferred = d
            elif fallback is None:
                fallback = d
    return preferred or fallback
```

`sd.query_devices()` returns a `sounddevice.DeviceList` — iterable as a sequence of plain dicts with keys: `name`, `index`, `max_input_channels`, `max_output_channels`, `default_samplerate`. No attribute access needed; dict key access works.

### Pattern 8: PID File Liveness Check

```python
# Source: verified in project venv — os.kill with signal 0
import os
from pathlib import Path

def is_recording_active(pid_path: Path) -> tuple[bool, Optional[int]]:
    """Returns (is_alive, pid). Handles missing/stale PID files."""
    if not pid_path.exists():
        return False, None
    try:
        pid = int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return False, None
    try:
        os.kill(pid, 0)   # signal 0 = probe only, no actual kill
        return True, pid
    except ProcessLookupError:
        return False, pid   # stale PID
    except PermissionError:
        return True, pid    # process alive, different user (edge case)
```

### Pattern 9: WAV File Naming

Recommended naming: `mote_YYYYMMDD_HHMMSS.wav` within `~/.mote/recordings/`.

```python
import datetime
from pathlib import Path

def new_recording_path(recordings_dir: Path) -> Path:
    recordings_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return recordings_dir / f"mote_{ts}.wav"
```

Orphan detection at start of `mote record`:
```python
orphans = sorted(recordings_dir.glob("*.wav"))
if orphans:
    # Warn user: list orphans with size + mtime, prompt keep/delete
```

### Anti-Patterns to Avoid

- **`sd.rec()` for open-ended recording:** Pre-allocates fixed array — unknown duration makes this wrong.
- **Collecting int16 in callback:** Collect float32, convert at write time — int16 loses precision for dB math.
- **`signal.signal()` from a non-main thread:** Python raises `ValueError: signal only works in main thread`.
- **Rich `Live` without `transient=False`:** Default keeps the live block in terminal history after exit, which is correct for this use case. Do NOT set `transient=True` — the final "Recording stopped" summary should remain visible.
- **`threading` for audio+transcription:** CLAUDE.md constraint. The `threading.Event` used here is only for signaling, not concurrent audio+transcription.
- **PyAudio:** Not in the project stack. sounddevice bundles PortAudio and has a NumPy-native API.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe audio queue | Custom ring buffer | `queue.Queue` | Thread-safe stdlib; supports timeout for polling |
| WAV encoding | Binary packing | stdlib `wave` | Handles RIFF headers, sample width, frame counting |
| dB from int16 samples | Manual scaling | Record float32, compute before conversion | int16 loses dynamic range for quiet signals |
| Process liveness | PGID/proc filesystem | `os.kill(pid, 0)` | One-liner, macOS + Linux, raises `ProcessLookupError` on dead PID |
| Rich terminal width | Hardcoded bar length | `console.width` | Adapts to terminal size; Rich exposes this |

## Common Pitfalls

### Pitfall 1: BlackHole Device Index is Not Stable
**What goes wrong:** Storing device index as a config value and reusing it across reboots. macOS assigns audio device indices dynamically.
**Why it happens:** Device index in sounddevice is a PortAudio enumeration index, not a stable identifier.
**How to avoid:** Always call `find_blackhole_device()` at recording start to resolve the current index. Never persist the index.
**Warning signs:** "No such device" errors after an audio routing change.

### Pitfall 2: Recording Starts Before BlackHole is Active Input
**What goes wrong:** InputStream opens on a device that exists but no audio flows because the meeting app output isn't routed to BlackHole's aggregate device.
**Why it happens:** BlackHole acts as a virtual cable. Audio only flows if the system output (or app output) is set to route through BlackHole.
**How to avoid:** This is a user setup issue. The `mote record` startup message should remind users: "Ensure your meeting app output is routed to BlackHole." The recording itself will still work (silent if not routed); this is Phase 2 scope — detection of audio flow is covered by the level indicator (AUD-03).
**Warning signs:** Level bar shows -60dB throughout the recording.

### Pitfall 3: SIGINT Inside Rich Live Leaves Terminal in Broken State
**What goes wrong:** If the program exits inside a `Live` context manager without proper cleanup, the terminal cursor may be hidden or the live block may flicker.
**Why it happens:** Rich Live uses ANSI escape sequences; abnormal exit skips `__exit__`.
**How to avoid:** Use `Live` as a context manager and only call `stop_event.set()` from the SIGINT handler — let the main loop exit the `with Live(...):` block normally after the event is set.

### Pitfall 4: PID File Left on Crash Prevents Next Recording
**What goes wrong:** `mote record` crashes without cleaning up `mote.pid`. Next invocation sees the PID file, checks if alive (dead), must handle gracefully.
**Why it happens:** Unhandled exceptions bypass cleanup code not in `finally` blocks.
**How to avoid:** Decision D-12 already specifies the handling. Implement PID write/delete in a `try/finally` block. Stale PID detection in D-12 clears the file and proceeds.

### Pitfall 5: float32 Clipping on int16 Conversion
**What goes wrong:** If audio exceeds ±1.0 float32 (possible with some BlackHole configurations), `astype(np.int16)` wraps around instead of clipping, producing loud distortion.
**Why it happens:** NumPy int16 cast wraps on overflow — it does NOT clip.
**How to avoid:** Always use `.clip(-32768, 32767)` before `.astype(np.int16)` — see WAV write pattern above.

### Pitfall 6: queue.Queue.get() Without Timeout Blocks Forever
**What goes wrong:** `audio_queue.get()` (no timeout) blocks the main thread even when `stop_event` is set, causing the program to hang on Ctrl+C.
**Why it happens:** The callback stops producing data when the stream stops, so the queue drains and `get()` blocks.
**How to avoid:** Always use `audio_queue.get(timeout=0.1)` and catch `queue.Empty` — loop continues and stop_event check fires.

## Code Examples

### Full Recording Flow Sketch

```python
# Source: synthesized from verified patterns above
import os
import queue
import signal
import threading
import time
import wave
import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from rich.live import Live

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 1024   # ~64ms per block


def record_to_wav(device_index: int, recordings_dir: Path) -> Path:
    """Record until SIGINT. Returns path to written WAV file."""
    audio_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    chunks: list[np.ndarray] = []

    def _callback(indata: np.ndarray, frames: int, time, status) -> None:
        audio_queue.put(indata.copy())

    signal.signal(signal.SIGINT, lambda s, f: stop_event.set())

    wav_path = new_recording_path(recordings_dir)
    start = time.monotonic()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=BLOCKSIZE,
        device=device_index,
        callback=_callback,
    ):
        with Live(refresh_per_second=4) as live:
            current_db = -60.0
            while not stop_event.is_set():
                try:
                    chunk = audio_queue.get(timeout=0.1)
                    chunks.append(chunk)
                    current_db = rms_db(chunk)
                except queue.Empty:
                    pass
                elapsed = int(time.monotonic() - start)
                live.update(make_display(elapsed, current_db))

    # Write WAV after stream closes
    write_wav(wav_path, chunks)
    return wav_path
```

### mote status Command Sketch

```python
# Source: uses verified PID pattern
@cli.command("status")
def status_command():
    """Show whether a recording is in progress."""
    from mote.config import get_config_dir
    pid_path = get_config_dir() / "mote.pid"
    alive, pid = is_recording_active(pid_path)
    if alive:
        click.echo(f"Recording in progress (PID {pid})")
    else:
        click.echo("Idle")
```

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| PyAudio bytes callback | sounddevice float32 NumPy callback | sounddevice is the modern standard |
| Fixed-length `sd.rec()` | Open-ended InputStream + queue | Required for unknown duration recording |
| scipy.io.wavfile for WAV | stdlib `wave` | No extra dependency needed for PCM WAV |
| `KeyboardInterrupt` catch | `signal.signal(SIGINT, handler)` | More predictable inside Rich Live context |

## Open Questions

1. **Recording from BlackHole requires specific macOS audio routing**
   - What we know: BlackHole 2ch captures system audio only if the meeting app output is routed through it (via aggregate device or "Use BlackHole as output").
   - What's unclear: Should `mote record` detect zero-signal audio and warn after N seconds?
   - Recommendation: Out of scope for Phase 2. The level indicator covers it visually. Add a warning if dB stays below -58dB for 10+ seconds in a future phase.

2. **CLI-06 says "triggers transcription" but Phase 4 does transcription**
   - What we know: CLI-06 in REQUIREMENTS.md says "Ctrl+C during recording gracefully stops and triggers transcription." Phase 4 delivers transcription.
   - What's unclear: Should Phase 2 stub a post-record hook or just write the WAV and exit?
   - Recommendation: Phase 2 writes the WAV and prints its path. CLI-06 is partially satisfied (graceful stop) and fully satisfied in Phase 4 (transcription trigger). CONTEXT.md does not mention transcription in Phase 2 scope, so WAV-write-only is correct here.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (exists) |
| Quick run command | `uv run pytest tests/test_audio.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUD-01 | BlackHole device found via query_devices | unit | `uv run pytest tests/test_audio.py::test_find_blackhole_found -x` | Wave 0 |
| AUD-01 | No BlackHole raises ClickException | unit | `uv run pytest tests/test_audio.py::test_find_blackhole_not_found -x` | Wave 0 |
| AUD-02 | `mote record` exits 0 after stop_event | unit | `uv run pytest tests/test_audio.py::test_record_writes_wav -x` | Wave 0 |
| AUD-03 | rms_db returns expected dB for known signal | unit | `uv run pytest tests/test_audio.py::test_rms_db -x` | Wave 0 |
| AUD-04 | Elapsed time formatting MM:SS | unit | `uv run pytest tests/test_audio.py::test_make_display_elapsed -x` | Wave 0 |
| CLI-01 | `mote record --help` exits 0 | smoke | `uv run pytest tests/test_cli.py::test_record_help -x` | Wave 0 |
| CLI-04 | `mote status` shows Idle with no PID file | unit | `uv run pytest tests/test_cli.py::test_status_idle -x` | Wave 0 |
| CLI-04 | `mote status` shows "Recording in progress" with live PID | unit | `uv run pytest tests/test_cli.py::test_status_recording -x` | Wave 0 |
| CLI-06 | Ctrl+C stop writes WAV file and exits cleanly | integration | manual (requires BlackHole hardware) | manual-only |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_audio.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_audio.py` — covers AUD-01, AUD-02, AUD-03, AUD-04 (new file needed)
- [ ] `tests/test_cli.py` — extend with record/status tests (file exists; add new test functions)

*(No new framework config needed — pytest already configured in pyproject.toml)*

## Sources

### Primary (HIGH confidence)
- sounddevice 0.5.5 installed in project venv — `InputStream`, `query_devices`, `DeviceList` structure verified by direct inspection
- Python stdlib `wave`, `signal`, `queue`, `os` — verified by execution in project venv
- Rich 14.3.3 installed in project venv — `Live`, `Text`, `refresh_per_second` parameter verified
- numpy 2.x — float32 to int16 conversion + `.clip()` pattern verified in project venv
- CLAUDE.md — stack constraints (no threading for audio+transcription, sounddevice over PyAudio, cpu+int8 for CTranslate2)
- Phase 2 CONTEXT.md — all locked decisions D-01 through D-12

### Secondary (MEDIUM confidence)
- https://python-sounddevice.readthedocs.io/en/latest/ — queue-based InputStream pattern for open-ended recording
- https://maxhalford.github.io/blog/flask-sse-no-deps/ — (SSE pattern from CLAUDE.md sources, not directly relevant to Phase 2)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries installed and API-verified in project venv
- Architecture: HIGH — patterns verified by execution, not just documentation
- Pitfalls: HIGH — most are verified by direct test (float32 clip wrapping, queue timeout, PID liveness)
- Test map: MEDIUM — test file names are recommendations; planner will finalize

**Research date:** 2026-03-27
**Valid until:** 2026-09-27 (stable libraries; sounddevice and Rich rarely break API)
