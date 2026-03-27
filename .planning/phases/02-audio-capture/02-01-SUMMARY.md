---
phase: 02-audio-capture
plan: 01
subsystem: audio
tags: [sounddevice, numpy, rich, wave, blackhole, pid, tdd]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: get_config_dir() for recordings/ and mote.pid paths, mote_home test fixture

provides:
  - find_blackhole_device: detects BlackHole input device, prefers 2ch (D-08)
  - rms_db: float32 RMS dB with -60dB floor
  - make_level_bar: ASCII block bar mapping -60..0dB
  - make_display: Rich Text with HH:MM:SS elapsed + level bar + dB (D-01)
  - write_wav: stdlib wave, 16kHz mono 16-bit with float32 clip (D-06)
  - new_recording_path: timestamped WAV path in recordings/ dir (D-04)
  - is_recording_active: PID file liveness check (D-10, D-11, D-12)
  - find_orphan_recordings: sorted glob of *.wav (D-05)
  - record_session: full queue-based InputStream recording engine

affects:
  - 02-02 (CLI record/status commands that wire these functions to Click commands)

# Tech tracking
tech-stack:
  added: []  # No new dependencies — all already in pyproject.toml
  patterns:
    - "Queue-based InputStream callback: PortAudio thread enqueues, main thread drains"
    - "threading.Event stop signal set by SIGINT handler on main thread"
    - "float32 capture -> clip -> int16 for WAV write (prevents overflow wrapping)"
    - "PID file lifecycle in try/finally block (prevents stale PID on crash)"
    - "queue.get(timeout=0.1) to avoid blocking forever after stop_event"

key-files:
  created:
    - src/mote/audio.py
    - tests/test_audio.py
  modified: []

key-decisions:
  - "make_display uses HH:MM:SS format (not MM:SS) so recordings > 1 hour display correctly"
  - "Ctrl+C hint printed once before Live context (simpler than Group/newline in Live)"
  - "find_orphan_recordings returns empty list if recordings dir absent (not an error)"

patterns-established:
  - "TDD RED-GREEN: write failing tests first, commit, then implement, run green"
  - "sounddevice device detection: always call find_blackhole_device() at start (never persist index)"
  - "PID file write/delete wrapped in try/finally in record_session"

requirements-completed: [AUD-01, AUD-02, AUD-03, AUD-04]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 2 Plan 1: Audio Capture Core Module Summary

**Queue-based BlackHole InputStream recording engine with Rich live display, RMS dB metering, stdlib WAV writing, PID file tracking, and 23 unit tests covering all pure functions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T19:03:15Z
- **Completed:** 2026-03-27T19:05:19Z
- **Tasks:** 1 (TDD: RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- Implemented all 9 exported functions in `src/mote/audio.py` with full docstrings
- Written 23 unit tests covering BlackHole detection, dB math, level bar, WAV I/O, PID management, orphan detection — all pass
- Full test suite (43 tests) passes with no regressions from Phase 1
- record_session wires all components: InputStream → queue → dB → Rich Live → WAV write

## Task Commits

1. **Task 1 (RED): Failing tests** — `e1d1a91` (test)
2. **Task 1 (GREEN): Implementation** — `72ff84e` (feat)

## Files Created/Modified

- `/Users/johan/Library/Mobile Documents/com~apple~CloudDocs/mote/src/mote/audio.py` — Full audio capture module: BlackHole detection, recording engine, WAV write, PID management, display helpers
- `/Users/johan/Library/Mobile Documents/com~apple~CloudDocs/mote/tests/test_audio.py` — 23 unit tests for all pure functions in audio.py

## Decisions Made

- `make_display` uses HH:MM:SS format instead of MM:SS — recordings can exceed one hour
- "Ctrl+C to stop" hint printed once before entering the Rich Live context — simpler than embedding in Live with Group, and matches D-03 requirement (hint visible below live line at start)
- `find_orphan_recordings` returns empty list when recordings directory doesn't exist — consistent with the "no orphans" semantic rather than raising FileNotFoundError

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all patterns were pre-verified in RESEARCH.md. Tests went RED on first run and GREEN after implementation with no debugging required.

## User Setup Required

None — no external service configuration required. BlackHole device must be installed (`brew install blackhole-2ch`) but that is a system prerequisite documented in CLAUDE.md.

## Next Phase Readiness

- `src/mote/audio.py` exports all 9 functions ready for Plan 02-02 CLI wiring
- CLI Plan 02-02 can immediately import `find_blackhole_device`, `record_session`, `is_recording_active`, `find_orphan_recordings` for `mote record` and `mote status` commands
- No blockers

## Self-Check

- [x] `src/mote/audio.py` exists with all 9 functions
- [x] `tests/test_audio.py` exists with 23 tests
- [x] Commits e1d1a91 (RED) and 72ff84e (GREEN) exist
- [x] `uv run pytest tests/test_audio.py -x` exits 0 (23 passed)
- [x] `uv run pytest tests/ -x` exits 0 (43 passed)

---
*Phase: 02-audio-capture*
*Completed: 2026-03-27*
