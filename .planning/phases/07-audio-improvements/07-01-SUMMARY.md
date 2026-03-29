---
phase: "07-audio-improvements"
plan: "01"
subsystem: "audio"
tags: ["silence-detection", "recording", "rich-display", "tdd"]
dependency_graph:
  requires: []
  provides: ["silence-detection", "SilenceTracker", "make_display-silence_warning"]
  affects: ["src/mote/audio.py", "tests/test_audio.py"]
tech_stack:
  added: []
  patterns: ["SilenceTracker class for testable state tracking", "TDD red-green cycle"]
key_files:
  created: []
  modified:
    - "src/mote/audio.py"
    - "tests/test_audio.py"
decisions:
  - "SilenceTracker class over inline variables — cleaner for unit testing via time.monotonic mock"
  - "One-shot warning per silence stretch — no repeated triggers until audio resumes"
  - "SILENCE_THRESHOLD_DB = -50.0 and SILENCE_WARN_SECONDS = 30 hardcoded per D-08"
metrics:
  duration_seconds: 125
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_modified: 2
---

# Phase 7 Plan 01: Silence Detection Warning Summary

**One-liner:** Inline silence detection that warns users after 30s of sustained silence when audio routing is broken, implemented via `SilenceTracker` class and extended `make_display`.

## What Was Built

Added silence detection to the recording display loop so users see a bold yellow warning when sustained silence suggests BlackHole audio routing is not active.

### Changes to `src/mote/audio.py`

- Added `SILENCE_THRESHOLD_DB = -50.0` and `SILENCE_WARN_SECONDS = 30` constants after the recording constants block
- Extended `make_display(elapsed_s, db, silence_warning=False)` signature with optional `silence_warning` parameter — backward compatible, appends `"bold yellow"` styled warning text when True
- Added `SilenceTracker` class with `update(db) -> bool` method that tracks silence duration and returns True after 30s of sustained silence below threshold
- Updated `record_session` to instantiate `SilenceTracker()` and pass `silence_warned = silence.update(current_db)` to `make_display`

### Changes to `tests/test_audio.py`

Added 13 new silence-related tests:
- `test_silence_threshold_db_value` — constant equals -50.0
- `test_silence_warn_seconds_value` — constant equals 30
- `test_make_display_no_silence_warning_by_default` — backward compat
- `test_make_display_silence_warning_false` — no warning when False
- `test_make_display_silence_warning_true_contains_message` — message content
- `test_make_display_silence_warning_style` — bold yellow style applied
- `test_rms_db_complete_silence_below_threshold` — zeros return -60dB < -50dB
- `test_rms_db_quiet_audio_above_threshold` — 0.01 amplitude returns ~-40dB > -50dB
- `test_silence_tracker_no_warn_before_threshold` — no warn at 29s
- `test_silence_tracker_warns_at_threshold` — warn at 30s
- `test_silence_tracker_resets_on_audio` — new window after audio resumes
- `test_silence_tracker_no_spam` — stays True during same silence stretch

## Test Results

All 35 audio tests pass. Full suite: 216 passing (1 pre-existing unrelated failure in test_models.py::test_download_model_passes_tqdm_class — not caused by this plan).

## Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| 1 RED | d94a6a6 | test | Failing tests for silence constants and make_display silence_warning |
| 1 GREEN | 3478840 | feat | Add silence detection constants and extend make_display |
| 2 RED | e575b7e | test | Failing tests for SilenceTracker class |
| 2 GREEN | 33c4696 | feat | Add SilenceTracker class and integrate into record_session |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all silence detection logic is fully wired. `SilenceTracker` state flows from the drain loop to `make_display`, which renders the warning in the live display.

## Self-Check: PASSED

- `src/mote/audio.py` exists and contains `SILENCE_THRESHOLD_DB`, `SilenceTracker`, `silence_warning` parameter
- `tests/test_audio.py` exists and contains all 4 `test_silence_tracker_*` functions
- All 4 commits confirmed in git log: d94a6a6, 3478840, e575b7e, 33c4696
</content>
</invoke>