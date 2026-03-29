# Phase 9: NotebookLM Integration - Research

**Researched:** 2026-03-29
**Domain:** Unofficial NotebookLM Python API via notebooklm-py, cookie-based authentication, async API patterns
**Confidence:** HIGH (library actively maintained, API well-documented, patterns mirror Phase 8)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Research phase MUST check notebooklm-py GitHub status (last commit, open issues, API stability) before planning proceeds. If the library is dead or broken, Phase 9 pivots to documenting "use Drive + manually add to NotebookLM" as the recommended workflow instead of writing code.
- **D-02:** Use cookie extraction from Chrome's cookie store (notebooklm-py's default approach). User must be logged into Google in Chrome. `mote auth notebooklm` extracts and stores the session cookies.
- **D-03:** Store session credentials at `~/.mote/notebooklm_session.json` with permissions 600, consistent with google_token.json pattern from Phase 8.
- **D-04:** Add `"notebooklm"` as a valid destination in the existing `[destinations]` config. Same pattern as Drive: add to `active` list to enable, or use `--destination notebooklm` per-run override.
- **D-05:** Add `[destinations.notebooklm]` subsection in config for NotebookLM-specific settings (notebook name).
- **D-06:** Upload markdown file only (.md) to NotebookLM. Plain text and JSON add no value for NotebookLM's source ingestion.
- **D-07:** Use a single "Mote Transcripts" notebook. Each transcription adds the markdown as a new source. Mirrors the Drive folder approach. Auto-create notebook if it doesn't exist; cache notebook ID locally.
- **D-08:** Same pattern as Drive (D-09 from Phase 8): attempt upload silently, on auth failure show "NotebookLM session expired. Run: mote auth notebooklm". No proactive session checks.
- **D-09:** NotebookLM failures never propagate — local files and Drive upload are unaffected. Warning format matches Drive: one-line with retry hint.
- **D-10:** `mote auth notebooklm` added as subcommand under existing `auth` group (alongside `google`). Shows status when already authenticated, offers re-auth.

