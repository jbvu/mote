---
phase: 06-cli-polish-and-config-reliability
plan: 01
subsystem: config-and-output
tags: [config-validation, json-output, wav-cleanup, tdd]
dependency_graph:
  requires: []
  provides: [validate_config, cleanup_old_wavs, json-output-format]
  affects: [plan-02-transcribe-command, plan-03-cli-wiring]
tech_stack:
  added: []
  patterns: [function-based-modules, tdd-red-green, mock-patch-imports]
key_files:
  created: []
  modified:
    - src/mote/config.py
    - src/mote/output.py
    - tests/test_config.py
    - tests/test_output.py
key_decisions:
  - validate_config() imports are at module level (not lazy) — config.py has no startup cost concern unlike transcribe.py
  - JSON output is opt-in by not adding 'json' to default config format list — avoids file clutter per D-08 guidance
  - cleanup_old_wavs() returns early if retention_days <= 0 to support 'keep forever' semantics
metrics:
  duration_seconds: 175
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_modified: 4
---

# Phase 6 Plan 1: Library Foundations Summary

validate_config() with 4-check D-03 logic, cleanup_old_wavs() with mtime-based WAV deletion, [cleanup] section in default config, and JSON output branch in write_transcript() with UTF-8 Swedish character preservation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for validate_config, cleanup_old_wavs, default config | 3d60d5b | tests/test_config.py |
| 1 (GREEN) | Implement validate_config(), cleanup_old_wavs(), [cleanup] default | 587155c | src/mote/config.py |
| 2 (RED) | Failing tests for JSON output format | 885d86e | tests/test_output.py |
| 2 (GREEN) | Implement JSON branch in write_transcript() | 3c5a111 | src/mote/output.py |

## Verification

```
47 passed in 0.52s (tests/test_config.py + tests/test_output.py)
```

Full suite: 168 passed, 1 pre-existing failure (test_download_model_passes_tqdm_class — unrelated to this plan).

## What Was Built

### validate_config() in src/mote/config.py

Four validation checks per D-03:
1. Engine name must be 'local' or 'openai' — error if invalid
2. Model availability check when engine=local via is_model_downloaded() — error if not downloaded
3. Output dir exists as directory or can be created — error if path is a file
4. API key presence when engine=openai — warning (not error) if api_keys.openai is empty

Returns `(errors: list[str], warnings: list[str])`. Absent v2 config keys produce no errors per D-06.

### cleanup_old_wavs() in src/mote/config.py

Scans recordings_dir for *.wav files with mtime older than cutoff = now - retention_days*86400. Returns list of deleted paths. Returns [] for nonexistent dir or retention_days <= 0.

### [cleanup] section in default config

`_write_default_config()` now adds `[cleanup]` section with `wav_retention_days = 7` (days). New installs get this automatically; existing v1 configs without this section are valid per D-06.

### JSON output format in src/mote/output.py

Added `if "json" in formats:` branch after the `txt` branch. Produces a flat 7-key JSON payload matching the YAML frontmatter fields: `date`, `duration`, `words`, `engine`, `language`, `model`, `transcript`. Uses `json.dumps(..., ensure_ascii=False)` so Swedish characters (a-ring, a-umlaut, o-umlaut) are stored as literal UTF-8 rather than \uXXXX escape sequences. Filename reuses `_build_filename()` with `.json` extension.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functions are fully wired and tested.

## Self-Check: PASSED

Files exist:
- src/mote/config.py — FOUND
- src/mote/output.py — FOUND
- tests/test_config.py — FOUND
- tests/test_output.py — FOUND

Commits exist:
- 3d60d5b — FOUND
- 587155c — FOUND
- 885d86e — FOUND
- 3c5a111 — FOUND
