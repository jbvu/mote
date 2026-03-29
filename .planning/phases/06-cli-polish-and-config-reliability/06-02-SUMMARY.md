---
phase: 06-cli-polish-and-config-reliability
plan: 02
subsystem: cli
tags: [transcribe-command, shared-helper, output-format, tdd]
dependency_graph:
  requires: [06-01-json-output]
  provides: [_run_transcription-helper, transcribe-command, output-format-flag]
  affects: [plan-03-config-wiring]
tech_stack:
  added: []
  patterns: [tdd-red-green, shared-helper-extraction, click-path-argument]
key_files:
  created: []
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
key_decisions:
  - _run_transcription() lives in cli.py (not a new module) because it depends on click.echo — a CLI concern
  - transcribe_command passes delete_wav=False to preserve the user's source WAV file
  - WAV mtime used as write_transcript timestamp so overwrite detection is deterministic (Pitfall 5)
  - Overwrite detection checks predicted filenames before calling _run_transcription — prompt shown once per format
metrics:
  duration_seconds: 480
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_modified: 2
---

# Phase 6 Plan 2: CLI Transcription Refactor Summary

_run_transcription() shared helper extracted from record_command with delete_wav/timestamp params; mote transcribe <file> command added with --engine/--language/--name/--output-format flags, WAV mtime timestamp, and overwrite detection; --output-format json flag wired on both record and transcribe.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for _run_transcription and --output-format record | 0dfc21a | tests/test_cli.py |
| 1 (GREEN) | Extract _run_transcription(), add --output-format to record | 692c305 | src/mote/cli.py |
| 2 (RED) | Failing tests for mote transcribe command | 6f9c96e | tests/test_cli.py |
| 2 (GREEN) | Add transcribe_command with overwrite detection | 67ae3dc | src/mote/cli.py |

## Verification

```
39 passed in 0.86s (tests/test_cli.py)
176 passed, 1 pre-existing failure (tests/test_models.py::test_download_model_passes_tqdm_class — unrelated)
```

## What Was Built

### _run_transcription() helper in src/mote/cli.py

Shared post-recording transcription pipeline used by both record_command and transcribe_command (D-12). Signature:

```python
def _run_transcription(
    wav_path: Path,
    engine: str,
    language: str,
    model_alias: str,
    api_key: str | None,
    output_dir: Path,
    formats: list[str],
    name: str | None,
    delete_wav: bool = True,
    timestamp: datetime | None = None,
) -> list[Path]:
```

Calls get_wav_duration, transcribe_file, write_transcript in order. Deletes WAV only if delete_wav=True. Prints summary line. Returns list of written paths.

### record_command refactored to use _run_transcription()

Lines 142-181 of the old record_command replaced with _run_transcription() call. Added --output-format json flag (extra_formats). Existing test_record_name_flag still passes — write_transcript call signature preserved.

### transcribe_command in src/mote/cli.py

New top-level command: `mote transcribe <wav_file>`. Accepts:
- WAV file path (click.Path(exists=True, path_type=Path) — validated by Click)
- --engine, --language, --name, --output-format (same as record)

Key behaviors:
1. Uses WAV mtime as timestamp for deterministic output filenames
2. Overwrite detection: predicts output filenames using _build_filename() before writing; prompts per-format
3. Passes delete_wav=False — user's WAV is never deleted
4. Config resolution same pattern as record_command

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functions are fully wired and tested.

## Self-Check: PASSED

Files exist:
- src/mote/cli.py — FOUND
- tests/test_cli.py — FOUND

Commits exist:
- 0dfc21a — FOUND
- 692c305 — FOUND
- 6f9c96e — FOUND
- 67ae3dc — FOUND
