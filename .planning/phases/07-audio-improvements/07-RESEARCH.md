# Phase 7: Audio Improvements - Research

**Researched:** 2026-03-29
**Domain:** macOS audio device switching, silence detection, crash recovery, CLI command groups
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Audio Switching via SwitchAudioSource**
- D-01: Detect SwitchAudioSource via `which SwitchAudioSource` at `mote record` startup. If missing, print advisory every time and continue (graceful degradation — user routes audio manually).
- D-02: When SwitchAudioSource is available, always auto-switch output to BlackHole on `mote record` — no confirmation, no config opt-in.
- D-03: Print one-line status on switch: `Switched audio output to BlackHole 2ch (was: MacBook Pro Speakers)`. On stop: `Restored audio output to MacBook Pro Speakers`.
- D-04: Before switching, write `~/.mote/audio_restore.json` with the previous output device name. Delete the file after successful restore.

**Silence Detection**
- D-05: Silence threshold — Claude picks the appropriate dB value (Claude's Discretion below).
- D-06: Duration: warn after 30 seconds of sustained silence (all chunks below threshold).
- D-07: Warn once per silent stretch. If audio resumes then goes silent again, warn again.
- D-08: Threshold and duration are hardcoded constants — not configurable in config.toml.

**Crash Recovery**
- D-09: On `mote record` startup, check for `~/.mote/audio_restore.json`. If found, auto-restore the original output device silently, print `Restored audio output to [device] (from previous crash)`, delete the file, then continue with normal recording flow.
- D-10: Add `mote audio restore` standalone command — reads `audio_restore.json` and restores the device.

**Warning Presentation**
- D-11: Silence warning appears inline in the Rich live display: `Recording  00:01:45  ▁▁▁▁▁  -58dB  ⚠ Silence detected — check audio routing`.
- D-12: Warning text is amber/yellow styled in the Rich display.

### Claude's Discretion
- Exact silence dB threshold value (D-05)
- Implementation of `audio` CLI command group structure
- Error handling for SwitchAudioSource failures (device not found, permission errors)
- Whether `mote audio restore` also appears as `mote restore` alias

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUD-05 | Audio output auto-switches to BlackHole before recording and restores original after; graceful degradation if SwitchAudioSource not installed | SwitchAudioSource CLI verified; subprocess.run pattern; audio_restore.json lifecycle mirrors existing PID file pattern |
| AUD-06 | User is warned if sustained silence (>30s) detected during recording; does not stop recording | Existing rms_db() function reused directly; silence tracking added to existing drain loop in record_session(); Rich Text.append() with style="bold yellow" for D-12 |
</phase_requirements>

## Summary

Phase 7 adds two independent but complementary features to `mote record`: automatic audio output switching via the `SwitchAudioSource` CLI tool, and inline silence detection warnings in the Rich live display.

Both features integrate cleanly with the existing codebase. The audio switching wraps `record_command()` in `cli.py` with a before/after pattern (detect → write restore file → switch → record → restore → delete file). The silence detection extends the existing main-thread drain loop in `record_session()` with a running counter and a warned flag — the `rms_db()` function already computes the values needed. The crash recovery check reads `audio_restore.json` at startup before any other pre-flight, mirroring the PID file lifecycle already in the codebase.

The `mote audio restore` standalone command requires adding an `audio` command group to `cli.py` — the same pattern as the existing `config` and `models` groups.

**Primary recommendation:** Implement audio switching entirely in `cli.py` (not `audio.py`) since it is a CLI orchestration concern and calls a subprocess. Implement silence detection in `audio.py` by extending `record_session()` to accept a silence callback, or by returning silence state as part of display data via `make_display()`. The callback approach is cleaner: `record_session()` calls an optional `on_silence_warning()` callable that `record_command()` provides.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SwitchAudioSource | 1.2.2 (Homebrew) | macOS audio output switching | Only maintained CLI tool for programmatic audio device switching on macOS; Homebrew formula tested on Sequoia |
| subprocess | stdlib | Run SwitchAudioSource commands | Standard Python way to call external CLI tools |
| shutil.which | stdlib | Detect SwitchAudioSource availability | Standard availability check; avoids catching FileNotFoundError from subprocess |
| json | stdlib | Read/write audio_restore.json | Simple key-value store; consistent with crash recovery anchor pattern |
| Rich Text | 14.3.3 (installed) | Inline silence warning styling | Already used in make_display(); append with style="bold yellow" adds amber color |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading.Event | stdlib | Silence state shared between drain loop and display | Already used in record_session() for stop signal |
| time.monotonic | stdlib | Silence duration tracking | Already used for elapsed time; reuse same start reference approach |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SwitchAudioSource | osascript `set volume output active...` | AppleScript can switch devices but is slower, more fragile, and harder to get/set the current device name cleanly |
| SwitchAudioSource | CoreAudio Python bindings (pyobjc) | pyobjc works but adds a heavy macOS-only dependency just for this feature; SwitchAudioSource is lighter |
| subprocess.run | subprocess.check_output | check_output raises on non-zero; run with check=True is equivalent but more explicit about error handling intent |

**Installation:**
```bash
brew install switchaudio-osx
```

## Architecture Patterns

### Recommended Project Structure
No new modules needed. All changes go into existing files:
```
src/mote/
├── audio.py         # Add silence detection state to record_session()
│                    # Extend make_display() signature or add make_display_with_warning()
└── cli.py           # Add audio command group + restore subcommand
                     # Wrap record_command() with switch/restore + crash recovery
```

### Pattern 1: SwitchAudioSource subprocess calls

**What:** Three subprocess calls wrap the recording session in `record_command()`.
**When to use:** Whenever SwitchAudioSource is available (detected via `shutil.which`).

```python
import json
import shutil
import subprocess
from pathlib import Path

AUDIO_RESTORE_FILE = "audio_restore.json"

def _detect_switch_audio_source() -> bool:
    """Return True if SwitchAudioSource is on PATH."""
    return shutil.which("SwitchAudioSource") is not None

def _get_current_output_device() -> str | None:
    """Return current audio output device name, or None on failure."""
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-t", "output", "-c"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, OSError):
        return None

def _set_output_device(device_name: str) -> bool:
    """Switch output to device_name. Return True on success."""
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-t", "output", "-s", device_name],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
```

### Pattern 2: audio_restore.json lifecycle (mirrors PID file)

**What:** Write before switching, delete after successful restore. Written at ~/.mote/audio_restore.json.
**When to use:** Every time SwitchAudioSource is available and switching is about to happen.

```python
def _write_audio_restore(config_dir: Path, device_name: str) -> None:
    restore_path = config_dir / AUDIO_RESTORE_FILE
    restore_path.write_text(json.dumps({"device": device_name}))

def _read_audio_restore(config_dir: Path) -> str | None:
    restore_path = config_dir / AUDIO_RESTORE_FILE
    if not restore_path.exists():
        return None
    try:
        data = json.loads(restore_path.read_text())
        return data.get("device")
    except (json.JSONDecodeError, OSError):
        return None

def _delete_audio_restore(config_dir: Path) -> None:
    restore_path = config_dir / AUDIO_RESTORE_FILE
    restore_path.unlink(missing_ok=True)
```

### Pattern 3: record_command() switch/restore wrapping

**What:** The recording session is wrapped with audio switching in a try/finally block so restore always runs even if recording raises.

```python
# In record_command(), after BlackHole detection:
has_switcher = _detect_switch_audio_source()
original_device = None

if has_switcher:
    original_device = _get_current_output_device()
    if original_device:
        _write_audio_restore(config_dir, original_device)
        ok = _set_output_device("BlackHole 2ch")
        if ok:
            click.echo(f"Switched audio output to BlackHole 2ch (was: {original_device})")
        else:
            _delete_audio_restore(config_dir)
            original_device = None  # failed — don't try to restore
    else:
        click.echo("Warning: Could not detect current audio output device. Skipping auto-switch.")
else:
    click.echo(
        "Advisory: SwitchAudioSource not installed — route audio to BlackHole manually.\n"
        "Install with: brew install switchaudio-osx"
    )

try:
    wav_path = record_session(device_index, recordings_dir, pid_path)
    click.echo(f"\nRecording saved: {wav_path}")
finally:
    if original_device:
        _set_output_device(original_device)
        _delete_audio_restore(config_dir)
        click.echo(f"Restored audio output to {original_device}")
```

### Pattern 4: Crash recovery check at startup

**What:** Reads audio_restore.json at the very start of record_command(), before all other checks. Restores and continues.

```python
# First thing in record_command(), before PID check:
restore_path = config_dir / AUDIO_RESTORE_FILE
crashed_device = _read_audio_restore(config_dir)
if crashed_device:
    ok = _set_output_device(crashed_device)
    if ok:
        _delete_audio_restore(config_dir)
        click.echo(f"Restored audio output to {crashed_device} (from previous crash)")
    else:
        click.echo(f"Warning: Could not restore audio to {crashed_device}. File kept at {restore_path}")
```

### Pattern 5: Silence detection in record_session() drain loop

**What:** The main-thread drain loop already tracks elapsed time and current_db. Add silence duration counter alongside. Call an optional callback when silence threshold is crossed.

```python
# Silence tracking constants (hardcoded per D-08)
SILENCE_THRESHOLD_DB = -50.0   # see "Silence threshold recommendation" section below
SILENCE_WARN_SECONDS = 30

# In record_session(), add to drain loop:
silence_start: float | None = None
silence_warned = False

while not stop_event.is_set():
    try:
        chunk = audio_queue.get(timeout=0.1)
        chunks.append(chunk)
        current_db = rms_db(chunk)

        # Silence tracking
        if current_db < SILENCE_THRESHOLD_DB:
            if silence_start is None:
                silence_start = time.monotonic()
            elif not silence_warned and (time.monotonic() - silence_start) >= SILENCE_WARN_SECONDS:
                silence_warned = True
                # signal warning to display layer
        else:
            # Audio resumed — reset for next stretch (D-07)
            silence_start = None
            silence_warned = False

    except queue.Empty:
        pass
    elapsed = int(time.monotonic() - start)
    live.update(make_display(elapsed, current_db, silence_warned))
```

### Pattern 6: Extending make_display() for silence warning

**What:** Add optional `silence_warning: bool = False` parameter. When True, append amber warning suffix per D-11, D-12.

```python
def make_display(elapsed_s: int, db: float, silence_warning: bool = False) -> Text:
    """Build Rich Text for the live recording display."""
    hours, rem = divmod(elapsed_s, 3600)
    mm, ss = divmod(rem, 60)
    bar = make_level_bar(db)
    t = Text()
    t.append("Recording  ")
    t.append(f"{hours:02d}:{mm:02d}:{ss:02d}", style="bold cyan")
    t.append(f"  {bar}", style="green")
    t.append(f"  {db:.0f}dB", style="dim")
    if silence_warning:
        t.append("  ⚠ Silence detected — check audio routing", style="bold yellow")
    return t
```

### Pattern 7: `audio` command group in cli.py

**What:** Add a Click group `audio` with subcommand `restore`. Follows the same pattern as the existing `config` and `models` groups.

```python
@cli.group()
def audio():
    """Audio device management."""
    pass

@audio.command("restore")
def audio_restore():
    """Restore system audio output if left on BlackHole after a crash."""
    config_dir = get_config_dir()
    device = _read_audio_restore(config_dir)
    if device is None:
        click.echo("No audio restore file found — audio output is not stuck.")
        return
    if not _detect_switch_audio_source():
        raise click.ClickException(
            "SwitchAudioSource not installed. Cannot restore automatically.\n"
            "Install with: brew install switchaudio-osx\n"
            f"Then run: SwitchAudioSource -t output -s '{device}'"
        )
    ok = _set_output_device(device)
    if ok:
        _delete_audio_restore(config_dir)
        click.echo(f"Restored audio output to {device}")
    else:
        raise click.ClickException(f"Failed to switch to '{device}'. Is the device available?")
```

### Anti-Patterns to Avoid

- **Switching inside audio.py:** Audio switching is a CLI orchestration concern (calls subprocess, prints status). Keep it in cli.py. audio.py stays pure audio capture.
- **Catching all exceptions in try/finally restore:** If `_set_output_device` raises OSError in the finally block, the exception will mask the original exception. Use a narrow try/except inside the finally.
- **Writing audio_restore.json in audio.py:** The file lifecycle must be managed by the same layer that does the switching (cli.py). audio.py doesn't know about switching.
- **Using subprocess.check_output:** Returns stdout but raises CalledProcessError on failure. Use subprocess.run with check=False and inspect returncode — more predictable for error handling.
- **Silence threshold too sensitive:** BlackHole captures complete silence (all zeros) when no audio is routed through it. The -60dB floor is exactly this case. A threshold too close to -60dB will false-positive during any brief pause. See Silence threshold recommendation below.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio device switching | Custom CoreAudio API calls via ctypes | SwitchAudioSource CLI | It already handles device enumeration, output type filtering, and macOS audio routing internals |
| SwitchAudioSource detection | Try/except on subprocess call | `shutil.which("SwitchAudioSource")` | which() is the standard idiom; subprocess will raise FileNotFoundError on missing tool which is harder to distinguish from other errors |
| Silence duration tracking | Thread with sleep loop | Counter in existing drain loop | The drain loop already runs at ~10Hz (100ms queue timeout); adding a float counter costs nothing and avoids thread coordination |

**Key insight:** All silence detection can be done inline in the existing `while not stop_event.is_set()` drain loop — no additional threads, queues, or timing machinery needed.

## Runtime State Inventory

Not applicable — this is a new feature phase, not a rename/refactor phase.

## Silence Threshold Recommendation

**Recommended value: `SILENCE_THRESHOLD_DB = -50.0`**

Reasoning:
- `rms_db()` floors at -60.0dB, which is returned for complete silence (np.zeros input)
- BlackHole with no audio routed through it typically returns near-zero data, landing at or near -60dB
- Normal meeting audio (speech, background) typically reads between -35dB and -10dB
- System noise floor (fan, idle hum) on macOS virtual devices via BlackHole is essentially -60dB — no thermal noise like physical mic
- -50dB gives a 10dB buffer above the floor, comfortably below any real audio signal, while clearly distinguishing "silence" from "very quiet speech"
- This matches the existing `make_level_bar()` scale: at -50dB the bar is ~17% full (10/60 = 0.167), which visually looks like silence

**Confidence:** MEDIUM — based on rms_db() implementation analysis and BlackHole's known behavior as a virtual device. No physical hardware testing possible in this session. The 10dB margin above -60dB floor is conservative and can be tuned if false positives occur.

## Common Pitfalls

### Pitfall 1: audio_restore.json not deleted on SwitchAudioSource failure during switch
**What goes wrong:** Switch fails (device name mismatch, tool error), but the restore file was already written. Next `mote record` startup sees the file and tries to restore to the old device even though the switch never happened.
**Why it happens:** Write-before-switch is correct for the crash case but requires cleanup on switch failure.
**How to avoid:** If `_set_output_device()` returns False (switch failed), immediately call `_delete_audio_restore()` before printing any error. Only keep the file if the switch succeeded.
**Warning signs:** Spurious "Restored audio output to X (from previous crash)" messages when no crash occurred.

### Pitfall 2: Silence counter not reset when audio resumes
**What goes wrong:** Per D-07, if audio resumes after a silent stretch, `silence_start` and `silence_warned` must both reset. If only `silence_warned` resets (not `silence_start`), the next silent chunk immediately counts from the old start time rather than starting a new 30-second window.
**Why it happens:** Logic that checks `silence_warned` to prevent spam but forgets to reset `silence_start`.
**How to avoid:** On audio-above-threshold, reset both `silence_start = None` AND `silence_warned = False`.
**Warning signs:** Second silence warning appears faster than 30 seconds after audio resumes.

### Pitfall 3: SwitchAudioSource device name case sensitivity
**What goes wrong:** `SwitchAudioSource -c` returns "MacBook Pro Speakers" but `SwitchAudioSource -s "macbook pro speakers"` fails silently (returncode 0 but device unchanged, or returncode non-zero).
**Why it happens:** SwitchAudioSource uses exact name matching (case-sensitive).
**How to avoid:** Use the device name exactly as returned by `-c`. Do not normalize/lowercase the stored device name in audio_restore.json.
**Warning signs:** `_set_output_device()` returns True (returncode 0) but audio is not actually restored.

### Pitfall 4: Finally block masking the original exception
**What goes wrong:** If record_session() raises an exception AND the restore call in the finally block also raises, the original exception is lost and only the finally exception propagates.
**Why it happens:** Python exception chaining — an unhandled raise in a finally replaces the original.
**How to avoid:**
```python
finally:
    if original_device:
        try:
            _set_output_device(original_device)
            _delete_audio_restore(config_dir)
            click.echo(f"Restored audio output to {original_device}")
        except Exception:
            pass  # Best-effort restore; don't mask original exception
```

### Pitfall 5: Crash recovery check order — must be BEFORE PID check
**What goes wrong:** If crash recovery check runs after the PID check, and the PID from the crashed session is somehow still in the file, the stale PID logic fires before recovery. More practically: if recovery is deferred, the user might not get their speakers back promptly.
**Why it happens:** Forgetting that crash recovery is user-facing UX that should happen immediately.
**How to avoid:** Per D-09, put the crash recovery check as the very first action in `record_command()`, before the PID alive-check.

### Pitfall 6: SwitchAudioSource timeout — use short timeout
**What goes wrong:** SwitchAudioSource hangs on Bluetooth device enumeration sometimes (see GitHub issue #76 about AirPlay devices). Without a timeout, `mote record` hangs.
**Why it happens:** The tool does device enumeration on every call; AirPlay/Bluetooth discovery can block.
**How to avoid:** Always pass `timeout=5` to `subprocess.run()`. On TimeoutExpired, treat as failure and skip switching with a warning.

## Code Examples

### Get current output device
```python
# Source: SwitchAudioSource README + verified behavior
result = subprocess.run(
    ["SwitchAudioSource", "-t", "output", "-c"],
    capture_output=True, text=True, timeout=5
)
current_device = result.stdout.strip()  # e.g. "MacBook Pro Speakers"
```

### Set output device
```python
result = subprocess.run(
    ["SwitchAudioSource", "-t", "output", "-s", "BlackHole 2ch"],
    capture_output=True, text=True, timeout=5
)
success = result.returncode == 0
```

### Rich Text with amber warning suffix
```python
# Source: Rich docs — Text.append() with style argument
from rich.text import Text

t = Text()
t.append("Recording  ")
t.append("00:01:45", style="bold cyan")
t.append("  ░░░░░░░░░░░░░░░░░░░░", style="green")
t.append("  -58dB", style="dim")
t.append("  ⚠ Silence detected — check audio routing", style="bold yellow")
```

### JSON restore file read/write
```python
import json
from pathlib import Path

# Write
path = config_dir / "audio_restore.json"
path.write_text(json.dumps({"device": "MacBook Pro Speakers"}))

# Read
data = json.loads(path.read_text())
device = data["device"]  # "MacBook Pro Speakers"

# Delete
path.unlink(missing_ok=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| osascript audio switching | SwitchAudioSource CLI | ~2011 (tool created) | Much cleaner output parsing; no AppleScript fragility |
| PyAudio for audio capture | sounddevice | Already in this project | N/A — already on current approach |

**No deprecated patterns in scope for this phase.**

## Open Questions

1. **Does SwitchAudioSource's `-s "BlackHole 2ch"` work when the device name is exactly "BlackHole 2ch"?**
   - What we know: The device name from `find_blackhole_device()` is the sounddevice name, which is typically "BlackHole 2ch". SwitchAudioSource should accept this.
   - What's unclear: Whether the SwitchAudioSource name and the sounddevice name are always identical.
   - Recommendation: In the implementation, use the device name from `find_blackhole_device()` to set the SwitchAudioSource target (not a hardcoded string), so they're guaranteed to match.

2. **Should `mote audio restore` also be available as `mote restore`?**
   - What we know: D-10 specifies `mote audio restore`. D-12 in Claude's Discretion allows the alias.
   - What's unclear: User preference.
   - Recommendation: Skip the alias. `mote audio restore` is clear and consistent with the group structure. Aliases add CLI surface area with no clear benefit for a recovery command.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SwitchAudioSource | AUD-05 audio switching | Not installed on dev machine | — | Graceful degradation per D-01: print advisory, continue |
| Python subprocess | SwitchAudioSource calls | Built-in | stdlib | — |
| Python json | audio_restore.json | Built-in | stdlib | — |
| Python shutil.which | Tool detection | Built-in | stdlib | — |
| macOS 15 Sequoia | Platform | Yes | 15.7.4 | — |

**Missing dependencies with no fallback:** None — SwitchAudioSource absence is handled by graceful degradation per D-01.

**Note on SwitchAudioSource macOS compatibility:** Homebrew formula `switchaudio-osx` v1.2.2 explicitly lists Sequoia (macOS 15) as a supported build target for Apple Silicon. This satisfies the STATE.md pending todo "Verify SwitchAudioSource works on macOS 14/15 before implementing Phase 7". **Confidence: HIGH** (from Homebrew formula page showing Sequoia binary).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_audio.py tests/test_cli.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUD-05 | SwitchAudioSource detected via shutil.which | unit | `uv run pytest tests/test_audio.py -k "switch" -x` | ❌ Wave 0 |
| AUD-05 | Switch to BlackHole on record start | unit | `uv run pytest tests/test_cli.py -k "switch" -x` | ❌ Wave 0 |
| AUD-05 | Restore original device on record stop | unit | `uv run pytest tests/test_cli.py -k "restore" -x` | ❌ Wave 0 |
| AUD-05 | Advisory printed when SwitchAudioSource missing | unit | `uv run pytest tests/test_cli.py -k "advisory" -x` | ❌ Wave 0 |
| AUD-05 | Crash recovery: audio_restore.json triggers restore on startup | unit | `uv run pytest tests/test_cli.py -k "crash_recovery" -x` | ❌ Wave 0 |
| AUD-05 | mote audio restore command exists and works | unit | `uv run pytest tests/test_cli.py -k "audio_restore" -x` | ❌ Wave 0 |
| AUD-05 | mote audio restore when no file found | unit | `uv run pytest tests/test_cli.py -k "audio_restore_no_file" -x` | ❌ Wave 0 |
| AUD-06 | Silence warning not shown before 30s | unit | `uv run pytest tests/test_audio.py -k "silence" -x` | ❌ Wave 0 |
| AUD-06 | Silence warning shown after 30s sustained silence | unit | `uv run pytest tests/test_audio.py -k "silence_warn" -x` | ❌ Wave 0 |
| AUD-06 | Silence warning resets when audio resumes | unit | `uv run pytest tests/test_audio.py -k "silence_reset" -x` | ❌ Wave 0 |
| AUD-06 | make_display with silence_warning=True contains warning text | unit | `uv run pytest tests/test_audio.py -k "display_silence" -x` | ❌ Wave 0 |
| AUD-06 | Recording does not stop during silence | unit | `uv run pytest tests/test_audio.py -k "silence_no_stop" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_audio.py tests/test_cli.py -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green (excluding pre-existing `test_download_model_passes_tqdm_class` failure) before `/gsd:verify-work`

### Wave 0 Gaps
All new test cases for this phase need to be created:
- [ ] `tests/test_audio.py` — add silence detection unit tests (SILENCE_THRESHOLD_DB, make_display silence_warning, silence counter reset logic)
- [ ] `tests/test_cli.py` — add SwitchAudioSource integration tests (mocked subprocess), crash recovery tests, `mote audio restore` command tests

*(Existing test infrastructure fully covers the framework — only new test functions needed, no new files.)*

## Project Constraints (from CLAUDE.md)

- **Platform:** macOS only — no cross-platform concerns for SwitchAudioSource
- **Security:** No new network calls, no config file changes for this phase
- **Tech stack:** Python, Click, Rich — all already in use; `subprocess` is stdlib
- **Distribution:** No new pip dependencies introduced by this phase — SwitchAudioSource is an OS-level tool (brew), not a Python package
- **Audio:** BlackHole 2ch assumed installed (existing pre-flight check)
- **No threading for audio+transcription:** The silence detection is in-loop (main thread), not a new thread — compliant
- **Config:** No new config keys — D-08 locks threshold/duration as hardcoded constants

## Sources

### Primary (HIGH confidence)
- Homebrew formula: https://formulae.brew.sh/formula/switchaudio-osx — v1.2.2, macOS Sequoia listed as supported binary target
- GitHub: https://github.com/deweller/switchaudio-osx — CLI flags reference (-t output -c, -t output -s)
- Existing codebase: `src/mote/audio.py` — rms_db(), make_display(), record_session() drain loop pattern
- Existing codebase: `src/mote/cli.py` — command group patterns (config, models), PID file lifecycle

### Secondary (MEDIUM confidence)
- WebSearch: SwitchAudioSource -t output -c returns device name as plain stdout line (verified by multiple usage examples)
- rms_db() analysis: -50dB threshold recommendation based on function implementation and BlackHole virtual device characteristics

### Tertiary (LOW confidence)
- SwitchAudioSource AirPlay/Bluetooth hanging behavior: reported in GitHub issues, timeout=5 recommendation is defensive

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already installed; SwitchAudioSource Homebrew formula confirms Sequoia support
- Architecture: HIGH — all patterns extend existing code directly; no novel patterns
- Pitfalls: HIGH for exception handling/state management; MEDIUM for silence threshold value
- Environment: HIGH — dev machine confirmed macOS 15.7.4; SwitchAudioSource not installed but graceful degradation is the designed behavior

**Research date:** 2026-03-29
**Valid until:** 2026-09-29 (stable tooling, no fast-moving dependencies)
