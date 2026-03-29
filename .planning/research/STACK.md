# Stack Research

**Domain:** macOS meeting transcription tool — Swedish/Scandinavian focus
**Researched:** 2026-03-27 (v1) · updated 2026-03-28 (v2.0 additions)
**Confidence:** HIGH for all v1 components and Drive OAuth pattern; MEDIUM for notebooklm-py (unofficial API, inherently fragile); MEDIUM for SwitchAudioSource (brew-only, not pip-installable)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | tomllib stdlib (no tomli dep), standard enough that `pip install` from GitHub is frictionless; 3.11 is the minimum that ships tomllib |
| faster-whisper | 1.2.1 | Local transcription engine | CTranslate2 backend, 4x faster than openai/whisper at same WER, directly accepts KBLab ctranslate2-format models by Hugging Face model ID — no format conversion needed |
| sounddevice | 0.5.5 | Audio capture from BlackHole | NumPy-native API, simpler than PyAudio, works with PortAudio/Core Audio on macOS, cleaner device enumeration; the standard choice for BlackHole-via-Python patterns |
| Click | 8.3.0 | CLI framework | Composable command structure, decorator-based, clean help generation; the established standard for Python CLI tools with no heavy framework overhead |
| Flask | 3.1.3 | Web UI server | Built-in streaming response for SSE without Redis dependency, Jinja2 templates for UI, minimal overhead for a single-user localhost tool; FastAPI adds complexity with no benefit here |
| hatchling | latest | Build backend | `pyproject.toml`-native, pip-installable from GitHub, zero-config for pure-Python packages; the recommended backend for `pip install git+https://...` distribution |

### Transcription Engines

| Engine | Library | Version | Swedish Support | Notes |
|--------|---------|---------|----------------|-------|
| KBLab local (primary) | faster-whisper | 1.2.1 | Native — 47% lower WER than whisper-large-v3 on Swedish | Load via `WhisperModel("KBLab/kb-whisper-large")`, ctranslate2 format on HuggingFace; 5 sizes: tiny/base/small/medium/large |
| OpenAI Whisper API (fallback) | openai | 2.29.0 | Good — multilingual | `client.audio.transcriptions.create(model="whisper-1")`; 25MB file limit; `gpt-4o-transcribe` also available |
| Mistral Voxtral (fallback) | mistralai | 2.0.1 | LOW confidence — Swedish NOT in documented 13-language list | Do not rely on Voxtral for Swedish; include as optional engine but document the limitation clearly |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 2.x | Audio buffer handling | Required by sounddevice for WAV array recording; always |
| tomlkit | 0.13.x | TOML config read + write | Use tomlkit (not tomllib) because config needs both reading and writing; tomlkit preserves comments and formatting when updating values |
| google-api-python-client | 2.193.0 | Google Drive API v3 calls | Upload transcripts to Drive; use with google-auth-oauthlib for OAuth2 installed-app flow |
| google-auth-oauthlib | 1.x | OAuth2 browser flow for Drive | Handles the consent screen + token storage pattern for a locally-installed app |
| google-auth | 2.38.0 | Token refresh | Dependency of the above; handles credential refresh automatically |
| nativemessaging-ng | 1.3.3 | Chrome extension native messaging | Handles stdin/stdout message framing (4-byte length prefix) between Chrome extension and Python host; installs browser manifest via CLI; actively maintained |
| rich | 13.x | CLI output formatting | Progress bars for transcription, styled status output; optional but makes the CLI significantly more usable |
| notebooklm-py | 0.3.4 | NotebookLM source upload | Unofficial Python API for Google NotebookLM; v2.0 only. Install with `[browser]` extra for first-time auth, base install for subsequent runs. Treat as best-effort — Google can break the undocumented API it wraps at any time |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Virtualenv + dependency management | Faster than pip for dev iteration; `uv pip install -e .` for editable installs |
| hatchling | Build backend | Declared in `[build-system]` in pyproject.toml; enables `pip install git+https://github.com/...` |
| ruff | Linting + formatting | Replaces flake8 + black + isort in one tool; fast, zero-config |
| pytest | Testing | Standard; pair with `pytest-tmp-path` for audio fixture cleanup |

---

## v2.0 Additions — What's New

