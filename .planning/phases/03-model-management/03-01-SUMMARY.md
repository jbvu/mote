---
phase: 03-model-management
plan: 01
subsystem: models
tags: [huggingface_hub, faster-whisper, kblab, rich, tqdm, click, kb-whisper]

requires:
  - phase: 01-foundation
    provides: CLI entry point (cli group), config system (load_config, set_config_value)
  - phase: 02-audio-capture
    provides: Established CLI command group pattern and mote.cli.* patch target convention

provides:
  - "src/mote/models.py: MODELS dict, APPROX_SIZES, ALLOW_PATTERNS, is_model_downloaded, get_downloaded_models, get_models_status, download_model, cleanup_partial_download, delete_model, require_model_downloaded, config_value_to_alias"
  - "src/mote/cli.py: models command group with list, download, delete subcommands"
  - "tests/test_models.py: 49 unit tests for all model management functions and CLI commands"

affects:
  - phase 04-transcription (require_model_downloaded guard, MODELS/ALLOW_PATTERNS constants, config_value_to_alias)
  - phase 05-webui (models list data shape for web model management page)

tech-stack:
  added: []
  patterns:
    - "huggingface_hub cache API: try_to_load_from_cache for fast download check, scan_cache_dir for size/list, delete_revisions().execute() for safe deletion"
    - "snapshot_download with tqdm_class=rich_tqdm for Rich-styled download progress"
    - "ALLOW_PATTERNS mirrors faster-whisper's internal list to ensure downloaded files are immediately usable by WhisperModel"
    - "config_value_to_alias() bridges kb-whisper-{size} config format to CLI alias"
    - "Patch target for CLI mocks is mote.cli.* not mote.models.* (established in Phase 2, continued here)"

key-files:
  created:
    - src/mote/models.py
    - tests/test_models.py
  modified:
    - src/mote/cli.py
    - tests/test_cli.py

key-decisions:
  - "Use try_to_load_from_cache (not WhisperModel) for download check — avoids loading GB into RAM"
  - "Use delete_revisions().execute() for delete (not shutil.rmtree) — HF cache consistency, blob deduplication"
  - "ALLOW_PATTERNS must exactly mirror faster-whisper's list or WhisperModel will silently re-download"
  - "CacheNotFound constructor requires (msg, cache_dir) — discovered during test RED phase"
  - "All 5 KB-Whisper repo IDs confirmed as KBLab/kb-whisper-{tiny,base,small,medium,large}; no Stage 2 variants exist as of 2026-03-28"

patterns-established:
  - "Pattern: Model alias (tiny/base/small/medium/large) vs config value (kb-whisper-{size}) — use config_value_to_alias() to bridge"
  - "Pattern: Wrap scan_cache_dir() calls in try/except CacheNotFound — raises on fresh machines with no HF cache"

requirements-completed: [MOD-01, MOD-02, MOD-03, MOD-04, CLI-02]

duration: 4min
completed: 2026-03-28
---

# Phase 3 Plan 1: Model Management Summary

**KB-Whisper model management via huggingface_hub APIs: list/download/delete with Rich table and progress bar, Ctrl+C cleanup, and require_model_downloaded guard for Phase 4 transcription**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T14:54:37Z
- **Completed:** 2026-03-28T14:58:55Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `mote models list` renders Rich table with all 5 KB-Whisper models showing approx/actual size and marking the active model
- `mote models download <name>` prompts for size confirmation, downloads with Rich progress bar via tqdm_class, skips existing unless --force, handles Ctrl+C with partial cleanup
- `mote models delete <name>` removes from HF cache via delete_revisions().execute(), warns on active model, reports freed bytes
- `require_model_downloaded()` guard ready for Phase 4 — raises ClickException with `mote models download <alias>` instructions
- 49 unit tests total (36 model logic + 13 CLI integration), all mocked — no network, no real HF cache

## Task Commits

1. **Task 1: Model management module with tests** - `4f35aad` (feat + test)
2. **Task 2: CLI commands for models group** - `107a7a8` (feat + test)

## Files Created/Modified

- `src/mote/models.py` - Model management logic: constants, cache inspection, download, delete, guard
- `tests/test_models.py` - 49 unit tests covering all functions and CLI commands
- `src/mote/cli.py` - Added models command group (list/download/delete) and _human_size helper
- `tests/test_cli.py` - Added test_models_group_help smoke test

## Decisions Made

- Used `try_to_load_from_cache` (not `scan_cache_dir` or `WhisperModel`) for `is_model_downloaded` — fast single-file check with no RAM load
- Used `delete_revisions(*all_hashes).execute()` for delete to respect HF's blob deduplication logic
- ALLOW_PATTERNS mirrors `faster_whisper.utils.download_model` exactly — mismatched patterns would cause silent re-download at transcription time
- Ctrl+C cleanup uses `shutil.rmtree` on the entire model cache dir (D-08) — removes .incomplete blobs so next download starts fresh

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CacheNotFound constructor requires two positional args**
- **Found during:** Task 1 (test RED phase for get_downloaded_models)
- **Issue:** `CacheNotFound("no cache dir")` raised TypeError — constructor signature is `(msg, cache_dir)` in huggingface_hub 1.8.0
- **Fix:** Updated test mocks to pass `CacheNotFound("no cache dir", cache_dir="/fake")`
- **Files modified:** tests/test_models.py
- **Verification:** Tests passed after fix
- **Committed in:** 4f35aad (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test setup)
**Impact on plan:** Minor test correctness fix. No behavior or scope change.

## Issues Encountered

- pytest not installed in venv (only in dev optional-dependencies but uv sync --dev didn't install it). Fixed by running `uv pip install pytest` directly. This is a pre-existing setup issue unrelated to this plan.

## Known Stubs

None — all model management functions are fully implemented with real huggingface_hub API calls. No hardcoded empty values or placeholders.

## User Setup Required

None — no external service configuration required. huggingface_hub is a transitive dependency of faster-whisper; no new packages added to pyproject.toml.

## Next Phase Readiness

- Phase 4 (transcription) can import `require_model_downloaded` from `mote.models` and call it before loading `WhisperModel` — the guard raises ClickException with clear download instructions
- `config_value_to_alias()` available for Phase 4 to convert config `transcription.model` value to alias for MODELS lookup
- `MODELS` dict and `ALLOW_PATTERNS` available for Phase 4 WhisperModel initialization

---
## Self-Check: PASSED

- FOUND: src/mote/models.py
- FOUND: tests/test_models.py
- FOUND: .planning/phases/03-model-management/03-01-SUMMARY.md
- FOUND: commit 4f35aad (Task 1 — model management module)
- FOUND: commit 107a7a8 (Task 2 — CLI commands)

*Phase: 03-model-management*
*Completed: 2026-03-28*
