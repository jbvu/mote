---
phase: 04-transcription-engine
plan: 02
subsystem: cli
tags: [cli, transcription, record-command, wav-lifecycle, testing]
dependency_graph:
  requires: [transcribe_file, get_wav_duration, config_value_to_alias, load_config]
  provides: [record_command_with_transcription_flags]
  affects: [src/mote/cli.py, tests/test_cli.py]
tech_stack:
  added: []
  patterns: [cli-flag-override, wav-delete-on-success, wav-keep-on-failure, config-resolution-chain]
key_files:
  created: []
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
decisions:
  - get_wav_duration called before transcribe_file so duration is available even after WAV deletion
  - Empty string api_key treated as None (normalizes config default empty string)
  - Existing tests that do not patch transcribe_file pass because they don't assert exit_code after recording
metrics:
  duration: 420s
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_changed: 2
---

# Phase 4 Plan 2: CLI Transcription Integration — Summary

**One-liner:** record_command extended with --engine/--language/--no-transcribe flags, auto-transcription after recording, WAV lifecycle management, and 6 new CLI tests.

## What Was Built

### src/mote/cli.py

Updated `record_command` with three new Click options and a full auto-transcription flow:

- `--engine [local|openai]` — overrides `transcription.engine` from config
- `--language [sv|no|da|fi|en]` — overrides `transcription.language` from config
- `--no-transcribe` — skips transcription entirely, leaves WAV on disk

Post-recording flow:
1. If `--no-transcribe`, return immediately (WAV kept)
2. Load config; resolve engine, language, model_alias, api_key
3. Read WAV duration before transcription (so it's available after delete)
4. Call `transcribe_file(wav_path, engine, language, model_alias, api_key)`
5. On success: delete WAV, print `"Transcription complete (M:SS, N,NNN words)"`
6. On `ClickException` (e.g. missing API key): re-raise — WAV stays on disk
7. On other exception: wrap in `ClickException` with `"WAV kept at: {path}"` — WAV stays on disk

### tests/test_cli.py

Added `_make_test_wav` helper and 6 new test functions:

| Test | Behavior verified |
|------|------------------|
| `test_record_auto_transcribes` | `transcribe_file` called with default engine="local", language="sv" |
| `test_record_engine_flag` | `--engine openai` passes engine="openai" to transcribe_file |
| `test_record_language_flag` | `--language en` passes language="en" to transcribe_file |
| `test_record_no_transcribe_flag` | `transcribe_file` not called; WAV still exists on disk |
| `test_record_deletes_wav_on_success` | WAV file does not exist after successful transcription |
| `test_record_keeps_wav_on_failure` | WAV file exists + "WAV kept at" in output when transcribe_file raises |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Read WAV duration before `transcribe_file` call | WAV is deleted on success; duration must be captured first |
| Treat empty string api_key as None | Config defaults to `openai = ""` — empty string should be treated the same as absent |
| Patch `mote.cli.get_wav_duration` in tests | Imported into cli namespace via `from mote.transcribe import ...; patch target is mote.cli.* |

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- **Before:** 121 tests (phases 1-4 plan 01)
- **After:** 127 tests (6 new in tests/test_cli.py)
- **Result:** All 127 pass

## Known Stubs

None — all functionality is fully implemented.

## Self-Check: PASSED
