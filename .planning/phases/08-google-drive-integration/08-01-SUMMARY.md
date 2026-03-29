---
phase: 08-google-drive-integration
plan: "01"
subsystem: drive
tags: [google-drive, oauth2, config, destinations]
dependency_graph:
  requires: []
  provides: [drive.py, destinations-config]
  affects: [config.py, pyproject.toml]
tech_stack:
  added:
    - google-api-python-client>=2.193.0
    - google-auth-oauthlib>=1.3.0
    - google-auth>=2.38.0
  patterns:
    - lazy-import (Google libraries imported inside function bodies per Phase 4 pattern)
    - token-file-caching (folder_id stored alongside OAuth credentials in google_token.json)
    - tdd (RED/GREEN cycle per plan spec)
key_files:
  created:
    - src/mote/drive.py
    - tests/test_drive.py
  modified:
    - src/mote/config.py
    - pyproject.toml
    - tests/test_config.py
decisions:
  - "Lazy imports for all Google libraries inside function bodies — follows Phase 4 pattern to avoid startup cost and missing-dep errors"
  - "CLIENT_CONFIG embedded in drive.py with placeholder values — standard for open-source installed-app OAuth"
  - "Folder ID cached inside google_token.json alongside OAuth credentials — same lifecycle, avoids polluting config.toml"
  - "drive.file scope only — app can only see folders/files it created; folder search works correctly with cached folder_id"
metrics:
  duration: "4 minutes"
  completed: "2026-03-29"
  tasks_completed: 2
  files_modified: 5
---

# Phase 8 Plan 1: Google Drive Module Summary

Google Drive API wrapper (drive.py) with OAuth2 auth, folder management, and file upload; [destinations] config section with drive subsection; 3-part dotted key support in set_config_value.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create drive.py module and tests/test_drive.py | 9986e5f | src/mote/drive.py, tests/test_drive.py, pyproject.toml |
| 2 | Extend config.py with [destinations] section | 43563ff | src/mote/config.py, tests/test_config.py |

## What Was Built

### src/mote/drive.py

New module with 9 public/private functions:

- `get_token_path(config_dir)` — returns `~/.mote/google_token.json`
- `get_credentials(token_path)` — loads and optionally refreshes OAuth credentials
- `run_auth_flow(token_path)` — browser OAuth2 consent via `InstalledAppFlow.run_local_server(port=0, access_type="offline", prompt="consent")`
- `build_service(creds)` — builds Drive v3 service via `googleapiclient.discovery.build`
- `get_or_create_folder(service, folder_name)` — searches for app-created folder; creates if absent
- `upload_file(service, local_path, folder_id)` — uploads single file with correct MIME type
- `upload_transcripts(config_dir, files, folder_name)` — orchestrates full upload flow; raises RuntimeError if not authenticated
- `_save_token(token_path, creds, folder_id)` — writes credentials JSON with optional folder_id; chmod 600
- `_load_folder_id(token_path)` — reads cached folder_id from token file

All Google imports are lazy (inside function bodies), following the Phase 4 pattern.

### src/mote/config.py

Extended `_write_default_config` to include:
```toml
[destinations]
# Active destinations: local, drive
active = ["local"]

[destinations.drive]
# Google Drive folder name for uploads
folder_name = "Mote Transcripts"
```

Extended `set_config_value` to handle 3-part dotted keys (e.g., `destinations.drive.folder_name`) with proper KeyError for unknown sections, subsections, and keys.

### pyproject.toml

Added three Google API dependencies to core `dependencies` list:
- `google-api-python-client>=2.193.0`
- `google-auth-oauthlib>=1.3.0`
- `google-auth>=2.38.0`

## Test Results

- `tests/test_drive.py`: 24 tests pass (469 lines)
- `tests/test_config.py`: 29 tests pass (added 6 new tests for destinations config)
- Full suite: 209 passing tests, no regressions from plan changes
- Pre-existing failure: `test_models.py::test_download_model_passes_tqdm_class` — unrelated to this plan, deferred

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

`CLIENT_CONFIG` in `src/mote/drive.py` contains placeholder `client_id` and `client_secret` values. This is intentional per D-01: the real Google Cloud project credentials are provided by the maintainer when they create their Cloud Console Desktop app project. The placeholder values prevent the auth flow from working but do not block Plan 02 (CLI wiring) which mocks all Drive calls in tests.

## Self-Check

### Created files exist
- src/mote/drive.py: FOUND
- tests/test_drive.py: FOUND
- tests/test_config.py (modified): FOUND

### Commits exist
- 27836e6 (RED test(08-01): drive tests): FOUND
- 9986e5f (feat(08-01): drive.py): FOUND
- 59acd7c (RED test(08-01): config tests): FOUND
- 43563ff (feat(08-01): config.py): FOUND

## Self-Check: PASSED