### NotebookLM Integration (INT-05)

**Library:** `notebooklm-py` 0.3.4 (released 2026-03-12)
**PyPI:** https://pypi.org/project/notebooklm-py/
**GitHub:** https://github.com/teng-lin/notebooklm-py

**Install:**
```bash
# First-time setup on a machine where browser auth is needed:
pip install "notebooklm-py[browser]"
playwright install chromium

# Subsequent installs (token already stored from first login):
pip install notebooklm-py
```

**Authentication flow:**
1. `notebooklm login` — opens browser for Google OAuth consent; stores cookies locally
2. `notebooklm auth check --test` — validates stored credentials
3. Subsequent calls use stored cookies; no browser required until cookies expire

**Key API pattern:**
```python
from notebooklm_py import NotebookLMClient

client = NotebookLMClient.from_storage()  # loads stored cookies
notebook = await client.notebooks.get(notebook_id)
await client.sources.add_file(notebook_id, file_path="transcript.md")
```

**`mote auth notebooklm` command:** shell out to `notebooklm login` or call the library's browser flow directly. Store `notebook_id` in `~/.mote/config.toml` under `[destinations.notebooklm]`.

**Critical caveat (MEDIUM confidence):** This wraps undocumented Google APIs. Tested as of March 2026 (0.3.4), but Google can break the internal endpoints without notice. The library explicitly states: "Best for prototypes, research, and personal projects." Design the NotebookLM destination as optional/gracefully-degrading — catch exceptions and log failures rather than hard-crashing.

**Playwright is a heavyweight dependency (~100MB for chromium binary).** It is only needed for the initial `notebooklm login` step. Do NOT add playwright to pyproject.toml `dependencies`. Document it as a one-time setup step. `notebooklm-py` (without `[browser]`) works fine once cookies are already stored, so the pip-installed tool stays lean.

---

### Auto-Switch BlackHole Audio Routing (AUD-05)

**Tool:** `SwitchAudioSource` (brew tool, not pip)
**Install:** `brew install switchaudio-osx`
**GitHub:** https://github.com/deweller/switchaudio-osx

**This is a macOS system tool, not a Python library.** Use Python's stdlib `subprocess` to call it. Do NOT add a Python wrapper library as a dependency.

**Pattern — save/restore audio output:**
```python
import subprocess

def get_current_output() -> str:
    result = subprocess.run(
        ["SwitchAudioSource", "-c", "-t", "output"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

def set_output(device_name: str) -> None:
    subprocess.run(
        ["SwitchAudioSource", "-s", device_name, "-t", "output"],
        check=True
    )
```

**Recording flow with auto-routing:**
```python
original = get_current_output()
try:
    set_output("BlackHole 2ch")
    record()
finally:
    set_output(original)  # always restore, even on Ctrl+C
```

**Handling missing `SwitchAudioSource`:** Check if the binary exists before recording. If absent, warn the user and skip auto-routing (manual routing only). Do not hard-fail — the tool is useful without auto-routing.

```python
import shutil

def switchaudio_available() -> bool:
    return shutil.which("SwitchAudioSource") is not None
```

**Installation note for README/docs:** `brew install switchaudio-osx` is a pre-requisite for AUD-05. It cannot be included in `pyproject.toml`. Add it to the installation instructions alongside `brew install blackhole-2ch`.

---

### Silence Detection (AUD-06)

**Library:** None needed — use `numpy` (already a dependency) and `sounddevice` (already a dependency).

**Pattern — RMS-based silence detection during recording:**
```python
import numpy as np

SILENCE_THRESHOLD_RMS = 0.005   # normalized 0.0–1.0; tune to taste
SILENCE_WARN_SECONDS = 10       # warn if silent for this many seconds

def compute_rms(audio_chunk: np.ndarray) -> float:
    """Returns normalized RMS energy of audio chunk."""
    return float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)))

# During sounddevice InputStream callback or periodic chunk check:
rms = compute_rms(chunk)
is_silent = rms < SILENCE_THRESHOLD_RMS
```

**Integration point:** During `mote record`, check RMS on each ~1-second audio chunk. If silence persists past `SILENCE_WARN_SECONDS`, print a Rich warning: "No audio signal detected on BlackHole 2ch — check your audio routing." Do not stop recording; it's a warning only.

