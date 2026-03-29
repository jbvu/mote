# Phase 8: Google Drive Integration - Research

**Researched:** 2026-03-29
**Domain:** Google Drive API v3, OAuth2 Installed App Flow, Python
**Confidence:** HIGH

## Summary

Phase 8 adds Google Drive as a transcript destination. The core work is: (1) a new `drive.py` module wrapping the Drive API, (2) a `mote auth google` command group with OAuth2 browser flow, (3) a `mote upload` command for manual/retry uploads, (4) `[destinations]` config section with folder_name and folder_id caching, and (5) wiring the Drive upload into `_run_transcription()` after local write.

The Google library stack (google-api-python-client, google-auth-oauthlib, google-auth) is mature and well-documented. The official quickstart pattern for installed apps covers the entire flow: `InstalledAppFlow.from_client_secrets_file()` → `run_local_server(port=0)` → `Credentials.from_authorized_user_file()` with refresh. Drive API v3 folder search, folder creation, and file upload are all straightforward single-call operations.

The main design risks are: (1) the `drive.file` scope being too restrictive for folder search (it only covers files the app creates, not existing folders), and (2) the embedded `client_id` pattern — the Cloud Console project must be configured as "Desktop app" (not "Web") for the OOB-free local server flow to work without a redirect URI allowlist.

**Primary recommendation:** Use `drive.file` scope plus folder creation on first run (never search for existing folders the user created outside Mote) — this avoids the scope mismatch entirely and is the most privacy-respecting approach.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Ship a Google Cloud "installed app" (Desktop type) client_id embedded in source code. Standard practice for open-source CLI tools (gcloud, gh). Users run `mote auth google` with zero credential setup.
- **D-02:** Store OAuth refresh token at `~/.mote/google_token.json` with permissions 600, consistent with existing config layout.
- **D-03:** Use `access_type='offline'` and `prompt='consent'` with `run_local_server(port=0)` per roadmap decision. OOB flow deprecated.
- **D-04:** Config schema uses simple list: `[destinations] active = ["local"]`. Adding `"drive"` enables auto-upload. `--destination` flag overrides per-run.
- **D-05:** Local files are always written regardless of destination flag. Drive upload is additive, not a replacement.
- **D-06:** `[destinations.drive]` subsection holds Drive-specific config (folder_name).
- **D-07:** Upload ALL configured output formats (md, txt, json — whatever the user has in `output.format`) to Drive.
- **D-08:** Use named folder with auto-create: `[destinations.drive] folder_name = "Mote Transcripts"`. On first upload, search Drive for folder by name; if not found, create it. Cache folder_id locally.
- **D-09:** Destination errors are warnings, not failures — one-line warning with retry hint.
- **D-10:** `mote auth google` when already authenticated shows status (email, token validity, folder) and offers re-auth via `click.confirm`. Non-destructive by default.
- **D-11:** First-time `mote auth google` opens browser consent page, stores refresh token, confirms success with email display.
- **D-12:** Add `mote upload [file]` command for manual/retry uploads. Completes the Drive workflow for failed auto-uploads.

### Claude's Discretion
- Drive API scope selection (drive.file vs broader scope)
- Folder ID caching mechanism (in token file, separate cache file, or config)
- File naming convention on Drive (mirror local filenames or add metadata)
- Whether `mote upload` without arguments uploads the most recent transcript or requires explicit file path

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INT-03 | User can configure transcript destinations via `[destinations]` config section and `--destination` flag | Config schema pattern (D-04, D-06) documented; `set_config_value` needs extension for nested `destinations.drive.folder_name` keys (current impl only handles 2-part dotted keys) |
| INT-04 | User can upload transcripts to Google Drive via `mote auth google` (one-time OAuth2 browser consent) + automatic upload after transcription | Full OAuth2 flow + Drive API upload pattern documented; integration hook is `_run_transcription()` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-api-python-client | 2.193.0 | Drive API v3 calls (files.create, files.list) | Official Google Python client; weekly releases; stable v3 Drive API |
| google-auth-oauthlib | 1.3.0 | InstalledAppFlow for OAuth2 browser consent | Official auth library for installed apps; handles local redirect server |
| google-auth | 2.49.1 | Token refresh, Credentials serialization | Dependency of oauthlib; handles `.refresh()` and `Credentials.from_authorized_user_file()` |

