---
phase: 09-notebooklm-integration
plan: 02
subsystem: cli
tags: [notebooklm, cli, auth, destination, tdd]
dependency_graph:
  requires: [src/mote/notebooklm.py, src/mote/cli.py]
  provides: [auth notebooklm command, NotebookLM upload in _run_transcription, --destination notebooklm]
  affects: [src/mote/cli.py, tests/test_cli.py]
tech_stack:
  added: []
  patterns: [lazy import in _run_transcription, try/except warning pattern, shutil.which + subprocess.run for Playwright check]
key_files:
  created: []
  modified:
    - src/mote/cli.py
    - tests/test_cli.py
decisions:
  - "auth notebooklm uses shutil.which + subprocess.run(['playwright','install','--check','chromium']) for binary check — fails fast with clear install hint before invoking run_login"
  - "NotebookLM upload block placed after Drive block in _run_transcription, before delete_wav — follows exact Drive warning pattern"
metrics:
  duration: 420s
  completed: "2026-03-30T00:00:00Z"
  tasks_completed: 2
  files_changed: 2
---

# Phase 9 Plan 02: CLI NotebookLM Integration Summary

NotebookLM wired into CLI: auth notebooklm command with Playwright Chromium pre-check, upload block in _run_transcription following Drive warning pattern, --destination notebooklm added to record and transcribe commands.

## What Was Built

### src/mote/cli.py

Three changes:

**1. `auth notebooklm` command** — New subcommand under the existing `auth` group (alongside `auth google`). Checks for Playwright binary via `shutil.which`, then runs `playwright install --check chromium` to verify the Chromium browser is installed. Fails fast with clear install hints if either is absent. Calls `run_login(session_path)` on success. Shows session file path if already authenticated and offers re-auth.

**2. NotebookLM upload block in `_run_transcription`** — Placed after the Drive upload block, before `delete_wav`. Guards with `if "notebooklm" in active_destinations`. Lazy-imports `upload_transcript` from `mote.notebooklm`. Reads `notebook_name` from `cfg["destinations"]["notebooklm"]["notebook_name"]` (defaults to "Mote Transcripts"). All exceptions caught as warnings with "Run 'mote auth notebooklm' if session expired." message.

**3. `--destination Choice` extended** — Both `record_command` and `transcribe_command` now accept `"notebooklm"` as a valid `--destination` choice alongside `"local"` and `"drive"`.

### tests/test_cli.py

8 new tests in `# NotebookLM integration tests` section:

- `test_auth_notebooklm_new_session` — run_login called when no session, success output
- `test_auth_notebooklm_already_authenticated` — shows path, run_login not called on decline
- `test_auth_notebooklm_login_failure` — ClickException raised on RuntimeError
- `test_auth_notebooklm_no_playwright` — Abort with "Playwright not found" hint
- `test_auth_notebooklm_no_chromium` — Abort with "Playwright Chromium browser not found" hint
- `test_run_transcription_notebooklm_destination` — upload_transcript called with correct args
- `test_run_transcription_notebooklm_failure_is_warning` — exception → warning, no exit_code != 0
- `test_destination_choice_includes_notebooklm` — record and transcribe --help show "notebooklm"

## Test Results

```
tests/test_cli.py -k notebooklm — 8 passed
Full suite (excluding pre-existing test_models.py failure) — 254 passed
```

Pre-existing failure: `tests/test_models.py::test_download_model_passes_tqdm_class` — asserts `rich_tqdm` class but module uses `_SafeRichTqdm` wrapper. Pre-existed before this plan.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Commits

- `057240d` — feat(09-02): add auth notebooklm command, NotebookLM upload in _run_transcription, --destination notebooklm
- `58ab832` — test(09-02): add NotebookLM integration tests for CLI

## Self-Check: PASSED

- FOUND: src/mote/cli.py contains `@auth.command("notebooklm")`
- FOUND: src/mote/cli.py contains `def auth_notebooklm():`
- FOUND: src/mote/cli.py contains `from mote.notebooklm import get_session_path, is_authenticated, run_login`
- FOUND: src/mote/cli.py contains `from mote.notebooklm import upload_transcript`
- FOUND: src/mote/cli.py contains `if "notebooklm" in active_destinations:`
- FOUND: src/mote/cli.py contains `"Run 'mote auth notebooklm' if session expired."`
- FOUND: src/mote/cli.py contains `notebook_name` reading from config
- FOUND: src/mote/cli.py contains Playwright Chromium check
- FOUND: src/mote/cli.py contains `"playwright install chromium"` hint message
- FOUND: record_command and transcribe_command --destination Choice includes "notebooklm"
- FOUND: commit 057240d
- FOUND: commit 58ab832
- All 8 notebooklm tests pass
