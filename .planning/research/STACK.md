# Stack Research

**Domain:** macOS meeting transcription tool — Swedish/Scandinavian focus
**Researched:** 2026-03-27
**Confidence:** HIGH (all core components verified against current official sources or PyPI)

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

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Virtualenv + dependency management | Faster than pip for dev iteration; `uv pip install -e .` for editable installs |
| hatchling | Build backend | Declared in `[build-system]` in pyproject.toml; enables `pip install git+https://github.com/...` |
| ruff | Linting + formatting | Replaces flake8 + black + isort in one tool; fast, zero-config |
| pytest | Testing | Standard; pair with `pytest-tmp-path` for audio fixture cleanup |

---

## Installation

```bash
# User install from GitHub
pip install git+https://github.com/USERNAME/mote.git

# System dependency (not pip-installable)
brew install blackhole-2ch

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
    "openai>=2.0",       # optional engine
    "mistralai>=2.0.1",  # optional engine
]
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| sounddevice | PyAudio | If you need stream callback control with byte-level precision; PyAudio is more complex to install (PortAudio brew dep) and its bytes-based API requires manual WAV packing |
| sounddevice | pyaudio + portaudio brew | Never for this project — sounddevice bundles PortAudio via pip, reducing install friction |
| Flask | FastAPI | If you need async I/O or OpenAPI docs; overkill for a single-user localhost tool with SSE and template pages |
| Flask | Quart | If async becomes necessary (e.g., concurrent transcription + recording); Quart is Flask-compatible async alternative |
| tomlkit | tomllib (stdlib) | tomllib is read-only; use it only if you never need to write config. Since Möte writes config from settings UI, tomlkit is required |
| hatchling | setuptools | setuptools is fine but requires more boilerplate; hatchling is zero-config for pure-Python packages |
| nativemessaging-ng | Raw stdin/stdout | Acceptable if you want zero extra deps; nativemessaging-ng just handles the 4-byte length-prefixed framing and manifest install CLI |
| faster-whisper | whisper.cpp | whisper.cpp has no Python-native API — you'd shell-exec it; faster-whisper integrates directly and handles KBLab models natively |
| faster-whisper | WhisperX | WhisperX builds on faster-whisper and adds diarization (out of scope); adds deps without benefit for this project |
| KBLab kb-whisper-large | openai/whisper-large-v3 | Use OpenAI's model only if KBLab is unavailable; KBLab is 47% lower WER on Swedish, same model API |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Mistral Voxtral for Swedish | Swedish is NOT in Voxtral's documented 13-language support list (English, Spanish, French, Portuguese, Hindi, German, Dutch, Italian, etc.). Including it as the primary Swedish engine will produce poor results. | KBLab kb-whisper via faster-whisper as primary; OpenAI whisper-1 as secondary |
| Flask-SSE (pip package) | Requires Redis as pubsub backend — massively over-engineered for a single-user tool. | Plain Flask streaming response: `Response(generator(), mimetype="text/event-stream")` — no extra dependencies |
| oauth2client | Deprecated since 2019; Google no longer recommends it. | `google-auth` + `google-auth-oauthlib` |
| openai-whisper (the original pip package) | CPU-only, slow, no CTranslate2 acceleration; can't use KBLab ctranslate2 format directly. | faster-whisper |
| PyAudio | Harder to install (requires separate PortAudio brew step, prone to macOS permission issues), bytes-based API. | sounddevice (bundles PortAudio, NumPy-native) |
| threading for audio + transcription | Python GIL contention. Use subprocess isolation or — better — sequential record-then-transcribe which matches the project's batch-only design. | Sequential: record to WAV, then transcribe WAV after stop |
| tomllib (stdlib) for config | Read-only; cannot write config values. | tomlkit |
| YAML for config | No stdlib support, extra dep (pyyaml), less readable for non-developers. | TOML via tomlkit |

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

---

*Stack research for: Möte — macOS Swedish meeting transcription tool*
*Researched: 2026-03-27*