**Note on CLAUDE.md versions vs current PyPI:**
- CLAUDE.md specifies google-auth 2.38.0, google-auth-oauthlib 1.x, google-api-python-client 2.193.0
- PyPI current: google-auth 2.49.1, google-auth-oauthlib 1.3.0, google-api-python-client 2.193.0
- Use `>=` minimum version specs in pyproject.toml; these libraries are backward compatible within major version

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| googleapiclient.http.MediaFileUpload | (bundled) | Multipart file upload for Drive | Used in every file upload call |
| googleapiclient.errors.HttpError | (bundled) | Typed error for Drive API failures | Catch for 4xx/5xx from Drive API |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| drive.file scope | drive scope (full) | Full scope sees all user's Drive files — unnecessarily broad; drive.file is correct for an app that only manages its own uploads |
| drive.file scope | drive.appdata scope | appdata is hidden/non-browsable storage — user can't see files in Drive UI; wrong for our use case |
| Credentials.to_json() | pickle | JSON is human-readable and future-proof; pickle is brittle across Python versions |

**Installation:**
```bash
pip install "google-api-python-client>=2.193.0" "google-auth-oauthlib>=1.3.0" "google-auth>=2.38.0"
```

Add to pyproject.toml `dependencies` list (not optional-dependencies — Drive upload is a core v2 feature).

## Architecture Patterns

### Recommended Project Structure
```
src/mote/
├── drive.py         # New: Google Drive API wrapper (pure functions)
├── cli.py           # Modified: add auth group + upload command + _run_transcription wiring
├── config.py        # Modified: add [destinations] section to default config
└── ...
```

### Pattern 1: OAuth2 Installed App Flow

**What:** `InstalledAppFlow.from_client_config()` (not `from_client_secrets_file` — we embed credentials in code, not a separate JSON file) → `run_local_server(port=0)` → serialize credentials to `~/.mote/google_token.json`.

**When to use:** First-time auth and re-auth via `mote auth google`.

```python
# Source: https://developers.google.com/workspace/drive/api/quickstart/python (adapted)
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# client_config embedded in source (D-01)
CLIENT_CONFIG = {
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

def get_credentials(token_path: Path) -> Credentials | None:
    """Load credentials from token file, refreshing if expired."""
    if not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            token_path.chmod(0o600)
    return creds if creds.valid else None

def run_auth_flow(token_path: Path) -> Credentials:
    """Run browser OAuth2 consent flow and store token (D-03)."""
    flow = InstalledAppFlow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
    )
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )
    token_path.write_text(creds.to_json())
    token_path.chmod(0o600)
    return creds
```

### Pattern 2: Folder Search-or-Create with Caching

**What:** Search Drive by folder name using `files().list(q=...)`. Cache folder_id to avoid repeated API calls. Note: `drive.file` scope only sees files/folders the app created. For D-08's "search first" behavior, we must use this scope limitation as a design constraint.