### Claude's Discretion
- Exact cookie extraction mechanism (direct Chrome cookie DB read vs notebooklm-py's built-in method)
- Session credential storage format (mirror notebooklm-py's internal format or normalize)
- Whether `mote upload` command should also support NotebookLM as a target (or only auto-upload)
- Notebook naming convention and whether it's configurable

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INT-05 | User can upload transcripts to NotebookLM via `mote auth notebooklm` (experimental — unofficial API via notebooklm-py, sessions expire weekly) | notebooklm-py v0.3.4 is active (last commit 2026-03-12); `add_text()` API confirmed; async client pattern documented; session expiry detection mapped to RPCError pattern |
</phase_requirements>

---

## Summary

**Viability gate resolved (D-01): PROCEED with code implementation.** notebooklm-py is actively maintained — v0.3.4 released 2026-03-12, 8.2k GitHub stars, 11 open issues, last commit 17 days ago. The library provides a stable Python async API with `client.sources.add_text()` for uploading markdown content and `client.notebooks.create()` / `client.notebooks.list()` for notebook management. The library uses Playwright-based browser login for cookie extraction, storing session state in `~/.notebooklm/storage_state.json`.

The key implementation divergence from CONTEXT.md D-02 ("cookie extraction from Chrome's cookie store") is that notebooklm-py does NOT read from Chrome's SQLite cookie database directly. It runs a Playwright-controlled Chromium browser for the login flow, which captures and persists Google session cookies. This is actually better UX — the user sees a real browser window with Google's login UI including 2FA. The mote auth flow should invoke `notebooklm login` (or the equivalent Python API call) rather than reading Chrome's sqlite database.

Session credential storage needs a bridging decision: notebooklm-py stores its cookies at `~/.notebooklm/storage_state.json` by default. The simplest approach is to store the path to this file (or a custom path) in `~/.mote/notebooklm_session.json` rather than copying the cookies — this avoids stale copies and lets notebooklm-py manage its own session state. Alternatively, pass `--storage ~/.mote/notebooklm_session.json` to the login command to co-locate everything under `~/.mote/`.

**Primary recommendation:** Use notebooklm-py's Python async API with `asyncio.run()` wrapper in the upload function. Store session at `~/.mote/notebooklm_session.json` by passing a custom storage path to the login command. Cache notebook ID in the session file alongside the storage_state content (mirroring Drive's folder_id caching in google_token.json).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| notebooklm-py | 0.3.4 | NotebookLM API client | Only viable unofficial Python library; 8.2k stars; actively maintained; supports async text/file upload |
| notebooklm-py[browser] | 0.3.4 | Playwright browser login | Required extra for `notebooklm login`; installs Playwright + Chromium |
| asyncio | stdlib | Async wrapper | notebooklm-py is fully async; use `asyncio.run()` to call from sync Click commands |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| playwright (transitive) | latest | Browser automation for login | Pulled in by notebooklm-py[browser]; only needed at auth time, not upload time |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| notebooklm-py | Raw Playwright script | No benefit; notebooklm-py already wraps Playwright and provides the API abstraction |
| notebooklm-py | pynotebooklm | Less popular (fewer stars), less documentation; no clear advantage |
| notebooklm-py | Manual Chrome cookie extraction | Fragile (OS/Chrome version dependent), requires decryption; notebooklm-py's Playwright flow is cleaner |

**Installation:**
```bash
pip install "notebooklm-py[browser]"
playwright install chromium
```

Add to pyproject.toml dependencies:
```toml
"notebooklm-py[browser]>=0.3.4",
```

**Version verification (confirmed 2026-03-29):** notebooklm-py 0.3.4 on PyPI, published 2026-03-12.

---

## Architecture Patterns

### Recommended Project Structure

New module at `src/mote/notebooklm.py` following the exact `drive.py` pattern:

```
src/mote/
├── notebooklm.py        # New module: NotebookLM wrapper functions
├── drive.py             # Existing: mirror this pattern exactly
├── cli.py               # Extend: auth group + _run_transcription + --destination choice
└── config.py            # Extend: _write_default_config() + [destinations.notebooklm]
```

### Pattern 1: Session File Layout

The session file at `~/.mote/notebooklm_session.json` should store:
1. Path to (or embedded content of) the notebooklm-py storage_state — OR use `--storage ~/.mote/notebooklm_session.json` with the notebooklm login command so the storage_state is written directly there
2. Cached notebook ID alongside the session content (mirrors Drive's `drive_folder_id` in `google_token.json`)

Recommended: pass `storage_path = config_dir / "notebooklm_session.json"` to notebooklm-py so the library writes its cookies directly to the mote config dir. Then embed `notebook_id` in the same JSON file at save time.

```python
# Source: notebooklm-py docs/python-api.md
import json
from pathlib import Path

SESSION_FILE = "notebooklm_session.json"

def get_session_path(config_dir: Path) -> Path:
    return config_dir / SESSION_FILE

def _load_notebook_id(session_path: Path) -> str | None:
    if not session_path.exists():
        return None
    data = json.loads(session_path.read_text())
    return data.get("notebook_id")

def _save_notebook_id(session_path: Path, notebook_id: str) -> None:
    data = json.loads(session_path.read_text())
    data["notebook_id"] = notebook_id
    session_path.write_text(json.dumps(data))
    session_path.chmod(0o600)
```

### Pattern 2: Async Client Usage

notebooklm-py is fully async. Use `asyncio.run()` to bridge sync Click commands:

```python
# Source: notebooklm-py docs/python-api.md
import asyncio
from notebooklm import NotebookLMClient

async def _upload_source(session_path: Path, notebook_id: str, title: str, content: str) -> None:
    async with await NotebookLMClient.from_storage(str(session_path)) as client:
        await client.sources.add_text(notebook_id, title, content)

def upload_to_notebooklm(session_path: Path, notebook_id: str, title: str, content: str) -> None:
    asyncio.run(_upload_source(session_path, notebook_id, title, content))
```

### Pattern 3: Notebook Get-or-Create

```python
# Source: notebooklm-py docs/python-api.md
async def _get_or_create_notebook(client, notebook_name: str) -> str:
    notebooks = await client.notebooks.list()
    for nb in notebooks:
        if nb.title == notebook_name:
            return nb.id
    nb = await client.notebooks.create(notebook_name)
    return nb.id
```

### Pattern 4: auth notebooklm Command (mirrors auth_google)

```python
# Mirrors cli.py auth_google pattern
@auth.command("notebooklm")
def auth_notebooklm():
    """Authenticate with NotebookLM (Playwright browser flow)."""
    import subprocess
    from mote.notebooklm import get_session_path

    config_dir = get_config_dir()
    session_path = get_session_path(config_dir)

    if session_path.exists():
        click.echo(f"NotebookLM: session file exists at {session_path}")
        if not click.confirm("Re-authenticate?", default=False):
            return

    # Invoke notebooklm login with custom storage path
    result = subprocess.run(
        ["notebooklm", "login", "--storage", str(session_path)],
        check=False,
    )
    if result.returncode != 0:
        raise click.ClickException("NotebookLM login failed.")
    session_path.chmod(0o600)
    click.echo(f"NotebookLM session stored at {session_path}")
```

### Pattern 5: _run_transcription() Extension

Add NotebookLM block after Drive block, same try/except warning pattern:

```python
# In _run_transcription() after Drive block
if "notebooklm" in active_destinations:
    try:
        from mote.notebooklm import upload_transcript
        effective_config_dir = config_dir or get_config_dir()
        notebook_name = (cfg or {}).get("destinations", {}).get("notebooklm", {}).get("notebook_name", "Mote Transcripts")
        upload_transcript(effective_config_dir, written, notebook_name)
    except Exception as e:
        click.echo(
            f"Warning: NotebookLM upload failed: {e}. "
            "Transcripts saved locally. Run 'mote auth notebooklm' if session expired."
        )
```

### Pattern 6: config.py Extension

```python
# In _write_default_config(), after destinations_drive block
destinations_notebooklm = tomlkit.table()
destinations_notebooklm.add(tomlkit.comment("NotebookLM notebook name for uploads (experimental)"))
destinations_notebooklm.add("notebook_name", "Mote Transcripts")
destinations["notebooklm"] = destinations_notebooklm

# Update active destinations comment
destinations.add(tomlkit.comment("Active destinations: local, drive, notebooklm"))
```

### Anti-Patterns to Avoid

- **Synchronous blocking in async context:** Never call `asyncio.run()` from inside an already-running event loop. The Click CLI has no event loop, so `asyncio.run()` is safe and correct.
- **Storing cookies redundantly:** Do not copy the storage_state.json to a second location. Point notebooklm-py at `~/.mote/notebooklm_session.json` via `--storage` so there is one source of truth.
- **Proactive session checks:** D-08 is explicit — no pre-flight auth validation. Let the upload fail, catch the exception, surface a warning.
- **Raising on NotebookLM failure:** D-09 is absolute — NotebookLM failures are warnings, never exceptions that propagate to the caller.
- **Importing notebooklm at module level:** Use lazy imports inside function bodies (same as Phase 4 transcribe.py and Phase 8 drive.py). notebooklm-py is an optional heavy dependency.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NotebookLM API communication | Custom HTTP RPC client | notebooklm-py client | Undocumented Google RPC API with CSRF token management and automatic retry — not worth reverse engineering |
| Browser login flow | Custom Playwright script | `notebooklm login --storage <path>` | notebooklm-py already handles Google's 2FA, SSO, and persistent Chromium profile |
| CSRF token management | Manual token extraction | NotebookLMClient.from_storage() | Client handles automatic CSRF refresh transparently |
| Session expiry detection | Parse cookie timestamps | Catch RPCError from client calls | Library raises RPCError on auth failures; catching Exception covers all cases |
| Async-to-sync bridging | threading or concurrent.futures | asyncio.run() | asyncio.run() is the standard Python bridge; no extra deps |

**Key insight:** The RPC protocol is undocumented and complex. notebooklm-py is the only viable abstraction. Any custom implementation would be immediately fragile.

---

## Common Pitfalls

### Pitfall 1: Playwright Not Installed

**What goes wrong:** `notebooklm-py[browser]` requires `playwright install chromium` to be run after installation. If missing, `notebooklm login` fails with a cryptic Playwright error, not a user-friendly message.

**Why it happens:** Playwright downloads browser binaries separately from the Python package.

**How to avoid:** Add a `playwright install chromium` step to the Makefile setup target and document it in the auth command output. The `mote auth notebooklm` command should check for the chromium binary and print an install hint if absent.

**Warning signs:** `playwright._impl._errors.Error: Executable doesn't exist` during login.

### Pitfall 2: Session File Permissions After notebooklm Login

**What goes wrong:** `notebooklm login --storage ~/.mote/notebooklm_session.json` creates the file but may not set 600 permissions (notebooklm-py controls the write). A subsequent chmod call from mote is needed.

**Why it happens:** notebooklm-py manages its own file writes; it may use default OS permissions (644).

**How to avoid:** Always call `session_path.chmod(0o600)` in `auth_notebooklm` immediately after the login subprocess completes, before returning to the user.

### Pitfall 3: asyncio.run() Event Loop Conflict

**What goes wrong:** If anything else in the call stack creates an event loop before `upload_transcript` is called, `asyncio.run()` raises `RuntimeError: This event loop is already running`.

**Why it happens:** asyncio.run() cannot be nested.

**How to avoid:** In the Mote context, Click commands run synchronously with no event loop — `asyncio.run()` is safe. The pitfall is theoretical unless a future async refactor is done. Document this constraint explicitly.

### Pitfall 4: Notebook ID Cache Stale After Manual Deletion

**What goes wrong:** User manually deletes the "Mote Transcripts" notebook in NotebookLM UI. Cached notebook_id in session file is now invalid. Next upload gets an RPCError (invalid notebook ID).

**Why it happens:** Same as Drive's folder_id caching problem — the cache can become invalid externally.

**How to avoid:** On RPCError during upload, invalidate the cached notebook_id and retry with get-or-create. Add this retry logic to `upload_transcript()`.

### Pitfall 5: add_text() Source Title Uniqueness

**What goes wrong:** NotebookLM may reject or duplicate sources with identical titles. If the same transcript is uploaded twice (retry scenario), you get duplicate sources.

**Why it happens:** NotebookLM does not enforce source title uniqueness; `add_text()` always creates a new source.

**How to avoid:** Use the timestamped filename as the source title (e.g., `"2026-03-29-standup"` from the .md filename stem). Timestamps are unique by construction.

### Pitfall 6: Large Markdown Files

**What goes wrong:** Very long meetings produce large .md files. `add_text()` may fail or truncate above a certain text size limit (not documented by Google/notebooklm-py).

**Why it happens:** NotebookLM has undocumented source size limits.

**How to avoid:** NotebookLM's web UI accepts files up to 500,000 words per source. For a transcription tool at 1.9 MB/min audio → ~150 words/min, even a 3-hour meeting is ~27,000 words. Well within limits. Document limit but do not add chunking complexity.

---

## Code Examples

### Complete notebooklm.py module skeleton

```python
# Source: notebooklm-py docs/python-api.md, following drive.py pattern
"""NotebookLM API wrapper for Mote transcript uploads (experimental)."""

import asyncio
import json
from pathlib import Path

SESSION_FILE = "notebooklm_session.json"


def get_session_path(config_dir: Path) -> Path:
    """Return path to NotebookLM session file."""
    return config_dir / SESSION_FILE


def is_authenticated(config_dir: Path) -> bool:
    """Return True if session file exists (does not validate session)."""
    return get_session_path(config_dir).exists()


def run_login(session_path: Path) -> None:
    """Invoke notebooklm login with custom storage path.

    Raises RuntimeError if login command fails.
    """
    import subprocess
    result = subprocess.run(
        ["notebooklm", "login", "--storage", str(session_path)],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("NotebookLM login failed. Try running 'notebooklm login' manually.")
    session_path.chmod(0o600)


def _load_notebook_id(session_path: Path) -> str | None:
    """Read cached notebook ID from session file."""
    if not session_path.exists():
        return None
    try:
        data = json.loads(session_path.read_text())
        return data.get("notebook_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_notebook_id(session_path: Path, notebook_id: str) -> None:
    """Embed notebook_id in existing session file."""
    data = json.loads(session_path.read_text())
    data["notebook_id"] = notebook_id
    session_path.write_text(json.dumps(data))
    session_path.chmod(0o600)


async def _get_or_create_notebook(client, notebook_name: str) -> str:
    """Return notebook ID by name, creating if absent."""
    notebooks = await client.notebooks.list()
    for nb in notebooks:
        if nb.title == notebook_name:
            return nb.id
    nb = await client.notebooks.create(notebook_name)
    return nb.id


async def _upload_async(session_path: Path, notebook_name: str, title: str, content: str) -> None:
    """Async inner: get/create notebook and upload text source."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage(str(session_path)) as client:
        notebook_id = _load_notebook_id(session_path)
        if not notebook_id:
            notebook_id = await _get_or_create_notebook(client, notebook_name)
            _save_notebook_id(session_path, notebook_id)
        try:
            await client.sources.add_text(notebook_id, title, content)
        except Exception:
            # Notebook ID may be stale — retry with fresh lookup
            notebook_id = await _get_or_create_notebook(client, notebook_name)
            _save_notebook_id(session_path, notebook_id)
            await client.sources.add_text(notebook_id, title, content)


def upload_transcript(config_dir: Path, files: list[Path], notebook_name: str) -> None:
    """Upload markdown transcript to NotebookLM.

    Only uploads the .md file (D-06). Raises RuntimeError if not authenticated.
    """
    session_path = get_session_path(config_dir)
    if not session_path.exists():
        raise RuntimeError(
            "Not authenticated with NotebookLM. Run: mote auth notebooklm"
        )

    md_files = [f for f in files if f.suffix == ".md"]
    if not md_files:
        return  # No markdown file in this upload set — silent no-op

    for md_file in md_files:
        title = md_file.stem  # e.g. "2026-03-29-standup"
        content = md_file.read_text()
        asyncio.run(_upload_async(session_path, notebook_name, title, content))
```

### _run_transcription() addition in cli.py

```python
# After Drive upload block in _run_transcription()
if "notebooklm" in active_destinations:
    try:
        from mote.notebooklm import upload_transcript
        effective_config_dir = config_dir or get_config_dir()
        notebook_name = (
            (cfg or {})
            .get("destinations", {})
            .get("notebooklm", {})
            .get("notebook_name", "Mote Transcripts")
        )
        upload_transcript(effective_config_dir, written, notebook_name)
    except Exception as e:
        click.echo(
            f"Warning: NotebookLM upload failed: {e}. "
            "Run 'mote auth notebooklm' if session expired."
        )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Chrome cookie DB direct read (sqlite3 + keychain decryption) | Playwright persistent browser profile | notebooklm-py from initial release | Simpler auth UX; no keychain access required; supports 2FA naturally |
| Manual Google RPC reverse engineering | notebooklm-py library | Jan 2025 | CSRF token refresh, error handling, session management handled by library |
| Session stored separately from library | Use `--storage` to direct library to write directly to `~/.mote/` | notebooklm-py 0.3.x | Single source of truth for session data |

**Deprecated/outdated:**
- Direct Chrome cookie DB extraction: Requires `keyring`/`cryptography` libraries and macOS Keychain access for cookie decryption; notebooklm-py's Playwright flow avoids this entirely.

---

## Open Questions

1. **notebooklm-py import name**
   - What we know: Package installs as `notebooklm-py` on PyPI
   - What's unclear: The Python import name inside the package — whether it's `import notebooklm` or `from notebooklm_py import ...`
   - Recommendation: Verify with `python -c "import notebooklm; print(notebooklm.__version__)"` in Wave 0 task before writing notebooklm.py module. The code examples above use `from notebooklm import NotebookLMClient` based on the docs API examples — confirm this is correct.

2. **RPCError import path**
   - What we know: Library raises `RPCError` for API failures
   - What's unclear: Full import path for exception class
   - Recommendation: Check `from notebooklm.exceptions import RPCError` or `from notebooklm import RPCError` in Wave 0. For now, catching `Exception` is safe per project pattern.

3. **Notebook list() response shape**
   - What we know: `client.notebooks.list()` returns a list of notebook objects with `.id` and `.title` attributes
   - What's unclear: Exact attribute names confirmed only from docs, not tested against live API
   - Recommendation: The Wave 0 auth check task should verify the response shape by running a list() call after login.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | ✓ | 3.13 (venv) | — |
| notebooklm-py | New module | ✗ | — (not yet installed) | N/A — this is the feature |
| playwright chromium | notebooklm login | ✗ | — (not yet installed) | N/A — required for auth |
| asyncio | Async wrapper | ✓ | stdlib | — |

**Missing dependencies with no fallback:**
- `notebooklm-py[browser]` — must be added to pyproject.toml and installed
- Chromium binaries — must be installed via `playwright install chromium` after package install

**Missing dependencies with fallback:** None.

**Note on Makefile:** Add `playwright install chromium` to the `setup` or `install` target in the Makefile so new installs get the browser binary automatically.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_notebooklm.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INT-05 | `get_session_path()` returns `~/.mote/notebooklm_session.json` | unit | `pytest tests/test_notebooklm.py::test_get_session_path -x` | ❌ Wave 0 |
| INT-05 | `is_authenticated()` returns False when session file absent | unit | `pytest tests/test_notebooklm.py::test_is_authenticated_no_file -x` | ❌ Wave 0 |
| INT-05 | `upload_transcript()` raises RuntimeError when session file absent | unit | `pytest tests/test_notebooklm.py::test_upload_raises_when_not_authenticated -x` | ❌ Wave 0 |
| INT-05 | `upload_transcript()` calls `add_text` with .md content (not .txt) | unit | `pytest tests/test_notebooklm.py::test_upload_uses_md_only -x` | ❌ Wave 0 |
| INT-05 | `upload_transcript()` caches notebook_id after first get-or-create | unit | `pytest tests/test_notebooklm.py::test_upload_caches_notebook_id -x` | ❌ Wave 0 |
| INT-05 | `upload_transcript()` retries get-or-create on stale notebook_id | unit | `pytest tests/test_notebooklm.py::test_upload_retries_on_stale_notebook_id -x` | ❌ Wave 0 |
| INT-05 | `_run_transcription()` calls upload_transcript when "notebooklm" in destinations | unit | `pytest tests/test_cli.py::test_run_transcription_notebooklm_destination -x` | ❌ Wave 0 |
| INT-05 | `_run_transcription()` catches NotebookLM exception, prints warning, does not raise | unit | `pytest tests/test_cli.py::test_run_transcription_notebooklm_failure_is_warning -x` | ❌ Wave 0 |
| INT-05 | Default config includes `[destinations.notebooklm]` section | unit | `pytest tests/test_config.py::test_default_config_has_notebooklm_section -x` | ❌ Wave 0 |
| INT-05 | `mote auth notebooklm` — shows status when already authenticated | integration (mocked subprocess) | `pytest tests/test_cli.py::test_auth_notebooklm_already_authenticated -x` | ❌ Wave 0 |
| INT-05 | Session expiry message displayed on upload failure | unit | `pytest tests/test_cli.py::test_notebooklm_session_expired_warning -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_notebooklm.py tests/test_cli.py tests/test_config.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_notebooklm.py` — all notebooklm module unit tests (new file)
- [ ] Additional test cases in `tests/test_cli.py` — auth_notebooklm, _run_transcription notebooklm block
- [ ] Additional test cases in `tests/test_config.py` — default config notebooklm section

*(Existing test infrastructure covers framework setup — only new test files/cases needed)*

---

## Project Constraints (from CLAUDE.md)

- Python 3.11+ runtime
- All dependencies declared in pyproject.toml
- Lazy imports for heavy dependencies inside function bodies
- `~/.mote/` config dir; session files with chmod 0o600
- Function-based modules, no classes
- Destination errors are warnings not failures
- Mock-heavy testing for external service calls
- Click CLI, no async framework at CLI layer (use `asyncio.run()` for bridge)
- No Flask-SSE, no Redis, no threading for I/O

**New constraint from notebooklm-py:** `playwright install chromium` must be a documented post-install step. The package itself cannot auto-install browser binaries via pip.

---

## Sources

### Primary (HIGH confidence)
- [teng-lin/notebooklm-py GitHub](https://github.com/teng-lin/notebooklm-py) — viability check: v0.3.4 active, 8.2k stars, last commit 2026-03-12
- [notebooklm-py docs/python-api.md](https://github.com/teng-lin/notebooklm-py/blob/main/docs/python-api.md) — NotebookLMClient API, authentication patterns, add_text/add_file, async usage
- [notebooklm-py docs/configuration.md](https://github.com/teng-lin/notebooklm-py/blob/main/docs/configuration.md) — storage paths, env vars, --storage flag
- [notebooklm-py docs/troubleshooting.md](https://github.com/teng-lin/notebooklm-py/blob/main/docs/troubleshooting.md) — session expiry, RPCError, re-auth steps
- [notebooklm-py PyPI](https://pypi.org/project/notebooklm-py/) — v0.3.4 confirmed, Python >=3.10
- `src/mote/drive.py` — existing pattern to mirror exactly
- `src/mote/cli.py` — existing auth group, _run_transcription(), --destination flag

### Secondary (MEDIUM confidence)
- [WebSearch: notebooklm-py library status 2026](https://github.com/teng-lin/notebooklm-py/releases) — 8.2k stars, 1k forks independently confirmed

### Tertiary (LOW confidence)
- None applicable

---

## Metadata

**Confidence breakdown:**
- Viability gate (D-01): HIGH — library confirmed active, v0.3.4 released 2026-03-12
- Standard stack: HIGH — notebooklm-py is the clear single choice; version verified on PyPI
- Architecture: HIGH — pattern is a direct mirror of drive.py which is already implemented
- API calls (add_text, notebooks.list, notebooks.create): HIGH — verified from official docs
- Session expiry detection: HIGH — RPCError pattern documented in troubleshooting guide
- Playwright install requirement: HIGH — Playwright browser binary install is documented requirement
- Import name verification: MEDIUM — docs use `from notebooklm import NotebookLMClient` but not tested against installed package

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (notebooklm-py uses undocumented APIs; recheck if Google makes breaking changes)