**Confidence: HIGH** — this is standard numpy/signal processing, no external library required.

---

### Google Drive OAuth2 (INT-04)

**Libraries:** `google-api-python-client` 2.193.0 + `google-auth-oauthlib` 1.x (already in stack, validated in v1 research). The pattern below is the standard installed-app OAuth2 flow.

**`mote auth google` pattern:**
```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = Path.home() / ".mote" / "google_token.json"
CREDS_PATH = Path.home() / ".mote" / "google_credentials.json"  # user-provided OAuth client JSON

def get_drive_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
        TOKEN_PATH.chmod(0o600)
    return creds
```

**Key detail:** `google-auth-oauthlib` does NOT provide built-in token persistence. Use `creds.to_json()` / `Credentials.from_authorized_user_file()` to serialize/deserialize manually. This is the official pattern from Google's Drive quickstart docs.

**Scope:** Use `drive.file` (not `drive` or `drive.readonly`) — it grants access only to files created by the app, which is the minimum necessary scope for uploading transcripts.

**File upload pattern:**
```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_transcript(file_path: str, folder_id: str | None = None) -> str:
    creds = get_drive_credentials()
    service = build("drive", "v3", credentials=creds)
    metadata = {"name": Path(file_path).name}
    if folder_id:
        metadata["parents"] = [folder_id]
    media = MediaFileUpload(file_path, mimetype="text/markdown")
    file = service.files().create(body=metadata, media_body=media, fields="id").execute()
    return file["id"]
```

---

### JSON Output (INT-02)

**Library:** None — use Python stdlib `json`. No new dependency.

**Pattern:**
```python
import json
from dataclasses import dataclass, asdict

@dataclass
class TranscriptResult:
    text: str
    language: str
    engine: str
    duration_seconds: float
    segments: list[dict]   # [{start, end, text}]
    created_at: str        # ISO 8601

# Write:
Path(output_path).write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2))
```

**Integration:** Add `--format json` flag to `mote transcribe` and `mote record`. When JSON format is requested, write a `.json` file alongside (or instead of) the `.md` file. The `segments` field carries per-segment timestamps from faster-whisper's output, which is useful for downstream tools.

---

## Installation

```bash
# User install from GitHub
pip install git+https://github.com/USERNAME/mote.git

# System dependencies (not pip-installable)
brew install blackhole-2ch       # audio capture (required)
brew install switchaudio-osx     # auto audio routing (optional, for AUD-05)

# NotebookLM first-time auth setup (one-time, not in pyproject.toml)
pip install "notebooklm-py[browser]"
playwright install chromium
notebooklm login

# Dev install
uv venv && uv pip install -e ".[dev]"
```

```toml
# pyproject.toml — key sections
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mote"
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.2.1",
    "sounddevice>=0.5.5",
    "numpy>=2.0",
    "click>=8.3.0",
    "flask>=3.1.3",
    "tomlkit>=0.13",
    "google-api-python-client>=2.193",
    "google-auth-oauthlib>=1.0",
    "nativemessaging-ng>=1.3.3",
    "rich>=13.0",
    "openai>=2.0",           # optional engine
    "mistralai>=2.0.1",      # optional engine
    "notebooklm-py>=0.3.4",  # v2.0: NotebookLM destination
]
```

