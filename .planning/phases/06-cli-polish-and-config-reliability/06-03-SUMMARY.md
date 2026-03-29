---
phase: 06-cli-polish-and-config-reliability
plan: 03
subsystem: cli
tags: [config-validation, retry-loop, orphan-warning, auto-cleanup, tdd]
dependency_graph:
  requires: [06-01-validate_config, 06-02-transcribe-command]
  provides: [retry-loop, validation-wiring, config-validate-command, cleanup-command]
  affects: []
tech_stack:
  added: []
  patterns: [tdd-red-green, while-true-retry, validate-before-blackhole]
key_files:
  created: []
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
key_decisions:
  - validate_config() called before BlackHole detection in record_command so bad config exits cleanly without wasting time on device detection
  - validate_config() called at top of transcribe_command before any other work
  - retry loop uses while True with explicit except click.ClickException re-raise before generic except Exception to avoid retrying on ClickException subclasses
  - auto-cleanup runs silently (no output) at record startup; only mote cleanup command prints deleted file details
  - mote config validate is @config.command("validate") subcommand (not @cli.command) per D-05 and existing config group pattern
  - mote cleanup is @cli.command("cleanup") top-level command (not under config group) per D-15
metrics:
  duration_seconds: 447
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_modified: 2
---

# Phase 6 Plan 3: CLI Wiring and Commands Summary

Retry loop on transcription failure, validate_config() wired into record/transcribe startup, auto-cleanup at record startup, orphan warning enhanced with mote transcribe pointer, mote config validate subcommand, and mote cleanup top-level command — all with full TDD coverage.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for retry, validation, orphan, auto-cleanup | 69dc07f | tests/test_cli.py |
| 1 (GREEN) | Wire validation, retry loop, auto-cleanup, orphan enhancement | d020f35 | src/mote/cli.py, tests/test_cli.py |
| 2 (RED) | Failing tests for config validate and cleanup commands | 25dddc4 | tests/test_cli.py |
| 2 (GREEN) | Add mote config validate and mote cleanup commands | 1ff5a6b | src/mote/cli.py |

## Verification

```
52 passed in 0.86s (tests/test_cli.py)
189 passed, 1 pre-existing failure (tests/test_models.py::test_download_model_passes_tqdm_class — unrelated)
```

Phase 6 full suite: 99 passed in 1.09s (tests/test_cli.py + tests/test_config.py + tests/test_output.py)

## What Was Built

### Retry Loop in record_command and transcribe_command

Both `record_command` and `transcribe_command` now wrap `_run_transcription()` in a `while True:` retry loop per D-01:

```python
while True:
    try:
        _run_transcription(...)
        break
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"Transcription failed: {e}")
        click.echo(f"WAV kept at: {wav_path}")
        if not click.confirm("Retry transcription?", default=True):
            raise click.ClickException(f"Transcription failed. WAV kept at: {wav_path}")
```

`click.ClickException` is re-raised immediately (before generic `except Exception`) per Pitfall 2 from the research — avoids re-prompting on Click's own user-facing errors.

### validate_config() Wiring in record_command

Config validation now runs before BlackHole detection. `cfg = load_config()` was moved up from after the `if no_transcribe: return` guard to before validation. The `cfg` variable is then reused for engine/language resolution after recording completes — eliminating the duplicate `load_config()` call.

### validate_config() Wiring in transcribe_command

Validation runs at the very top of `transcribe_command`, before any other work including config resolution and overwrite detection.

### Auto-cleanup at record_command Startup

After validation, before the orphan check:
```python
retention_days = cfg.get("cleanup", {}).get("wav_retention_days", 7)
if retention_days > 0:
    cleanup_old_wavs(recordings_dir, retention_days)
```

Runs silently — no output unless a file is detected (not exposed to the user at startup, per D-14).

### Orphan Warning Enhancement

Added `click.echo("Transcribe them with: mote transcribe <file>")` in the orphan warning block, replacing the empty `click.echo()` call that was there before. Users now see exactly which command to run.

### mote config validate Subcommand

```python
@config.command("validate")
def config_validate():
    """Run pre-flight configuration checks."""
    cfg = load_config()
    errors, warnings = validate_config(cfg)
    # prints warnings with Warning: prefix
    # prints errors with Error: prefix
    # raises ClickException on errors (exit non-zero)
    # prints Configuration OK on success
```

Exits 0 with "Configuration OK" when clean, or "Configuration OK (N warning(s))." when warnings only. Exits non-zero on errors.

### mote cleanup Command

```python
@cli.command("cleanup")
def cleanup_command():
    """Delete expired WAV recordings older than retention period."""
```

Reads `wav_retention_days` from config (default: 7). Prints "WAV retention disabled" when 0. Reports "Deleted N expired WAV file(s):" with filenames, or "No expired WAV files found." when nothing to delete.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing tests broken by new validate_config() wiring**
- **Found during:** Task 1 GREEN
- **Issue:** All existing record/transcribe tests failed after adding validate_config() because the default test config has engine=local with no model downloaded — validation correctly exits before BlackHole detection
- **Fix:** Added `patch("mote.cli.validate_config", return_value=([], []))` to all existing tests that test behavior unrelated to validation. Also added `input="n\n"` to tests that now hit the retry prompt before the mock failure
- **Files modified:** tests/test_cli.py (18 tests updated)
- **Commit:** d020f35

## Known Stubs

None — all functions are fully wired and tested.

## Self-Check: PASSED

Files exist:
- src/mote/cli.py — FOUND
- tests/test_cli.py — FOUND

Commits exist:
- 69dc07f — FOUND
- d020f35 — FOUND
- 25dddc4 — FOUND
- 1ff5a6b — FOUND
