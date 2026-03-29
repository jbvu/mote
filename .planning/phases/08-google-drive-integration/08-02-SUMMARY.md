---
phase: 08-google-drive-integration
plan: "02"
subsystem: cli
tags: [cli, google-drive, oauth2, destinations, upload]
dependency_graph:
  requires: [08-01]
  provides: [auth-google-command, upload-command, destination-flag, drive-wiring]
  affects: [src/mote/cli.py, tests/test_cli.py]
tech_stack:
  added: []
  patterns:
    - lazy-import (Google libraries imported inside auth/upload function bodies)
    - failure-as-warning (Drive upload failures caught, printed as warnings, not hard errors)
    - destination-override (--destination flag overrides config active destinations per run)
key_files:
  created: []
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
decisions:
  - "Drive upload placed before wav deletion in _run_transcription — local files always written first (D-05)"
  - "Drive upload failures caught as Exception (not RuntimeError only) so all failure modes produce warning, never crash"
  - "upload_command imports upload_transcripts lazily inside function body — consistent with Phase 4/08-01 pattern"
  - "auth_google uses lazy import for googleapiclient.discovery so startup cost is zero when Drive not used"
metrics:
  duration: "5 minutes"
  completed: "2026-03-29"
  tasks_completed: 1
  files_modified: 2
---

# Phase 8 Plan 2: CLI Drive Integration Summary

Drive-wired CLI: `mote auth google` OAuth flow, `mote upload` manual upload command, `--destination` override flag on record/transcribe, auto-upload in `_run_transcription` with failure-as-warning per D-09.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for auth/upload/destination/Drive wiring | 58e56d9 | tests/test_cli.py |
| 1 (GREEN) | Implement auth group, upload command, --destination flag, Drive wiring | 3354e9e | src/mote/cli.py |

## What Was Built

### src/mote/cli.py

**auth command group** — new `@cli.group()` with `google` subcommand:
- First-time flow: `get_credentials` returns None → calls `run_auth_flow` → prints success message
- Re-auth flow: existing creds → shows status (email + token path) → `click.confirm` for re-auth
- Email display uses lazy `googleapiclient.discovery` build for `oauth2 v2` userinfo; falls back to "authenticated (email unavailable)" on any exception

**upload command** — top-level `mote upload`:
- Accepts optional `FILE` path argument or `--last` flag
- `--last` uses `list_transcripts` to find newest transcript, then collects all files sharing the same stem
- Calls `upload_transcripts(config_dir, files, folder_name)` with lazy import
- `RuntimeError` (not authenticated) → `ClickException` with auth hint
- Other exceptions → `ClickException` with "Upload failed:" prefix

**--destination flag** — added to both `record_command` and `transcribe_command`:
- `multiple=True` so multiple destinations can be specified: `--destination local --destination drive`
- Resolves: `destinations_override` if provided; else `cfg["destinations"]["active"]` (defaults to `["local"]`)
- Passed through to `_run_transcription` along with `config_dir` and `cfg`

**_run_transcription extended** — three new keyword params: `destinations`, `config_dir`, `cfg`:
- After `write_transcript` succeeds, checks if `"drive"` in `active_destinations`
- If yes: lazy-imports `upload_transcripts`, calls it; on any `Exception` prints warning and continues
- Warning format: `"Warning: Drive upload failed: {e}. Transcripts saved locally. Run 'mote upload' to retry."`
- `delete_wav` still runs after Drive upload attempt (local file preserved regardless)

### tests/test_cli.py

15 new tests covering all new CLI behaviours:
- `test_auth_google_first_time` — no token → run_auth_flow called
- `test_auth_google_already_authed_decline` — existing creds, decline → run_auth_flow NOT called
- `test_auth_google_already_authed_accept` — existing creds, accept → run_auth_flow called
- `test_upload_command_with_file` — file arg → upload_transcripts called, "Uploaded" in output
- `test_upload_command_not_authed` — RuntimeError → exit non-zero with auth hint
- `test_upload_command_no_args` — no file or --last → exit non-zero
- `test_destination_flag_drive_triggers_upload` — `--destination drive` → upload_transcripts called
- `test_destination_local_only_no_upload` — `--destination local` overrides drive-active config → no upload
- `test_drive_upload_failure_is_warning` — upload exception → warning in output, exit 0
- `test_drive_upload_no_upload_without_drive_destination` — destinations=["local"] → upload not called
- `test_transcribe_destination_flag_drive` — transcribe `--destination drive` → upload called
- `test_record_help_shows_destination_flag` / `test_transcribe_help_shows_destination_flag`
- `test_auth_group_help` / `test_upload_command_help`

## Test Results

- `tests/test_cli.py`: 93 tests pass (15 new, 78 existing — no regressions)
- `tests/test_drive.py` + `tests/test_config.py`: 53 tests pass
- Full suite: 204 passing, 1 pre-existing failure (`test_models.py::test_download_model_passes_tqdm_class` — unrelated, deferred in 08-01)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all new commands call through to `mote.drive` functions which are fully implemented. The `CLIENT_CONFIG` placeholder values in `src/mote/drive.py` are a pre-existing known stub documented in 08-01-SUMMARY.md.

## Self-Check

### Created files exist
- tests/test_cli.py (modified): FOUND
- src/mote/cli.py (modified): FOUND

### Commits exist
- 58e56d9 (RED test(08-02)): FOUND
- 3354e9e (feat(08-02)): FOUND

## Self-Check: PASSED
