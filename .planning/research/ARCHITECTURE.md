# Architecture Research

**Domain:** CLI meeting transcription tool — v2.0 integration and polish additions
**Researched:** 2026-03-28
**Confidence:** HIGH (based on direct codebase inspection + verified library documentation)

## Standard Architecture

### System Overview (Current v1 + v2 additions marked NEW)

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer  (cli.py)                      │
│  mote record  │  mote transcribe  │  mote auth  │  mote config  │
│  [existing]   │  [NEW — CLI-07]   │ [NEW auth]  │  [existing]   │
├───────────────┴───────────────────┴─────────────┴───────────────┤
│                     Core Pipeline Modules                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ audio.py │  │transcribe │  │ output.py│  │destinations/  │  │
│  │ existing +│  │   .py     │  │existing +│  │ [NEW module]  │  │
│  │ routing+ │  │ unchanged │  │ +json fmt│  │ drive.py      │  │
│  │ silence  │  │           │  │          │  │ notebooklm.py │  │
│  └──────────┘  └───────────┘  └──────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                     Infrastructure Modules                        │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐  │
│  │ config.py                │  │ models.py                    │  │
│  │ existing + [destinations]│  │ unchanged                    │  │
│  │ section + validate_config│  │                              │  │
│  └──────────────────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      Storage Layer                                │
│  ~/.mote/config.toml           (extended: [destinations] section)│
│  ~/.mote/google_token.json     (NEW — written by OAuth2 flow)    │
│  ~/.mote/google_credentials.json (user-provided, not generated)  │
│  ~/.mote/recordings/*.wav      (existing)                        │
│  ~/.notebooklm/storage_state.json (managed by notebooklm-py)    │
│  ~/Documents/mote/*.md|txt|json (existing + json format NEW)     │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | v2 Status |
|-----------|----------------|-----------|
| `cli.py` | Click command group wiring, flag parsing, user feedback | Modified — add `mote transcribe`, `mote auth`, `--destination` flag |
| `audio.py` | BlackHole device detection, recording loop, WAV writing, PID management | Modified — add routing wrapper + silence detection |
| `transcribe.py` | Engine dispatch (local KB-Whisper, OpenAI), chunking | Unchanged |
| `output.py` | Format rendering (markdown, txt), file naming, listing | Modified — add JSON format branch |
| `config.py` | TOML read/write, env var overrides, config dir resolution | Modified — add `[destinations]` section, `validate_config()` |
| `models.py` | HuggingFace model lifecycle (download/list/delete) | Unchanged |
| `destinations/__init__.py` | Destination registry, `deliver()` dispatcher | New |
| `destinations/drive.py` | Google Drive OAuth2 token management + file upload | New |
| `destinations/notebooklm.py` | notebooklm-py async wrapper + source upload | New |

---

## Recommended Project Structure

```
src/mote/
├── cli.py              # Modified: add mote transcribe, mote auth group, --destination flag
├── audio.py            # Modified: add auto_route_audio(), silence threshold tracking
├── transcribe.py       # Unchanged
├── output.py           # Modified: add "json" format to write_transcript()
├── config.py           # Modified: [destinations] in default config, validate_config()
├── models.py           # Unchanged
└── destinations/
    ├── __init__.py     # New: registry dict, deliver(paths, cfg) dispatcher
    ├── drive.py        # New: get_drive_credentials(), upload_file()
    └── notebooklm.py   # New: upload_to_notebooklm() asyncio.run() wrapper

~/.mote/
├── config.toml                  # Extended with [destinations] and sub-sections
├── google_token.json            # New: written by InstalledAppFlow, chmod 600
├── google_credentials.json      # User-provided: downloaded from Google Cloud Console
└── recordings/                  # Existing: temp WAV files
```

### Structure Rationale

- **`destinations/` subpackage:** External-service concerns stay isolated from the core pipeline. `output.py` writes local files; destinations consume those written paths. Zero coupling between transcription and delivery.
- **`destinations/__init__.py` as registry:** `cli.py` and `output.py` never import Drive or NotebookLM directly. They call `deliver(paths, cfg)` and the registry routes from there. This makes adding a future destination (e.g., Dropbox) a one-file change.
- **Auth tokens in `~/.mote/`:** All Mote state in one place, respecting `MOTE_HOME` env var. The existing test isolation pattern depends on this — every path must go through `get_config_dir()`, not `Path.home() / ".mote"` directly.
- **`~/.notebooklm/`:** notebooklm-py manages its own storage directory independently. Mote does not own or write these files; `mote auth notebooklm` just invokes the notebooklm-py login flow.

---

## Architectural Patterns

### Pattern 1: Destinations as Post-Write Side Effects

**What:** `write_transcript()` returns `list[Path]` of written files. After writing, the CLI calls a `deliver()` helper passing those paths to each enabled destination.

**When to use:** Every `mote record` and `mote transcribe` invocation where destinations are configured.

**Trade-offs:** Simple and sequential. Destination errors do not roll back local files. Network failure during Drive upload never loses the transcript — it's already written locally.

**Data flow:**
```
record_session() -> WAV path
    -> transcribe_file() -> transcript text
        -> write_transcript() -> list[Path]    (local files always written first)
            -> destinations.deliver(paths, cfg)  (optional, per config)
                -> drive.upload(path)
                -> notebooklm.add_source(path)
            -> wav_path.unlink()
```

### Pattern 2: Extract `_run_transcription()` Helper Before Adding Destinations

**What:** The post-recording block in `record_command` (cli.py lines 142-181) is already the full transcription + output pipeline. Before wiring destinations, extract it into a module-level helper `_run_transcription(wav_path, cfg, engine, language, name)`.

**Why this must happen first:** Both `record_command` and the new `transcribe_command` need identical transcription+output+delivery behavior. Extracting the helper eliminates duplication and provides a single place to add `deliver()` calls.

**Example skeleton:**
```python
def _run_transcription(wav_path: Path, cfg: dict, engine: str,
                       language: str, model_alias: str,
                       name: str | None) -> list[Path]:
    duration = get_wav_duration(wav_path)
    transcript = transcribe_file(wav_path, engine, language, model_alias, ...)
    output_cfg = cfg.get("output", {})
    output_dir = Path(output_cfg.get("dir", "~/Documents/mote")).expanduser()
    formats = output_cfg.get("format", ["markdown", "txt"])
    written = write_transcript(transcript, output_dir, formats, duration, ...)
    from mote.destinations import deliver
    deliver(written, cfg)
    return written
```

`record_command` calls `_run_transcription(wav_path, ...)` then `wav_path.unlink()`.
`transcribe_command` calls `_run_transcription(file, ...)` — no WAV cleanup (user owns the file).

### Pattern 3: Destination Registry in `destinations/__init__.py`

**What:** A dict mapping destination name strings to handler callables. The `[destinations] enabled` config list drives which handlers are called.

**Example skeleton:**
```python
# destinations/__init__.py
from pathlib import Path

_REGISTRY: dict = {}

def register(name: str):
    def decorator(fn):
        _REGISTRY[name] = fn
        return fn
    return decorator

def deliver(paths: list[Path], cfg: dict) -> None:
    enabled = cfg.get("destinations", {}).get("enabled", [])
    for name in enabled:
        handler = _REGISTRY.get(name)
        if handler:
            try:
                handler(paths, cfg)
            except Exception as e:
                import click
                click.echo(f"Warning: destination '{name}' failed: {e}")
```

Handlers register themselves at import time:
```python
# destinations/drive.py
from mote.destinations import register

@register("google_drive")
def _handle(paths, cfg):
    folder_id = cfg.get("destinations", {}).get("google_drive", {}).get("folder_id", "")
    for path in paths:
        upload_file(path, folder_id)
```

**Trade-offs:** The registry adds minor indirection. For two destinations it may feel over-engineered, but it pays off at the Web UI phase when Flask routes also need to trigger delivery.

### Pattern 4: Config Extension for `[destinations]`

**What:** Add a `[destinations]` section to `config.toml`. `set_config_value()` currently rejects unknown sections and keys (config.py lines 52-55). New section requires extending `_write_default_config()` AND the validation whitelist in `set_config_value()`.

**Config additions:**
```toml
[destinations]
# Enabled destinations: google_drive, notebooklm (empty = local only)
enabled = []

[destinations.google_drive]
folder_id = ""   # Drive folder ID to upload into

[destinations.notebooklm]
notebook_id = "" # NotebookLM notebook ID
```

**Constraint with `set_config_value()`:** The current implementation uses `doc[section][field]` with a two-part key check. Nested sections like `destinations.google_drive.folder_id` would need a three-part key. Either extend `set_config_value()` to handle three-part keys, or document that destinations config is set directly via `mote auth` commands rather than `mote config set`.

### Pattern 5: Audio Routing as Wrapper Around `record_session()`

**What:** `auto_route_audio()` in `audio.py` captures the current macOS audio output device, switches to BlackHole, calls `record_session()`, then restores the original device in `try/finally`.

**macOS mechanism:** `SwitchAudioSource` CLI tool via subprocess. Installable via `brew install switchaudio-osx`. Degrade gracefully if not installed — print a warning and proceed without auto-routing.

**Example skeleton:**
```python
def _get_current_output_device() -> str | None:
    """Return current default output device name via SwitchAudioSource, or None."""
    result = subprocess.run(["SwitchAudioSource", "-t", "output", "-c"],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None

def _set_output_device(name: str) -> bool:
    """Switch macOS default output to name. Returns True on success."""
    result = subprocess.run(["SwitchAudioSource", "-t", "output", "-s", name],
                            capture_output=True)
    return result.returncode == 0

def auto_route_audio(device_index: int, recordings_dir: Path,
                     pid_path: Path) -> Path:
    original = _get_current_output_device()
    if original:
        _set_output_device("BlackHole 2ch")
    try:
        return record_session(device_index, recordings_dir, pid_path)
    finally:
        if original:
            _set_output_device(original)
```

`record_command` in `cli.py` calls `auto_route_audio()` instead of `record_session()` when auto-routing is enabled (config flag or `--auto-route` CLI flag).

### Pattern 6: Silence Detection as In-Loop Monitor

**What:** Track consecutive silent chunks inside `record_session()`'s main loop. After N seconds of silence, emit a single Rich warning without stopping recording.

**Integration point:** The existing `current_db = rms_db(chunk)` line in `record_session()` is the hook. Add a silent-chunk counter and a "warning already shown" flag around it.

**Example addition inside the `while not stop_event.is_set()` loop:**
```python
SILENCE_THRESHOLD_DB = -50.0
SILENCE_WARN_SECONDS = 10
silence_chunks = 0
silence_warned = False

# inside loop, after: current_db = rms_db(chunk)
if current_db < SILENCE_THRESHOLD_DB:
    silence_chunks += 1
    if not silence_warned and silence_chunks >= (SILENCE_WARN_SECONDS * SAMPLE_RATE // BLOCKSIZE):
        click.echo("\nWarning: No audio signal detected. Check your BlackHole routing.")
        silence_warned = True
else:
    silence_chunks = 0
    silence_warned = False
```

No new module needed — this is ~10 lines inside `audio.py`.

### Pattern 7: Google Drive OAuth2 Auth Flow

**What:** One-time InstalledAppFlow. Opens browser for user consent. Token saved to `~/.mote/google_token.json`. Subsequent uploads refresh automatically.

**User setup requirement:** User must create a Google Cloud project, enable Drive API, and download `credentials.json`. This cannot be automated — document in README.

**Implementation (HIGH confidence — matches google-api-python-client installed-app docs):**
```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_credentials() -> Credentials:
    token_path = get_config_dir() / "google_token.json"
    creds_path = get_config_dir() / "google_credentials.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
        token_path.chmod(0o600)
    return creds

def upload_file(path: Path, folder_id: str) -> None:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = get_drive_credentials()
    service = build("drive", "v3", credentials=creds)
    media = MediaFileUpload(str(path), mimetype="text/plain")
    metadata = {"name": path.name, "parents": [folder_id] if folder_id else []}
    service.files().create(body=metadata, media_body=media).execute()
```

### Pattern 8: NotebookLM Async Wrapper

**What:** notebooklm-py's client is async. Since Mote's CLI is synchronous, wrap the async upload call with `asyncio.run()`.

**Auth:** notebooklm-py manages `~/.notebooklm/storage_state.json` (browser cookie state). Sessions expire approximately weekly. `mote auth notebooklm` is a thin wrapper that calls `notebooklm login` as a subprocess or via its CLI entry point.

**Fragility (MEDIUM confidence):** notebooklm-py uses undocumented Google internal APIs. It can break when Google changes internal endpoints. Mark as "experimental" in CLI help text. Surface clear re-auth errors: "NotebookLM session expired — run: mote auth notebooklm".

```python
import asyncio
from pathlib import Path

def upload_to_notebooklm(path: Path, notebook_id: str) -> None:
    async def _upload():
        from notebooklm import NotebookLMClient
        async with await NotebookLMClient.from_storage() as client:
            await client.sources.add_file(notebook_id, path)
    asyncio.run(_upload())
```

---

## Data Flow

### v2 Record -> Transcribe -> Deliver

```
mote record
    |
    v
[optional] auto_route_audio()     captures + switches macOS output device
    |
    v
record_session()                  EXISTING, silence_detector() added inside loop
    | Ctrl+C -> WAV written to ~/.mote/recordings/
    |
    v
[optional] restore_output_device()  try/finally in auto_route_audio()
    |
    v
_run_transcription(wav_path, cfg, ...)   NEW shared helper
    |
    v
validate_config(cfg)             NEW — fail fast on bad engine/missing model
    |
    v
transcribe_file(wav_path, ...)   EXISTING, unchanged
    |
    v
write_transcript(text, ...)      EXISTING + json format NEW
    | returns list[Path]
    |
    v
destinations.deliver(paths, cfg) NEW
    |---> drive.upload_file()     if "google_drive" in destinations.enabled
    |---> notebooklm.upload()     if "notebooklm" in destinations.enabled
    |
    v
wav_path.unlink()                EXISTING (record only — transcribe leaves WAV intact)
```

### mote transcribe <file> (New Command)

```
mote transcribe recording.wav
    |
    v
validate_config(cfg)             same validation as record
    |
    v
_run_transcription(file, cfg, ...)   same helper as record, no WAV cleanup
    |
    v
Summary output to terminal
```

### mote auth google (New Command)

```
mote auth google
    |
    v
check: ~/.mote/google_credentials.json exists?
    NO  -> print setup instructions, exit 1
    YES ->
    v
InstalledAppFlow.from_client_secrets_file()
    | opens browser for user consent
    v
token saved -> ~/.mote/google_token.json (chmod 600)
    |
    v
echo: "Authenticated. Set folder ID: mote config set destinations.google_drive.folder_id <id>"
```

### Config Validation (REL-01)

```
validate_config(cfg) called at start of record + transcribe commands
    |
    +-- engine == "local"?
    |     model downloaded? NO -> ClickException with instructions
    +-- engine == "openai"?
    |     api_key set? NO -> ClickException with instructions
    +-- "google_drive" in destinations.enabled?
    |     google_token.json exists? NO -> warn, continue (don't hard-fail)
    +-- "notebooklm" in destinations.enabled?
          storage_state.json exists? NO -> warn, continue (don't hard-fail)
```

Destination checks are warnings not errors because the user may want local output only and fix auth later. Engine checks are hard errors because transcription cannot proceed without a working engine.

---

## New vs Modified: Explicit Component List

| Component | New / Modified | Summary of Changes |
|-----------|---------------|-------------------|
| `cli.py` | Modified | Add `transcribe_command`, `auth` group, `auth google`, `auth notebooklm`; extract `_run_transcription()` helper; add `--destination` flag override |
| `audio.py` | Modified | Add `auto_route_audio()`, `_get_current_output_device()`, `_set_output_device()`; add silence tracking inside `record_session()` loop |
| `output.py` | Modified | Add `"json"` branch in `write_transcript()` — returns JSON with same metadata as markdown header |
| `config.py` | Modified | Extend `_write_default_config()` with `[destinations]` section and sub-sections; add `validate_config(cfg) -> None`; extend key whitelist in `set_config_value()` |
| `transcribe.py` | Unchanged | No changes needed |
| `models.py` | Unchanged | No changes needed |
| `destinations/__init__.py` | New | `_REGISTRY`, `register()` decorator, `deliver(paths, cfg)` |
| `destinations/drive.py` | New | `get_drive_credentials()`, `upload_file(path, folder_id)` |
| `destinations/notebooklm.py` | New | `upload_to_notebooklm(path, notebook_id)` via `asyncio.run()` |

---

## Build Order Recommendation

Features have dependencies. Recommended sequence minimises risk and ensures each step is independently testable:

1. **Config extension + `validate_config()` (REL-01, INT-03)**
   No external deps. Foundation for everything else. Add `[destinations]` TOML section and validate_config(). Tests: unit tests on config parsing, validation error cases.

2. **JSON output format (INT-02)**
   Zero-risk addition to `write_transcript()`. Add `"json"` to accepted formats. Proves the output extension pattern before destinations touch output paths.

3. **`mote transcribe <file>` + `_run_transcription()` helper (CLI-07)**
   Extract the shared helper first, then wire the new command. The extraction is a refactor with no behavior change — verify with existing tests before adding the command. This step is required before destinations so both `record` and `transcribe` get delivery.

4. **Retry orphaned WAVs (CLI-08)**
   `find_orphan_recordings()` already exists. Add prompt logic at `mote record` startup offering to transcribe orphans via `_run_transcription()`. Depends on step 3.

5. **Silence detection (AUD-06)**
   In-loop change to `record_session()`. ~10 lines. No new module. Low risk, easy to test with a mock audio stream.

6. **Auto-switch audio routing (AUD-05)**
   New `auto_route_audio()` wrapper in `audio.py`. Requires `SwitchAudioSource` to be installed for live testing but degrades gracefully without it. Batch with silence detection (same module, same review).

7. **Google Drive destination (INT-04) + `mote auth google`**
   New `destinations/` subpackage. Establish the registry pattern with Drive first — stable, well-documented official API. Requires live Google account for integration testing.

8. **NotebookLM destination (INT-05) + `mote auth notebooklm`**
   Build after Drive so the registry pattern is established and tested. Lower confidence in stability — mark as experimental.

---

## Anti-Patterns

### Anti-Pattern 1: Putting Destination Logic in `output.py`

**What people do:** Add `drive.upload()` calls inside `write_transcript()` since it's "already the output function."

**Why it's wrong:** `output.py` becomes responsible for both formatting and delivery. Tests for formatting now require mocking Drive API calls. The module has two reasons to change independently. Future destinations further pollute a simple formatter.

**Do this instead:** `write_transcript()` returns paths. The caller (`_run_transcription()` helper in `cli.py`) calls `deliver()` with those paths. `output.py` stays a pure formatter with no knowledge of destinations.

### Anti-Pattern 2: Hardcoded Token Paths Bypassing `MOTE_HOME`

**What people do:** `TOKEN_PATH = Path.home() / ".mote" / "google_token.json"` hardcoded in `drive.py`.

**Why it's wrong:** Breaks test isolation. The `MOTE_HOME` env var + `get_config_dir()` pattern is how existing tests redirect all Mote state to a temp directory. Any path that bypasses this breaks parallel test runs and CI environments.

**Do this instead:** Always `get_config_dir() / "google_token.json"`. Import `get_config_dir` from `mote.config` in `destinations/drive.py`.

### Anti-Pattern 3: Hard-Failing on Destination Errors

**What people do:** Raise `ClickException` if Google Drive upload fails.

**Why it's wrong:** Local files are written before destinations are called. A destination failure (expired token, network error) would make the user think transcription failed when their transcript is sitting in `~/Documents/mote/`. The transcript exists locally and is the source of truth.

**Do this instead:** Catch destination exceptions in `deliver()`, print `click.echo(f"Warning: '{name}' failed: {e}")`, and continue. The local files always survive.

### Anti-Pattern 4: Calling `await` from a Synchronous Click Command

**What people do:** Try to call notebooklm-py's async client directly from a synchronous Click callback.

**Why it's wrong:** Click command callbacks are synchronous. `await` outside an async function is a `SyntaxError`. Even with workarounds, the async event loop is not running.

**Do this instead:** Wrap the entire async sequence with `asyncio.run(_async_fn())` in `destinations/notebooklm.py`. This is the established pattern for calling async libraries from synchronous Python.

### Anti-Pattern 5: Duplicating Transcription Logic Between `record` and `transcribe`

**What people do:** Copy the `cfg` resolution + `transcribe_file()` + `write_transcript()` block from `record_command` into a new `transcribe_command` rather than extracting a shared helper.

**Why it's wrong:** Any change to the transcription or output pipeline (adding a destination, changing filename format) must be made twice. They drift out of sync.

**Do this instead:** Extract `_run_transcription()` helper first (step 3 in build order). Both commands delegate to it.

---

## Integration Points

### External Service Boundaries

| Service | Integration Pattern | Auth Storage | Notes |
|---------|---------------------|-------------|-------|
| Google Drive API v3 | `google-api-python-client` InstalledAppFlow | `~/.mote/google_token.json` (chmod 600) | HIGH confidence pattern; `drive.file` scope sufficient for upload; user must create GCP project + download credentials.json manually |
| Google NotebookLM | `notebooklm-py` unofficial async API via `asyncio.run()` | `~/.notebooklm/storage_state.json` (managed by notebooklm-py) | MEDIUM confidence — undocumented Google internals; sessions expire ~weekly; mark as experimental |
| macOS audio routing | `SwitchAudioSource` CLI via `subprocess.run()` | None (stateless) | Optional system dep (`brew install switchaudio-osx`); degrade gracefully if absent |

### Internal Module Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `cli.py` -> `destinations` | `deliver(paths, cfg)` only — no direct Drive/NotebookLM imports | CLI never couples to a specific destination |
| `output.py` -> `destinations` | No dependency — output writes files, CLI calls deliver separately | Keep `output.py` as a pure formatter |
| `destinations/drive.py` -> `config.py` | `get_config_dir()` for token path | Must use `get_config_dir()` not `Path.home()` for test isolation |
| `audio.py` -> macOS | `subprocess.run(["SwitchAudioSource", ...])` in isolated helpers | Fails gracefully if tool absent; never raises on routing failure |
| `config.py` validation -> `models.py` | `is_model_downloaded(alias)` call in `validate_config()` | One-way dependency, already exists for model management |

---

## Sources

- Direct codebase inspection: `src/mote/cli.py`, `audio.py`, `output.py`, `config.py`, `transcribe.py` (2026-03-28)
- [google-api-python-client OAuth installed app flow](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html) — HIGH confidence
- [Google Drive API v3 Python quickstart](https://developers.google.com/workspace/drive/api/quickstart/python) — HIGH confidence
- [notebooklm-py Python API docs](https://github.com/teng-lin/notebooklm-py/blob/main/docs/python-api.md) — MEDIUM confidence (unofficial API, may change)
- [notebooklm-py PyPI page](https://pypi.org/project/notebooklm-py/) — v0.3.4 confirmed
- notebooklm-py auth: browser cookie via Playwright, `~/.notebooklm/storage_state.json`, sessions expire ~1-2 weeks — MEDIUM confidence (verified against GitHub README)

---
*Architecture research for: Mote v2.0 Integration & Polish*
*Researched: 2026-03-28*
