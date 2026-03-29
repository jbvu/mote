---
phase: 09-notebooklm-integration
plan: 01
subsystem: notebooklm
tags: [notebooklm, async, session-management, config, tdd]
dependency_graph:
  requires: [src/mote/drive.py, src/mote/config.py, pyproject.toml]
  provides: [src/mote/notebooklm.py, notebooklm config extension]
  affects: [src/mote/config.py, pyproject.toml, tests/test_config.py]
tech_stack:
  added: [notebooklm-py[browser]>=0.3.4 (optional dependency)]
  patterns: [function-based module, lazy imports, asyncio.run bridge, session file with chmod 0o600, notebook ID caching]
key_files:
  created:
    - src/mote/notebooklm.py
    - tests/test_notebooklm.py
  modified:
    - src/mote/config.py
    - pyproject.toml
    - tests/test_config.py
decisions:
  - "notebooklm-py import is lazy (inside _upload_async function body) — follows Phase 4 pattern for optional heavy deps"
  - "asyncio.run() used as sync-to-async bridge in upload_transcript — safe in Click CLI context with no running event loop"
  - "notebook_id cached in same session JSON file alongside Playwright cookies — mirrors drive.py folder_id caching in google_token.json"
  - "Retry on add_text failure: invalidate cache, call _get_or_create_notebook fresh, re-save, retry — handles stale notebook ID after manual deletion"
metrics:
  duration: 184s
  completed: "2026-03-29T22:18:29Z"
  tasks_completed: 2
  files_changed: 5
---

# Phase 9 Plan 01: NotebookLM Module Summary

NotebookLM async API wrapper with session management, notebook ID caching, upload filtering (md-only), and retry-on-stale-ID logic, plus config extension and optional pyproject.toml dependency.

## What Was Built

### src/mote/notebooklm.py

New module following the `drive.py` pattern exactly. All functions:

- `get_session_path(config_dir)` — returns `config_dir / "notebooklm_session.json"`
- `is_authenticated(config_dir)` — returns True if session file exists
- `run_login(session_path)` — subprocess `notebooklm login --storage <path>`, raises RuntimeError on failure, chmod 0o600 on success
- `_load_notebook_id(session_path)` — reads notebook_id from session JSON, returns None if absent/invalid
- `_save_notebook_id(session_path, notebook_id)` — embeds notebook_id in existing session JSON, chmod 0o600
- `_get_or_create_notebook(client, notebook_name)` — async; lists notebooks by title, creates if not found
- `_upload_async(session_path, notebook_name, title, content)` — async; lazy-imports NotebookLMClient, uses cached notebook_id, retries on add_text failure
- `upload_transcript(config_dir, files, notebook_name)` — sync entry point; filters to .md only, calls asyncio.run per file

### src/mote/config.py

Extended `_write_default_config()` with `[destinations.notebooklm]` subsection and updated active-destinations comment to mention `notebooklm`.

### pyproject.toml

Added `notebooklm` optional dependency group with `notebooklm-py[browser]>=0.3.4`. Not in main dependencies — experimental/optional.

### tests/test_notebooklm.py (new, 21 tests)

Covers: session path, authentication checks, run_login success/failure, _load_notebook_id variants, _save_notebook_id, upload filtering (md-only, no-md, empty list), asyncio.run call verification, _get_or_create_notebook (existing/create paths), _upload_async retry on stale notebook ID.

### tests/test_config.py

Added `test_default_config_has_notebooklm_section` verifying [destinations.notebooklm] with notebook_name = "Mote Transcripts".

## Test Results

```
tests/test_notebooklm.py — 21 passed
tests/test_config.py — 30 passed (including new notebooklm test)
Total: 51 passed
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functions are fully implemented. The `notebooklm-py` library is an optional dependency that requires `pip install "mote[notebooklm]"` and `playwright install chromium` (documented Playwright requirement). The upload function will raise RuntimeError at runtime if not authenticated, caught as a warning by Plan 02's cli.py integration.

## Commits

- `a390d15` — feat(09-01): create notebooklm.py module, extend config, update pyproject.toml
- `4baa123` — test(09-01): add test_default_config_has_notebooklm_section to test_config.py

## Deferred Items

- Pre-existing test failure: `tests/test_models.py::test_download_model_passes_tqdm_class` — asserts `rich_tqdm` class but module uses `_SafeRichTqdm` wrapper. Pre-existed before this plan. Out of scope.

## Self-Check: PASSED

- FOUND: src/mote/notebooklm.py
- FOUND: tests/test_notebooklm.py
- FOUND: commit a390d15
- FOUND: commit 4baa123
- All acceptance criteria met