**Note:** `playwright` is NOT in `dependencies`. It is documented as a one-time setup step for `notebooklm login`. The base `notebooklm-py` package (without `[browser]`) works for all subsequent uploads once cookies are stored.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| sounddevice | PyAudio | Harder to install (PortAudio brew dep), bytes-based API requires manual WAV packing |
| Flask | FastAPI | Overkill for a single-user localhost tool with SSE and template pages |
| Flask | Quart | Only if async becomes necessary; currently not needed |
| tomlkit | tomllib (stdlib) | tomllib is read-only; Möte writes config |
| hatchling | setuptools | More boilerplate; hatchling is zero-config for pure-Python |
| nativemessaging-ng | Raw stdin/stdout | nativemessaging-ng adds 4-byte framing + manifest install CLI |
| faster-whisper | whisper.cpp | No Python-native API — would require shell-exec |
| faster-whisper | WhisperX | Adds diarization (out of scope), extra deps without benefit |
| subprocess SwitchAudioSource | pycaw or CoreAudio Python bindings | pycaw is Windows-only; raw CoreAudio bindings require ctypes and undocumented structs. SwitchAudioSource is the macOS standard CLI tool, well-maintained, trivially callable via subprocess |
| numpy RMS for silence detection | webrtcvad | webrtcvad is a C extension with non-trivial install; overkill for a "warn if silent" feature. numpy RMS is zero extra dependency |
| notebooklm-py | Playwright directly | notebooklm-py abstracts the API; writing raw Playwright automation against NotebookLM's DOM would be far more brittle |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Mistral Voxtral for Swedish | Swedish is NOT in Voxtral's 13-language support list. Primary engine will produce poor results. | KBLab kb-whisper via faster-whisper as primary; OpenAI whisper-1 as secondary |
| Flask-SSE (pip package) | Requires Redis — massively over-engineered for single-user tool | Plain Flask streaming response: `Response(generator(), mimetype="text/event-stream")` |
| oauth2client | Deprecated since 2019; Google no longer recommends it | `google-auth` + `google-auth-oauthlib` |
| openai-whisper (the original pip package) | CPU-only, slow, no CTranslate2 acceleration; can't use KBLab ctranslate2 format | faster-whisper |
| PyAudio | Harder to install, bytes-based API, macOS permission issues | sounddevice (bundles PortAudio, NumPy-native) |
| threading for audio + transcription | Python GIL contention | Sequential: record to WAV, then transcribe after stop |
| tomllib (stdlib) for config | Read-only; cannot write config values | tomlkit |
| YAML for config | No stdlib support, extra dep (pyyaml), less readable | TOML via tomlkit |
| playwright in pyproject.toml dependencies | ~100MB chromium binary pulled on every `pip install mote`; only needed once for `notebooklm login` | Document as a one-time setup step outside pyproject.toml |
| `drive` scope for Google OAuth | Over-privileged — grants full Drive access | `drive.file` scope: app can only see files it created |
| pycaw for audio device switching | Windows-only library | `subprocess` + `SwitchAudioSource` brew tool |

---

## Stack Patterns by Variant

**If running on Apple Silicon (M1/M2/M3):**
- Set `device="cpu"` and `compute_type="int8"` in WhisperModel — MPS (Metal) support in CTranslate2 is experimental as of v4.x; CPU with int8 quantization is more reliable
- `kb-whisper-medium` gives good speed/quality balance on M-series chips; `kb-whisper-large` is feasible but slower

**If running on Intel Mac:**
- Same device/compute_type recommendation (`cpu`, `int8`); no GPU path available
- `kb-whisper-small` may be preferable for interactive responsiveness

**If user chooses OpenAI Whisper API engine:**
- No local model management needed
- Must handle 25MB file size limit — split long recordings (WAV at 1.9MB/min means ~13 min max per chunk)
- Language detection is automatic; specify `language="sv"` to force Swedish and avoid misdetection

**If user chooses Mistral Voxtral engine:**
- Treat as English/multilingual fallback only; document clearly that Swedish is not officially supported
- Use `mistralai>=2.0.1`; SDK had breaking changes between v1 and v2
- Use `mistralai.Mistral` client with `client.audio.transcriptions.create()`

**For SSE (live status during transcription):**
- Use Flask streaming response, no extra package:
  ```python
  def event_stream():
      yield f"data: {json.dumps({'progress': pct})}\n\n"
  return Response(event_stream(), mimetype="text/event-stream")
  ```

**For Chrome extension native messaging host:**
- Register the Python script as a native messaging host via `nativemessaging-ng install --browser chrome`
- The manifest JSON must be placed at `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/`
- The extension communicates via `chrome.runtime.connectNative()`; the Python host reads/writes JSON over stdin/stdout

**For NotebookLM destination (v2.0):**
- Always wrap `notebooklm-py` calls in try/except; surface failures as warnings, not hard errors
- Store `notebook_id` in config, not hardcoded
- Design the destination as opt-in: only attempt upload if `[destinations.notebooklm]` is configured