**Scope decision (Claude's discretion):** Use `drive.file` + create folder on first upload, cache folder_id in token file. Never search for user-created folders (outside scope). The folder_id cache makes this invisible to the user.

```python
# Source: https://developers.google.com/drive/api/guides/folder
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def get_or_create_folder(service, folder_name: str) -> str:
    """Return folder_id for named folder, creating it if absent."""
    # Search only among folders this app created (drive.file scope)
    q = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    # Create the folder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]
```

### Pattern 3: File Upload

**What:** `MediaFileUpload` for the local file + `files().create()` with parent folder_id.

```python
# Source: https://developers.google.com/drive/api/guides/manage-uploads
from googleapiclient.http import MediaFileUpload

MIME_TYPES = {
    "md": "text/markdown",
    "txt": "text/plain",
    "json": "application/json",
}

def upload_file(service, local_path: Path, folder_id: str) -> str:
    """Upload local_path to Drive folder. Returns Drive file ID."""
    ext = local_path.suffix.lstrip(".")
    mime = MIME_TYPES.get(ext, "text/plain")
    metadata = {"name": local_path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(local_path), mimetype=mime)
    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
    ).execute()
    return file["id"]
```

### Pattern 4: drive.py Module Structure

**What:** Pure function module, no classes, lazy imports at function boundary (Phase 4 pattern).

```python
# src/mote/drive.py — top-level structure
def get_token_path(config_dir: Path) -> Path: ...
def get_credentials(token_path: Path) -> Credentials | None: ...
def run_auth_flow(token_path: Path) -> Credentials: ...
def build_service(creds: Credentials): ...
def get_or_create_folder(service, folder_name: str) -> str: ...
def upload_file(service, local_path: Path, folder_id: str) -> str: ...
def upload_transcripts(config_dir: Path, files: list[Path], folder_name: str) -> None: ...
    """Top-level: load creds, build service, get/create folder, upload all files.
    Raises DriveUploadError on failure so caller can warn (D-09)."""
```

### Pattern 5: Folder ID Caching

**What (Claude's discretion):** Store folder_id in the token JSON file alongside the OAuth credentials. `Credentials.to_json()` produces a dict we can extend before writing.

```python
def _save_token(token_path: Path, creds: Credentials, folder_id: str | None = None) -> None:
    data = json.loads(creds.to_json())
    if folder_id:
        data["drive_folder_id"] = folder_id
    token_path.write_text(json.dumps(data))
    token_path.chmod(0o600)

def _load_folder_id(token_path: Path) -> str | None:
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    return data.get("drive_folder_id")
```

**Why token file, not config:** The folder_id is a runtime artifact (Drive-assigned ID, not user-configured). It changes if the folder is deleted and recreated. Storing it alongside the auth token (same lifecycle) is cleaner than polluting config.toml.

### Pattern 6: config.py Extension

Add `[destinations]` and `[destinations.drive]` to `_write_default_config()`:

```python
# In _write_default_config:
destinations = tomlkit.table()
destinations.add(tomlkit.comment("Destinations: local, drive"))
destinations.add("active", ["local"])
doc.add("destinations", destinations)

destinations_drive = tomlkit.table()
destinations_drive.add(tomlkit.comment("Google Drive folder name for uploads"))
destinations_drive.add("folder_name", "Mote Transcripts")
# Note: tomlkit super-table syntax for [destinations.drive]
destinations["drive"] = destinations_drive
```

**IMPORTANT:** `set_config_value()` currently only handles `section.key` (2-part keys). For `destinations.drive.folder_name` (3-part), either extend `set_config_value` or accept that users set this manually. For Phase 8 the folder name defaults are fine; extend `set_config_value` to handle 3-part keys.

### Pattern 7: CLI auth group

```python
# In cli.py — follows existing @cli.group() pattern
@cli.group()
def auth():
    """Manage third-party service authentication."""
    pass

@auth.command("google")
def auth_google():
    """Authenticate with Google Drive (OAuth2 browser flow)."""
    config_dir = get_config_dir()
    token_path = config_dir / "google_token.json"
    # Check existing auth (D-10)
    creds = get_credentials(token_path)
    if creds:
        # Show status, offer re-auth
        ...
    else:
        # First-time auth (D-11)
        creds = run_auth_flow(token_path)
        ...
```

### Pattern 8: _run_transcription integration

```python
# In _run_transcription(), after write_transcript() returns written paths:
cfg_destinations = cfg.get("destinations", {}).get("active", ["local"])  # ← need cfg passed in
if "drive" in cfg_destinations:
    try:
        folder_name = cfg.get("destinations", {}).get("drive", {}).get("folder_name", "Mote Transcripts")
        upload_transcripts(config_dir, written, folder_name)
    except Exception as e:
        click.echo(f"Warning: Drive upload failed: {e}. Transcripts saved locally. Run 'mote upload' to retry.")
```

Note: `_run_transcription()` currently does NOT receive `cfg` or `config_dir` — it will need these added as parameters (or they can be loaded inside the function). Simplest: pass `cfg` in from callers that already have it.

### Anti-Patterns to Avoid
- **Loading google libraries at module import time:** Follows Phase 4 lazy import pattern — import inside `drive.py` functions, not at top of `cli.py`
- **Raising exceptions from upload as hard failures:** D-09 requires warnings only — always catch upload exceptions and warn, never propagate to fail the transcription
- **Using `pickle` for token storage:** Use `Credentials.to_json()` and JSON files — cross-version safe and readable
- **Using `drive` scope (full):** Use `drive.file` — only grants access to files the app creates; much better privacy posture
- **Storing folder_id in config.toml:** Folder IDs are runtime artifacts, not user config; store in token file
- **`from_client_secrets_file()` with an on-disk JSON:** Embed CLIENT_CONFIG dict directly in `drive.py`; no credentials file to lose or misconfigure

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth2 token refresh | Custom HTTP refresh logic | `google.auth.transport.requests.Request` + `creds.refresh()` | Handles token expiry, retry, error cases correctly |
| Multipart file upload | Raw `requests.post` with multipart body | `googleapiclient.http.MediaFileUpload` | Handles chunking, MIME type, progress for large files |
| HTTP error handling | Parse JSON error bodies manually | `googleapiclient.errors.HttpError` | Typed, has `.status_code` and `.reason` |
| Browser redirect server | Custom HTTP server for OAuth callback | `run_local_server(port=0)` | Handles port binding, browser open, code exchange |

**Key insight:** The Google Python client library handles all transport, retry, and auth complexity. The application code is only responsible for: (1) initiating the flow, (2) persisting the token, and (3) building the service.

## Common Pitfalls

### Pitfall 1: `drive.file` Scope Cannot Find User-Created Folders

**What goes wrong:** `files().list(q="name='Mote Transcripts'...")` returns empty even if the user manually created a folder with that name in Drive.

**Why it happens:** `drive.file` scope only grants access to files/folders the app itself created. It cannot see files created by other means.

**How to avoid:** With `drive.file` scope: never assume a folder already exists from a prior session unless you have the cached folder_id. On each startup with no cached ID: call `get_or_create_folder()` which will create a new folder if the app hasn't seen one before. The cached folder_id is the source of truth.

**Warning signs:** `files().list()` returns empty results even though user sees folder in Drive UI.

### Pitfall 2: `access_type='offline'` Not Passed to `run_local_server`

**What goes wrong:** Access token is returned but no refresh token. After ~1 hour the token expires and `mote` requires full re-auth.

**Why it happens:** `run_local_server()` passes `**kwargs` to the underlying OAuth session. Without `access_type='offline'`, Google issues access-only tokens.

**How to avoid:** Always pass `access_type="offline"` and `prompt="consent"` to `run_local_server()` (D-03).

### Pitfall 3: `set_config_value` Rejects 3-Part Keys

**What goes wrong:** `mote config set destinations.drive.folder_name "My Folder"` raises `ValueError: Key must be in 'section.key' format`.

**Why it happens:** Current `set_config_value` splits on `.` and expects exactly 2 parts.

**How to avoid:** Extend `set_config_value` to handle 2-part and 3-part keys. Or provide a dedicated config path in the `mote auth google` flow that writes the value directly.

### Pitfall 4: `_run_transcription` Lacks `cfg` and `config_dir` Parameters

**What goes wrong:** Drive upload requires knowing (a) whether drive is in `active` destinations and (b) where `~/.mote/` is for the token file.

**Why it happens:** `_run_transcription()` was designed in Phase 6 without Drive in scope.

**How to avoid:** Add `cfg: dict` and `config_dir: Path` as parameters to `_run_transcription()`. Both callers (`record_command`, `transcribe_command`) already have `cfg` loaded and `config_dir` available.

### Pitfall 5: Embedded `client_id` Requires Desktop App Type in Cloud Console

**What goes wrong:** Browser shows "redirect_uri_mismatch" error if the Cloud project is configured as "Web application" instead of "Desktop app".

**Why it happens:** Web app OAuth requires allowlisted redirect URIs. Desktop app type allows `http://localhost` redirects without allowlisting.

**How to avoid:** Document clearly that the Cloud Console project must be type "Desktop app". The embedded `client_id` must come from a Desktop app credential.

### Pitfall 6: Token File Created with Wrong Permissions

**What goes wrong:** Token file created world-readable if `path.write_text()` is called before `path.chmod(0o600)`.

**Why it happens:** `write_text` creates file with default umask permissions.

**How to avoid:** Always call `path.chmod(0o600)` immediately after every `write_text()` call on the token file. This is the same pattern used for `config.toml`.

### Pitfall 7: `MediaFileUpload` With Large Files

**What goes wrong:** Upload of large transcript files (json can be multi-MB) fails silently or times out.

**Why it happens:** Default `MediaFileUpload` does non-resumable upload. For files > 5MB, resumable upload is recommended.

**How to avoid:** Transcript files (md, txt, json) are typically < 1MB — non-resumable is fine. Document the limit; if a file is somehow large, `MediaFileUpload(resumable=True)` handles it.

## Code Examples

### Complete auth flow with status check

```python
# Source: official quickstart + drive.py design from CONTEXT.md
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def get_credentials(token_path: Path) -> Credentials | None:
    if not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        token_path.chmod(0o600)
    return creds if creds.valid else None

def run_auth_flow(token_path: Path) -> Credentials:
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    token_path.write_text(creds.to_json())
    token_path.chmod(0o600)
    return creds
```

### Upload all transcript files

```python
# drive.py top-level upload function
def upload_transcripts(config_dir: Path, files: list[Path], folder_name: str) -> None:
    """Upload all files to Drive. Raises on failure so caller can warn (D-09)."""
    from googleapiclient.discovery import build  # lazy import
    token_path = config_dir / "google_token.json"
    creds = get_credentials(token_path)
    if creds is None:
        raise RuntimeError("Not authenticated. Run: mote auth google")
    service = build("drive", "v3", credentials=creds)

    folder_id = _load_folder_id(token_path)
    if not folder_id:
        folder_id = get_or_create_folder(service, folder_name)
        _save_token(token_path, creds, folder_id=folder_id)

    for f in files:
        upload_file(service, f, folder_id)
```

### Drive upload warning in _run_transcription (D-09)

```python
# In cli.py _run_transcription() — after write_transcript() returns:
active_destinations = cfg.get("destinations", {}).get("active", ["local"])
if "drive" in active_destinations:
    try:
        from mote.drive import upload_transcripts  # lazy import
        folder_name = (
            cfg.get("destinations", {}).get("drive", {}).get("folder_name", "Mote Transcripts")
        )
        upload_transcripts(config_dir, written, folder_name)
    except Exception as e:
        click.echo(
            f"Warning: Drive upload failed: {e}. "
            "Transcripts saved locally. Run 'mote upload' to retry."
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `oauth2client` library | `google-auth` + `google-auth-oauthlib` | ~2019 | oauth2client deprecated; do not use |
| OOB redirect (`urn:ietf:wg:oauth:2.0:oob`) | `run_local_server(port=0)` | Oct 2022 | OOB deprecated; local server is the only supported desktop flow |
| Drive API v2 | Drive API v3 | 2015 (v3 GA) | v3 is current; use `build("drive", "v3", ...)` |

**Deprecated/outdated:**
- `oauth2client`: Removed from pip recommendations in 2019; `google-auth` replaces it entirely
- OOB `urn:ietf:wg:oauth:2.0:oob` redirect: Deprecated October 2022; will not work for new Cloud Console projects

## Open Questions

1. **Embedded client_id confidentiality**
   - What we know: gcloud, gh, and other open-source tools embed client_id/client_secret in source; this is accepted practice for "installed app" type credentials
   - What's unclear: Whether the user (project maintainer) wants to add a `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` env var override so their personal Cloud project can be used for testing without committing credentials to git
   - Recommendation: Add env var override `MOTE_GOOGLE_CLIENT_ID` / `MOTE_GOOGLE_CLIENT_SECRET` in `drive.py`; fall back to embedded constants; document in README that contributors need their own Cloud project for development

2. **`mote upload` without arguments — most recent or required path?**
   - What we know: D-12 says "uploads a local transcript file on demand" without specifying default behavior
   - What's unclear: UX preference — auto-detect most recent vs. require explicit path
   - Recommendation: Require explicit file path (safer, clearer). Add `--last` flag to upload the most recent transcript. This avoids accidental uploads.

3. **`--destination` flag implementation**
   - What we know: D-04 specifies `--destination drive` overrides active list per-run
   - What's unclear: Does `--destination local` suppress auto-upload even when drive is in `active`?
   - Recommendation: `--destination` replaces the `active` list entirely for that run. So `--destination local` means local only even if `active = ["local", "drive"]`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| google-api-python-client | Drive upload | Not yet installed | — | None — must install |
| google-auth-oauthlib | OAuth2 flow | Not yet installed | — | None — must install |
| google-auth | Token refresh | Not yet installed | — | None — must install |
| Python 3.11+ | Runtime | macOS system | 3.13 (venv) | — |

**Missing dependencies with no fallback:**
- `google-api-python-client`, `google-auth-oauthlib`, `google-auth` — must be added to `pyproject.toml` dependencies and installed

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_drive.py tests/test_cli.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INT-03 | `[destinations]` section written to default config | unit | `pytest tests/test_config.py::test_default_config_has_destinations -x` | ❌ Wave 0 |
| INT-03 | `active = ["local"]` default; adding `"drive"` enables upload | unit | `pytest tests/test_config.py::test_destinations_active_default -x` | ❌ Wave 0 |
| INT-03 | `--destination drive` overrides config per-run | unit (CLI mock) | `pytest tests/test_cli.py::test_destination_flag_override -x` | ❌ Wave 0 |
| INT-04 | `mote auth google` when no token: runs flow, saves token 600 | unit (mock flow) | `pytest tests/test_drive.py::test_auth_flow_saves_token -x` | ❌ Wave 0 |
| INT-04 | `mote auth google` when valid token: shows status, no re-auth | unit (mock creds) | `pytest tests/test_drive.py::test_auth_status_shows_when_valid -x` | ❌ Wave 0 |
| INT-04 | `upload_transcripts()` calls Drive API and uploads all formats | unit (mock service) | `pytest tests/test_drive.py::test_upload_all_formats -x` | ❌ Wave 0 |
| INT-04 | Drive upload failure is warning, not exception in `_run_transcription` | unit (mock fail) | `pytest tests/test_cli.py::test_drive_upload_failure_is_warning -x` | ❌ Wave 0 |
| INT-04 | `mote upload <file>` uploads file to Drive | unit (mock service) | `pytest tests/test_cli.py::test_upload_command -x` | ❌ Wave 0 |
| INT-04 | Token file permissions are 600 after auth flow | unit | `pytest tests/test_drive.py::test_token_file_permissions -x` | ❌ Wave 0 |
| INT-04 | Folder ID cached in token file after first upload | unit (mock service) | `pytest tests/test_drive.py::test_folder_id_cached -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_drive.py tests/test_cli.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_drive.py` — covers all INT-04 drive module tests
- [ ] Additional tests in `tests/test_cli.py` — covers INT-03 destination flag, INT-04 CLI integration
- [ ] Additional tests in `tests/test_config.py` — covers INT-03 destinations config section

*(Existing `conftest.py` with `mote_home` fixture is sufficient — no new shared fixtures needed)*

## Sources

### Primary (HIGH confidence)
- [Google Drive API Python Quickstart](https://developers.google.com/workspace/drive/api/quickstart/python) — complete auth flow, token storage, `run_local_server(port=0)` pattern
- [Drive API: Create and Populate Folders](https://developers.google.com/drive/api/guides/folder) — folder creation, parents field, MIME type
- [Drive API: Manage Uploads](https://developers.google.com/drive/api/guides/manage-uploads) — MediaFileUpload, files().create() pattern
- [Drive API: Search Files](https://developers.google.com/drive/api/guides/search-files) — list() with q parameter for folder search
- [google-auth-oauthlib API Reference](https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html) — InstalledAppFlow, run_local_server parameters
- PyPI verified versions (2026-03-29): google-api-python-client 2.193.0, google-auth-oauthlib 1.3.0, google-auth 2.49.1

### Secondary (MEDIUM confidence)
- [OAuth2 for Installed Applications (google-api-python-client docs)](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html) — OOB deprecation context, local server as standard pattern

### Tertiary (LOW confidence)
- None — all critical claims verified against official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyPI latest versions confirmed, official docs verified
- Architecture: HIGH — patterns taken directly from official Google quickstart and API guides; adapted for project conventions from CONTEXT.md
- Pitfalls: HIGH — drive.file scope limitation verified; token refresh and permission patterns confirmed against official examples

**Research date:** 2026-03-29
**Valid until:** 2026-06-29 (Google API library releases are frequent but backward compatible; OAuth2 flow pattern is stable)
