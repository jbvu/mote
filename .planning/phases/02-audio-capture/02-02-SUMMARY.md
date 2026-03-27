---
phase: 02-audio-capture
plan: 02
subsystem: cli
tags: [click, record, status, blackhole, pid, orphan, tdd, checkpoint]

# Dependency graph
requires:
  - phase: 02-audio-capture
    plan: 01
    provides: find_blackhole_device, record_session, is_recording_active, find_orphan_recordings

provides:
  - "mote record command: BlackHole detection, orphan warning, PID guard, calls record_session"
  - "mote status command: PID-based Idle/Recording in progress reporting"

affects:
  - Phase 03 (transcription commands will reuse config_dir / recordings patterns)

# Tech tracking
tech-stack:
  added: []  # No new dependencies
  patterns:
    - "Patch mote.cli.name (not mote.audio.name) when testing Click commands that import functions directly"
    - "find_blackhole_device returns dict with 'index' key for sd.InputStream compatibility"

key-files:
  created: []
  modified:
    - src/mote/cli.py
    - src/mote/audio.py
    - tests/test_cli.py

key-decisions:
  - "Patch target for mocked CLI functions is mote.cli.* not mote.audio.* — Click imports functions into cli module namespace"
  - "find_blackhole_device fixed to include numeric 'index' key via enumerate() — required for sd.InputStream(device=int)"

# Metrics
duration: 10min
completed: 2026-03-27
---

# Phase 2 Plan 2: CLI Record and Status Commands Summary

**`mote record` and `mote status` CLI commands wired to audio.py with BlackHole detection, orphan warning, PID guard, and 9 new CLI tests — stopped at human-verify checkpoint awaiting hardware test**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-27T19:07:53Z
- **Completed (Task 1):** 2026-03-27
- **Tasks:** 1 of 2 (Task 2 is human-verify checkpoint, not yet approved)
- **Files modified:** 3

## Accomplishments

- Implemented `mote status` command: reads PID file, reports "Recording in progress (PID N)" or "Idle", cleans stale PIDs
- Implemented `mote record` command: BlackHole detection with brew install instructions on failure, orphan WAV warning with file sizes, PID guard preventing double recording, stale PID cleanup with warning, delegates to `record_session`
- Fixed `find_blackhole_device` to include numeric `"index"` key via `enumerate()` — required for `sd.InputStream(device=int)`
- Written 9 new CLI tests covering all behaviors; all pass
- Full test suite: 52 tests pass (no regressions)

## Task Commits

1. **Task 1 (RED): Failing tests** — `a363ebc` (test)
2. **Task 1 (GREEN): Implementation** — `1c85268` (feat)

## Files Created/Modified

- `/Users/johan/Library/Mobile Documents/com~apple~CloudDocs/mote/src/mote/cli.py` — Added `status_command` and `record_command` Click commands; added imports from mote.audio and mote.config.get_config_dir
- `/Users/johan/Library/Mobile Documents/com~apple~CloudDocs/mote/src/mote/audio.py` — Fixed `find_blackhole_device` to include numeric `"index"` key in returned dict
- `/Users/johan/Library/Mobile Documents/com~apple~CloudDocs/mote/tests/test_cli.py` — 9 new tests for record and status commands

## Decisions Made

- Mock patch targets for CLI tests must be `mote.cli.find_blackhole_device` and `mote.cli.record_session` (the imported names in cli.py's namespace), not `mote.audio.*`
- `find_blackhole_device` must include `"index"` in the returned dict since sounddevice's `sd.InputStream(device=...)` requires a numeric index, not the device dict itself

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed find_blackhole_device to include numeric device index**
- **Found during:** Task 1 implementation
- **Issue:** `find_blackhole_device` returned device dicts without a numeric "index" key; `record_session` requires `device_index: int` for `sd.InputStream(device=int)`
- **Fix:** Changed for loop to `enumerate()` and added `device_with_index["index"] = i`
- **Files modified:** `src/mote/audio.py`
- **Commit:** `1c85268`

**2. [Rule 1 - Bug] Fixed test patch targets from mote.audio.* to mote.cli.***
- **Found during:** Task 1 TDD GREEN phase (test_record_stale_pid_allows_start failed)
- **Issue:** Tests patched `mote.audio.find_blackhole_device` but `cli.py` imports the function directly into its namespace — the mock didn't intercept the call
- **Fix:** Changed patch targets to `mote.cli.find_blackhole_device` and `mote.cli.record_session`
- **Files modified:** `tests/test_cli.py`
- **Commit:** `1c85268`

## Checkpoint Status

**Stopped at Task 2: human-verify checkpoint**

Task 1 is complete with all tests passing. The plan requires hardware verification with a real BlackHole device before marking complete. See checkpoint details below.

### What to Verify

1. Run `uv pip install -e .` first (reinstalls entry point after source changes)
2. Run `uv run mote status` — should show "Idle"
3. Ensure BlackHole 2ch is installed (`brew list blackhole-2ch`)
4. Route system audio through BlackHole
5. Play audio, then run `uv run mote record`
   - Should print "Recording from BlackHole 2ch (16kHz mono)"
   - Should show live display with level bar and elapsed time
   - Level bar should move with audio signal
6. In another terminal: `uv run mote status` — should show "Recording in progress (PID ...)"
7. Press Ctrl+C — should stop cleanly, print "Recording saved: ~/.mote/recordings/mote_*.wav"
8. Run `uv run mote status` — should show "Idle"
9. `file ~/.mote/recordings/mote_*.wav` — should show RIFF/WAVE/16-bit/mono/16000Hz

## Known Stubs

None — all functions call real implementation; no placeholder data.

## Self-Check

- [x] `src/mote/cli.py` contains `from mote.audio import`
- [x] `src/mote/cli.py` contains `@cli.command("record")`
- [x] `src/mote/cli.py` contains `@cli.command("status")`
- [x] `src/mote/cli.py` contains `find_blackhole_device()`
- [x] `src/mote/cli.py` contains `brew install blackhole-2ch`
- [x] `src/mote/cli.py` contains `Recording already in progress`
- [x] `src/mote/cli.py` contains `Recording saved:`
- [x] `src/mote/cli.py` contains `"Idle"` in status_command
- [x] `src/mote/cli.py` contains `"Recording in progress"` in status_command
- [x] `tests/test_cli.py` contains `def test_record_help`
- [x] `tests/test_cli.py` contains `def test_status_idle`
- [x] `tests/test_cli.py` contains `def test_status_recording`
- [x] `tests/test_cli.py` contains `def test_record_no_blackhole`
- [x] Commits `a363ebc` (RED) and `1c85268` (GREEN) exist
- [x] `uv run pytest tests/test_cli.py -x` exits 0 (16 passed)
- [x] `uv run pytest tests/ -x` exits 0 (52 passed)

## Self-Check: PASSED

---
*Phase: 02-audio-capture*
*Completed Task 1: 2026-03-27 — awaiting human-verify checkpoint for Task 2*
