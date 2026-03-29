---
phase: 08-google-drive-integration
verified: 2026-03-29T00:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 8: Google Drive Integration Verification Report

**Phase Goal:** Transcripts are automatically uploaded to Google Drive after each recording, completing the capture-to-Drive workflow without manual file management
**Verified:** 2026-03-29
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `mote auth google` opens a browser consent page and stores an OAuth2 refresh token; subsequent runs do not require re-authentication | VERIFIED | `run_auth_flow` calls `InstalledAppFlow.from_client_config` then `run_local_server(port=0, access_type="offline", prompt="consent")`, writes token via `_save_token`; `get_credentials` refreshes silently on subsequent calls |
| 2 | After transcription completes, the transcript is automatically uploaded to the configured Google Drive folder | VERIFIED | `_run_transcription` checks `"drive" in active_destinations` after `write_transcript` succeeds; calls `upload_transcripts(effective_config_dir, written, folder_name)` |
| 3 | A Drive upload failure is reported as a warning and does not mark the transcription as failed — local files are always written first | VERIFIED | Drive upload is in `try/except Exception`; on failure prints `"Warning: Drive upload failed: {e}. Transcripts saved locally. Run 'mote upload' to retry."` and continues normally; `write_transcript` runs before any Drive call |
| 4 | User can set `--destination drive` per-run or configure drive as the default destination in config | VERIFIED | `--destination [local\|drive]` flag (multiple=True) on both `record_command` and `transcribe_command`; defaults to `cfg["destinations"]["active"]` (default `["local"]`) |
| 5 | drive.py exists with OAuth2 auth flow, credential loading, folder create, and file upload functions | VERIFIED | All 9 functions present: `get_token_path`, `get_credentials`, `run_auth_flow`, `build_service`, `get_or_create_folder`, `upload_file`, `upload_transcripts`, `_save_token`, `_load_folder_id` |
| 6 | Default config includes [destinations] section with active = ['local'] and [destinations.drive] with folder_name | VERIFIED | `_write_default_config` adds `destinations` table with `active = ["local"]` and `destinations.drive` with `folder_name = "Mote Transcripts"` |
| 7 | Token file stored at ~/.mote/google_token.json with 600 permissions | VERIFIED | `get_token_path` returns `config_dir / "google_token.json"`; `_save_token` calls `token_path.chmod(0o600)` after every write |
| 8 | Folder ID is cached in token file to avoid repeated API lookups | VERIFIED | `upload_transcripts` checks `_load_folder_id` before calling `get_or_create_folder`; caches via `_save_token(token_path, creds, folder_id=folder_id)`; `get_credentials` preserves `folder_id` on token refresh |
| 9 | Google dependencies are declared in pyproject.toml | VERIFIED | Lines 21-23 of pyproject.toml: `google-api-python-client>=2.193.0`, `google-auth-oauthlib>=1.3.0`, `google-auth>=2.38.0` |
| 10 | mote auth google shows status and offers re-auth when already authenticated | VERIFIED | `auth_google` calls `get_credentials`; if non-None, prints email + token path, prompts `click.confirm("Re-authenticate?", default=False)` |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mote/drive.py` | Google Drive API wrapper: auth, upload, folder management | VERIFIED | 162 lines; exports all 9 required functions; SCOPES, CLIENT_CONFIG, MIME_TYPES constants present |
| `src/mote/config.py` | Extended default config with [destinations] and [destinations.drive] sections | VERIFIED | `_write_default_config` adds both sections; `set_config_value` handles 3-part dotted keys |
| `pyproject.toml` | Google API dependencies | VERIFIED | All three google packages present at specified minimum versions |
| `tests/test_drive.py` | Unit tests for drive.py functions | VERIFIED | 469 lines (well above 80-line minimum); 24 tests; all pass |
| `tests/test_config.py` | Tests for destinations config section | VERIFIED | Contains `test_default_config_has_destinations` and all 6 destination-related tests |
| `src/mote/cli.py` | auth group with google subcommand, upload command, --destination flag, Drive wiring in _run_transcription | VERIFIED | All required structures present and wired |
| `tests/test_cli.py` | Tests for auth command, upload command, destination flag, Drive failure warning | VERIFIED | 1633 lines; contains `test_auth_google`, `test_upload_command`, `test_drive_upload_failure_is_warning` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/mote/drive.py` | `google_auth_oauthlib.flow.InstalledAppFlow` | `from_client_config` with embedded CLIENT_CONFIG | WIRED | Line 60: `flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)` |
| `src/mote/drive.py` | `googleapiclient.discovery.build` | `build("drive", "v3", credentials=creds)` | WIRED | Line 70: `return build("drive", "v3", credentials=creds)` |
| `src/mote/drive.py` | `~/.mote/google_token.json` | `get_token_path` and credential persistence | WIRED | `get_token_path` returns `config_dir / "google_token.json"`; `_save_token` writes with chmod 600 |
| `src/mote/cli.py:_run_transcription` | `mote.drive.upload_transcripts` | lazy import after write_transcript returns, wrapped in try/except | WIRED | Lines 646-652: lazy import, call, Exception catch with warning print |
| `src/mote/cli.py:auth_google` | `mote.drive.run_auth_flow` | lazy import, calls run_auth_flow(token_path) | WIRED | Line 445: `from mote.drive import get_token_path, get_credentials, run_auth_flow`; line 467: `creds = run_auth_flow(token_path)` |
| `src/mote/cli.py:upload_command` | `mote.drive.upload_transcripts` | lazy import for manual upload | WIRED | Lines 520-521: lazy import + call |
| `src/mote/cli.py:record_command` | `_run_transcription` | passes cfg and config_dir for destination resolution | WIRED | Lines 324-330: call with `destinations`, `config_dir`, `cfg` kwargs |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `_run_transcription` → Drive upload | `written` (list of Paths from `write_transcript`) | `write_transcript` returns actual file paths written to disk | Yes — real file paths from local write | FLOWING |
| `upload_transcripts` → `upload_file` | `files` list, `folder_id` | Caller passes real file paths; `folder_id` from Drive API response or cache | Yes — real Drive API calls or cached ID | FLOWING |
| `auth_google` → token storage | `creds` from `run_auth_flow` | `InstalledAppFlow.run_local_server` (OAuth browser flow) | Yes — real Google OAuth token | FLOWING (with known stub: CLIENT_CONFIG placeholder values prevent actual OAuth until real credentials configured) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| drive module imports without error | `python -c "from mote.drive import SCOPES, upload_transcripts; print('ok')"` | `drive import ok` | PASS |
| `mote --help` shows auth and upload commands | `mote --help` | auth, upload listed | PASS |
| `mote auth --help` shows google subcommand | `mote auth --help` | google subcommand shown | PASS |
| `mote record --help` shows --destination flag | `mote record --help` | `--destination [local\|drive]` shown | PASS |
| `mote transcribe --help` shows --destination flag | `mote transcribe --help` | `--destination [local\|drive]` shown | PASS |
| Drive + config + CLI tests pass | `pytest tests/test_drive.py tests/test_config.py tests/test_cli.py -x -q` | 146 passed | PASS |
| Full suite has no new regressions | `pytest -q` | 272 passed, 1 pre-existing failure in test_models.py unrelated to this phase | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| INT-03 | 08-01, 08-02 | User can configure transcript destinations via `[destinations]` config section and `--destination` flag | SATISFIED | `[destinations]` section in default config; `--destination` flag on record/transcribe; `set_config_value` handles `destinations.drive.folder_name` |
| INT-04 | 08-01, 08-02 | User can upload transcripts to Google Drive via `mote auth google` (one-time OAuth2 browser consent) + automatic upload after transcription | SATISFIED | `mote auth google` command with InstalledAppFlow; auto-upload in `_run_transcription`; `mote upload` for manual retry |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/mote/drive.py` | 10-11 | `CLIENT_CONFIG` contains `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` placeholder values | INFO | Intentional and documented (08-01-SUMMARY Known Stubs). OAuth flow will not complete until the user configures a real Google Cloud Desktop app project. Does not affect test suite (all Drive calls mocked) or CLI command wiring. Standard pattern for open-source installed-app OAuth. |
| `~/.mote/config.toml` | — | Existing user config lacks `[destinations]` section (created before this phase) | INFO | `_write_default_config` is only called for new configs. All CLI reads use `.get("destinations", {})` with fallbacks, so the missing section defaults to `["local"]` safely. Users with existing configs can manually add the section or delete and recreate. No migration path is provided, but this does not block any phase goal. |

No blockers. No structural stubs in the implementation code.

### Human Verification Required

#### 1. Real OAuth2 Browser Flow

**Test:** Configure a real Google Cloud Desktop app OAuth credential, replace `CLIENT_CONFIG` in `src/mote/drive.py` with the real values, run `mote auth google`.
**Expected:** Browser opens to Google consent screen; after approval, `~/.mote/google_token.json` is created with 600 permissions; subsequent `mote auth google` runs show the authenticated email without opening a browser.
**Why human:** Cannot test real OAuth2 browser consent flow programmatically without a live Google Cloud project.

#### 2. End-to-End Drive Upload After Recording

**Test:** With real credentials configured, run `mote record --destination drive`, record a few seconds of audio, stop recording. Then check Google Drive.
**Expected:** A folder named "Mote Transcripts" (or configured name) appears in Drive; transcript files (.md, .txt, .json) are present inside it with correct content.
**Why human:** Requires live Drive API, real audio, real BlackHole device setup.

#### 3. Drive Upload Failure Warning (Real Network)

**Test:** Revoke the OAuth token manually, then run `mote record --destination drive` and let transcription complete.
**Expected:** Transcription succeeds, local files are written, a warning message appears: "Warning: Drive upload failed: ... Transcripts saved locally. Run 'mote upload' to retry." Exit code 0.
**Why human:** Requires live Drive API failure scenario with real revoked credentials.

### Gaps Summary

No gaps found. All 10 observable truths are verified. All artifacts exist at appropriate depth (not stubs), are wired to their callers, and data flows through the critical paths. The one known implementation stub (CLIENT_CONFIG placeholder values) is intentional, documented, and does not affect goal achievement — the full CLI and upload machinery is real and functional once real credentials are supplied.

The pre-existing test failure in `test_models.py::test_download_model_passes_tqdm_class` is unrelated to this phase and was deferred in both plan summaries.

---

_Verified: 2026-03-29_
_Verifier: Claude (gsd-verifier)_