**For Google Drive destination (v2.0):**
- Store token at `~/.mote/google_token.json` with chmod 600
- Store user-provided OAuth client JSON at `~/.mote/google_credentials.json`
- Use `drive.file` scope — minimum necessary privilege
- `mote auth google` runs the consent flow; all other commands call `get_drive_credentials()` which auto-refreshes

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| faster-whisper 1.2.1 | ctranslate2 >=4.0 | CTranslate2 4.x is pulled in automatically; CUDA 12 support added |
| KBLab/kb-whisper-* | faster-whisper >=1.0 | ctranslate2 format published on HuggingFace; load by repo ID directly |
| sounddevice 0.5.5 | numpy >=1.21 (numpy 2.x works) | NumPy 2.0 API changes don't affect sounddevice's usage patterns |
| Flask 3.1.3 | Python >=3.9 | No conflicts with other stack components |
| Click 8.3.0 | Python >=3.10 | Click dropped 3.7-3.9 support in 8.3.x |
| mistralai 2.0.1 | Python >=3.9 | Breaking changes vs v1; migration guide required if starting from scratch |
| google-api-python-client 2.193 | google-auth >=2.38 | These are released in lockstep; pip resolves correctly |
| notebooklm-py 0.3.4 | Python >=3.10 | Supports 3.10–3.14; `[browser]` extra requires `playwright install chromium` separately |
| SwitchAudioSource | macOS 10.7–11.2 tested | Works on macOS 12+ in practice; no Python version constraint (subprocess call) |

---

## Sources

- https://github.com/SYSTRAN/faster-whisper/releases — faster-whisper 1.2.1 confirmed (Oct 31, 2025)
- https://huggingface.co/KBLab/kb-whisper-large — KBLab model formats, ctranslate2 availability, 5 sizes, Stage 2 variants confirmed
- https://kb-labb.github.io/posts/2025-03-07-welcome-KB-Whisper/ — 47% WER reduction vs whisper-large-v3 on Swedish, 50K hours training data
- https://mistral.ai/news/voxtral — Voxtral language list (Swedish absent); confirmed 13 supported languages
- https://pypi.org/project/sounddevice/ — sounddevice 0.5.5 (Jan 23, 2026)
- https://pypi.org/project/click/ — Click 8.3.0 (Nov 15, 2025), Python >=3.10 required
- https://pypi.org/project/Flask/ — Flask 3.1.3 (Feb 19, 2026)
- https://pypi.org/project/openai/ — openai 2.29.0 (Mar 17, 2026)
- https://pypi.org/project/mistralai/ — mistralai 2.0.1 (Mar 12, 2026), breaking v1→v2 changes
- https://pypi.org/project/google-api-python-client/ — 2.193.0 (Mar 17, 2026)
- https://google-auth.readthedocs.io/ — google-auth 2.38.0, oauth2client deprecated
- https://github.com/roelderickx/nativemessaging-ng — nativemessaging-ng 1.3.3 (Feb 23, 2025), Chrome + Firefox, actively maintained
- https://python-sounddevice.readthedocs.io/en/latest/ — sounddevice 0.5.5 docs
- https://maxhalford.github.io/blog/flask-sse-no-deps/ — SSE without Redis pattern confirmed
- https://docs.astral.sh/uv/concepts/build-backend/ — hatchling as recommended build backend for pyproject.toml pip-installable packages
- https://pypi.org/project/tomlkit/ — tomlkit read+write with comment preservation (vs tomllib read-only stdlib)
- https://pypi.org/project/notebooklm-py/ — notebooklm-py 0.3.4 (Mar 12, 2026), Python >=3.10, unofficial Google API wrapper
- https://github.com/teng-lin/notebooklm-py — notebooklm-py source; authentication flow, cookie storage, unofficial API warning confirmed
- https://github.com/deweller/switchaudio-osx — SwitchAudioSource CLI tool; brew install, -c/-s/-t flags confirmed
- https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html — InstalledAppFlow.run_local_server pattern, drive.file scope recommendation

---

*Stack research for: Möte — macOS Swedish meeting transcription tool*
*Researched: 2026-03-27 (v1) · 2026-03-28 (v2.0 additions: notebooklm-py, SwitchAudioSource, silence detection, Drive OAuth pattern, JSON output)*
