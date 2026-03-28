---
phase: "05"
plan: "02"
subsystem: cli
tags: [cli, output, transcription, write_transcript, list_command, integration-tests]
dependency_graph:
  requires: [05-01]
  provides: [record_command_with_name, list_command]
  affects: []
tech_stack:
  added: []
  patterns: [mock-patching-for-isolation, rich-table-display]
key_files:
  created: []
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
decisions:
  - "write_transcript is called before wav_path.unlink() — WAV preservation on failure requires this ordering"
  - "Summary line uses unicode arrow (→) and lists output filenames for clear feedback"
  - "mote list defaults to 20 most recent transcripts; --all shows unbounded list"
  - "Existing tests patched to also mock write_transcript — prevents filesystem pollution to ~/Documents/mote during tests"
metrics:
  duration: "10 minutes"
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_created: 0
  tests_added: 7
---

# Phase 05 Plan 02: CLI Output Wiring Summary

**One-liner:** CLI wired to write_transcript() with --name flag, WAV-after-write ordering, and a Rich-table mote list command backed by list_transcripts().

## What Was Built

Updated `src/mote/cli.py` to complete the capture-to-file workflow:

- `--name` flag added to `record_command` — passes a sanitized name through to `write_transcript()` for named output files (e.g., `mote record --name standup` produces `2026-03-28_1000_standup.md`).
- `write_transcript()` wired into transcription block, called **before** `wav_path.unlink()` — WAV is preserved if file writing fails (per D-14).
- Summary line updated to include arrow and output filenames: `Transcription complete (5:22, 1,234 words) → 2026-03-28_1000.md, 2026-03-28_1000.txt`
- `mote list` command added — reads `output.dir` from config, calls `list_transcripts()`, renders a Rich table with Filename, Date, Duration, Words, Engine columns. Defaults to 20 most recent; `--all` shows all.
- `pathlib.Path` import added.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add --name flag and wire write_transcript() into record_command | bd1a66f | src/mote/cli.py |
| 2 | Add CLI integration tests for write wiring and list command | e3102fb | tests/test_cli.py |

## Test Results

- 7 new tests added in tests/test_cli.py — all passing
- 4 existing tests updated to add `write_transcript` mock (prevents filesystem pollution)
- Full suite: 152 passed (up from 145)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test filesystem pollution in existing transcription tests**
- **Found during:** Task 2 analysis
- **Issue:** After wiring `write_transcript()` into `record_command`, existing tests like `test_record_auto_transcribes` and `test_record_deletes_wav_on_success` would call the real `write_transcript()` during test runs, creating files in `~/Documents/mote` on the developer's filesystem.
- **Fix:** Added `patch("mote.cli.write_transcript", return_value=fake_written)` to 4 existing tests that exercise the transcription path: `test_record_auto_transcribes`, `test_record_engine_flag`, `test_record_language_flag`, `test_record_deletes_wav_on_success`.
- **Files modified:** tests/test_cli.py
- **Commit:** e3102fb

**2. [Rule 1 - Bug] Fixed Rich table truncation in test assertions**
- **Found during:** Task 2 (first test run)
- **Issue:** Rich truncates long filenames with `…` in table cells. Tests asserting `"meeting-one" in result.output` failed because the table showed `meeting-o…`.
- **Fix:** Adjusted assertions to check for prefix substrings (`"meeting-o"`, `"meeting-t"`) and used `.md` count for the --all flag row-count test.
- **Files modified:** tests/test_cli.py
- **Commit:** e3102fb

## Known Stubs

None — all functions fully implemented. `write_transcript()` writes real files, `list_command` reads real metadata.

## Self-Check: PASSED

- src/mote/cli.py contains `from mote.output import write_transcript, list_transcripts, _sanitize_name`
- src/mote/cli.py contains `@click.option("--name"` on record_command
- src/mote/cli.py contains `def record_command(engine, language, no_transcribe, name):`
- src/mote/cli.py contains `write_transcript(` call BEFORE `wav_path.unlink(missing_ok=True)`
- src/mote/cli.py contains `.expanduser()` on output_dir Path construction
- src/mote/cli.py contains `def list_command(show_all):`
- src/mote/cli.py contains `@cli.command("list")`
- src/mote/cli.py contains `records[:20]` for default limit
- src/mote/cli.py contains `"No transcripts found."` for empty case
- tests/test_cli.py contains all 7 new test functions
- Commits bd1a66f and e3102fb confirmed in git log
- Full test suite: 152 passed
