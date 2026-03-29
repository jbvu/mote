---
phase: 07-audio-improvements
plan: 02
subsystem: cli
tags: [audio-routing, switchaudiosource, crash-recovery, cli]
dependency_graph:
  requires: [src/mote/cli.py, src/mote/audio.py, src/mote/config.py]
  provides: [audio switching, crash recovery, mote audio restore command]
  affects: [src/mote/cli.py, tests/test_cli.py]
tech_stack:
  added: [shutil.which, subprocess.run for SwitchAudioSource]
  patterns: [try/finally for audio restore, crash recovery file pattern]
key_files:
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
decisions:
  - "Crash recovery check is the first action in record_command, before PID check — ensures audio is restored even if PID file is also stale"
  - "try/finally wraps record_session only (not transcription) — audio must be restored immediately when recording stops, not after potentially-long transcription"
  - "Failed switch to BlackHole immediately deletes audio_restore.json — no orphaned restore file if switch never happened (Pitfall 1)"
  - "inner try/except: pass inside finally — prevents masking recording exceptions with restore errors (Pitfall 4)"
  - "Advisory uses mote audio restore not direct SwitchAudioSource command — keeps UX in mote namespace"
metrics:
  duration: 15min
  completed: "2026-03-29"
  tasks_completed: 2
  files_modified: 2
---

# Phase 7 Plan 02: BlackHole Audio Switching Summary

Auto-switches system audio output to BlackHole 2ch on `mote record` start and restores original device on stop, with crash recovery via audio_restore.json and a standalone `mote audio restore` command.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SwitchAudioSource helpers and audio_restore.json lifecycle | ff63aa4 | src/mote/cli.py |
| 2 | Wire audio switching into record_command + audio restore command | 53ef2a7 | src/mote/cli.py, tests/test_cli.py |

## What Was Built

### Task 1: SwitchAudioSource helpers

Added to `src/mote/cli.py`:
- `import json`, `import shutil`, `import subprocess`
- `AUDIO_RESTORE_FILE = "audio_restore.json"` constant
- `_detect_switch_audio_source()` — checks PATH via shutil.which
- `_get_current_output_device()` — calls `SwitchAudioSource -t output -c` with 5s timeout
- `_set_output_device(name)` — calls `SwitchAudioSource -t output -s name` with 5s timeout
- `_write_audio_restore(config_dir, device)` — writes `{"device": name}` JSON
- `_read_audio_restore(config_dir)` — reads JSON, returns None on missing/malformed
- `_delete_audio_restore(config_dir)` — unlink with missing_ok=True

### Task 2: Audio switching wired into record_command

Changes to `record_command()`:
1. **Crash recovery** (first action, before PID check): reads audio_restore.json, if present and SwitchAudioSource available, restores device and deletes file with message "from previous crash"
2. **Pre-recording audio switch**: after BlackHole detection, detects current device, writes restore file, switches to BlackHole 2ch, prints switch message
3. **try/finally around record_session**: finally block restores audio to original device on any exit path
4. **Failed switch cleanup**: if switch to BlackHole fails, immediately deletes restore file and sets original_device=None so finally block won't attempt restore

Added `audio` command group with `restore` subcommand:
- `mote audio restore` — reads restore file, switches back to saved device, deletes file
- Raises ClickException with brew install instructions if SwitchAudioSource not installed
- Prints "No audio restore file found" if no file exists

## Test Coverage

Added 26 new tests in `tests/test_cli.py`:
- 15 tests for helper functions (Task 1)
- 11 tests for audio switching integration and audio restore command (Task 2)
- All 78 CLI tests pass; full suite 227 passing (1 pre-existing unrelated failure in test_models.py)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is fully wired.

## Self-Check: PASSED

- `src/mote/cli.py` modified: confirmed (contains all 6 helpers, crash recovery, switching logic, audio group)
- `tests/test_cli.py` modified: confirmed (26 new tests)
- Commits exist: f4e2c3f (RED tests Task 1), ff63aa4 (GREEN Task 1), 5041a7e (RED tests Task 2), 53ef2a7 (GREEN Task 2)
- `uv run pytest tests/test_cli.py -q` passes (78/78)
