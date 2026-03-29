# Project Research Summary

**Project:** Möte — macOS Swedish Meeting Transcription Tool
**Domain:** CLI tool for audio capture, local AI transcription, and cloud delivery
**Researched:** 2026-03-28 (v2.0 update; v1 research 2026-03-27)
**Confidence:** HIGH for Phases 1-3; MEDIUM for NotebookLM integration (Phase 4)

## Executive Summary

Möte is a macOS-only meeting transcription tool built around BlackHole virtual audio capture and KBLab's kb-whisper models — the only production-quality Swedish transcription models available, delivering 47% lower word error rate than the generic whisper-large-v3 baseline. The tool is now in its v2.0 Integration and Polish phase: v1 is complete with a working record-transcribe CLI pipeline, and v2.0 adds Google Drive delivery, auto audio routing, UX polish (retry flows, config validation), and optional NotebookLM upload. The architecture centers on a thin CLI layer over four stable modules (audio, transcribe, output, config), with a new `destinations/` subpackage for external delivery added in v2.

The recommended approach is sequential batch transcription — record to WAV, stop, transcribe — rather than streaming. This matches faster-whisper's design, avoids Python GIL contention, and produces clean output. The core pipeline is already built and proven. v2.0 changes are additive: new CLI commands, a new module, and extensions to existing modules. The build order matters: config validation and a `_run_transcription()` helper refactor must ship before destinations are wired, so both `record` and the new `transcribe` command share the delivery path without code duplication.

The key risks are not technical complexity but fragility at integration boundaries. Google Drive is stable and well-documented; its OAuth pitfalls are specific and avoidable with correct parameter choices. NotebookLM is fundamentally fragile — it wraps undocumented Google internals, sessions expire every 1-2 weeks, and Google can silently break it. The right mitigation is to make Drive the primary reliable path and NotebookLM a best-effort optional enhancement. Audio routing restore-on-crash is the other critical risk: a SIGKILL with BlackHole set as system output leaves the user with no sound; a recovery file written before the switch is the only protection.

## Key Findings

### Recommended Stack

The stack is fully resolved. Python 3.11+ with faster-whisper 1.2.1 and KBLab/kb-whisper models handles all transcription. sounddevice captures from BlackHole with a queue-based callback (never block the callback thread). Click 8.3.0 drives the CLI, Flask 3.1.3 serves the web UI with native SSE streaming. hatchling enables `pip install git+https://github.com/...` distribution. Config uses tomlkit (not stdlib tomllib) because the settings UI writes config values.

For v2.0, three additions: `google-api-python-client` + `google-auth-oauthlib` for Drive; `notebooklm-py` 0.3.4 for NotebookLM (unofficial API, treat as optional); `SwitchAudioSource` via `brew install switchaudio-osx` for auto audio routing (not pip-installable, must degrade gracefully). Silence detection requires no new deps — numpy RMS on existing sounddevice callback data.

**Core technologies:**
- faster-whisper 1.2.1: local transcription — CTranslate2 backend; only engine that natively loads KBLab ctranslate2 models
- KBLab/kb-whisper-{size}: primary Swedish model — 47% lower WER than generic whisper-large-v3; 5 sizes (tiny through large)
- sounddevice 0.5.5: BlackHole audio capture — NumPy-native, no separate PortAudio brew dep required
- Click 8.3.0: CLI framework — decorator-based, composable commands; Python 3.10+ required
- Flask 3.1.3: web UI server — native SSE streaming without Redis; single-user localhost tool
- tomlkit 0.13.x: TOML config — read and write with comment preservation (stdlib tomllib is read-only)
- google-api-python-client 2.193.0: Drive API v3 upload with InstalledAppFlow OAuth2
- notebooklm-py 0.3.4: NotebookLM source upload — unofficial API, best-effort only; do not make mandatory

**Avoid:** Mistral Voxtral as Swedish engine (Swedish not in confirmed 13-language list), Flask-SSE pip package (requires Redis), oauth2client (deprecated 2019), openai-whisper original package (CPU-only, no CTranslate2), PyAudio (harder install, bytes-based API), threading for concurrent audio + transcription (GIL contention), playwright in pyproject.toml (100MB binary; only needed once for notebooklm login).

### Expected Features

v1 is complete. v2.0 adds integration and polish features that build on the existing pipeline without restructuring it.

**Must have (table stakes) for v2.0:**
- `mote transcribe <file>` — power users expect to re-transcribe files; reuses all existing transcription logic
- Config validation on startup — fail fast before recording with actionable error messages; must not break existing v1 configs
- Retry failed transcription — WAV is already kept on failure; interactive prompt completes the loop
- Orphaned WAV offer on startup — detection already exists; only the prompt and transcription loop are new
- JSON output format — zero new deps; enables downstream automation and NotebookLM uploads
- Google Drive upload + `mote auth google` — primary integration value; closes the capture-to-Drive workflow
- Configurable destinations config section — enables Drive and future destinations
- Silence detection warning — RMS-based, ~10 lines in existing callback; catches routing misconfiguration early

**Should have for v2.0:**
- Auto-switch BlackHole routing — eliminates the biggest setup friction point; must degrade gracefully when SwitchAudioSource absent

**Defer to v2.1 or later:**
- NotebookLM upload via notebooklm-py — fragile unofficial API, Playwright dep; Google Drive is the reliable path; NotebookLM can source from a Drive folder natively in its web UI
- Web dashboard (Flask + SSE) — substantial scope; future phase
- Chrome extension — requires web UI first
- Speaker diarization — poor Swedish accuracy; out of scope

### Architecture Approach

v2 is evolutionary, not a redesign. The existing module structure (cli.py, audio.py, transcribe.py, output.py, config.py, models.py) is extended in four modules, and a new `destinations/` subpackage is added. The critical architectural move is extracting a `_run_transcription()` helper from `record_command` before wiring destinations, so both `record` and the new `transcribe` command share an identical post-transcription delivery path. The `destinations/` registry pattern isolates external service concerns: `output.py` writes local files and returns paths; the caller invokes `deliver(paths, cfg)` and the registry routes to enabled handlers. This keeps `output.py` a pure formatter with no knowledge of Drive or NotebookLM.

**Key design constraints:**
- All paths through `get_config_dir()` — never `Path.home() / ".mote"` directly; test isolation depends on this
- Destination errors are warnings, not failures — local files are always written first; a Drive upload failure must not appear as a transcription failure
- Config validation distinguishes fatal (invalid value) from non-fatal (absent v2 key) — apply silent defaults for new keys

**Major components:**
1. `cli.py` (modified) — add `transcribe_command`, `auth` command group, `_run_transcription()` helper, `--destination` flag
2. `audio.py` (modified) — add `auto_route_audio()` wrapper, silence tracking inside existing recording loop
3. `output.py` (modified) — add JSON format branch to `write_transcript()`; returns `list[Path]`
4. `config.py` (modified) — add `[destinations]` TOML section, `validate_config()`, extend key whitelist
5. `destinations/` (new) — `__init__.py` registry + `drive.py` (OAuth2, upload) + `notebooklm.py` (asyncio.run wrapper)

### Critical Pitfalls

1. **Audio routing restore on crash** — SIGKILL cannot be caught; write `~/.mote/audio_restore.json` before switching to BlackHole; check for recovery file on every `mote record` startup; `try/finally` alone is insufficient for force-quit scenarios.

2. **Google OAuth refresh token not issued** — always pass `access_type='offline'` and `prompt='consent'` to `run_local_server()`; without `prompt='consent'`, Google withholds the refresh token on repeat authorizations; use `run_local_server(port=0)` only (OOB/console flow deprecated October 2022).

3. **Config validation breaks existing users** — absent v2 config keys must apply silent defaults, not raise errors; only error when a key is present but has an invalid value; test validation with a v1-format config file before shipping.

4. **notebooklm-py breaks without warning** — library wraps undocumented Google internal endpoints that change without notice; wrap every call in try/except; surface as warnings; never let NotebookLM failure fail `mote record`; Drive-first is the stable delivery path.

5. **sounddevice callback must never block** — callback does exactly `q.put_nowait(indata.copy())`; any I/O, print, or lock acquisition causes silent audio buffer overflow; consumer thread handles all file writing.

6. **BlackHole Multi-Output drift on Apple Silicon** — progressive distortion after 20-30 minutes; for capture-only use, set BlackHole 2ch as system output directly (no Multi-Output device); document in setup instructions.

## Implications for Roadmap

The architecture research provides an explicit build order. These phase suggestions follow it directly:

### Phase 1: Config Foundation and CLI Polish
**Rationale:** Zero-risk, no new dependencies. Establishes foundation that all subsequent phases depend on. The `_run_transcription()` helper must exist before destinations can be wired into both `record` and `transcribe` commands.
**Delivers:** `validate_config()`, `[destinations]` TOML section with defaults, JSON output format, `mote transcribe <file>` command, retry-on-failure prompt, orphaned WAV offer on startup.
**Addresses:** Config validation (REL-01), JSON output (INT-02), `mote transcribe` (CLI-07), retry/orphan UX (CLI-08).
**Avoids:** Config backward-compatibility break (Pitfall 9 — silent defaults for absent keys); duplication between `record` and `transcribe` (extract `_run_transcription()` first).
**Research flag:** None — all standard Python/Click/tomlkit patterns; fully specified in research.

### Phase 2: Audio Improvements
**Rationale:** Both features modify `audio.py`, share the same review, and have no new dependencies. Silence detection validates that auto-routing succeeded. Build together.
**Delivers:** Silence detection warning during recording, auto-switch BlackHole routing with recovery file for crash protection.
**Addresses:** Silence detection (AUD-06), auto-routing (AUD-05).
**Avoids:** SIGKILL audio restore failure (Pitfall 2 — write recovery file before switch), SwitchAudioSource absent (Pitfall 3 — `shutil.which()` check, degrade gracefully), false-positive silence warnings (Pitfall 10 — conservative -50 dBFS threshold, 10-second window).
**Research flag:** None — subprocess and numpy patterns fully specified in research; no ambiguity.

### Phase 3: Google Drive Integration
**Rationale:** Primary integration value for v2.0. Well-documented official API. Must be built before NotebookLM so the destinations registry is proven with a stable API first. Drive is also the recommended intermediary for NotebookLM (upload to Drive; NotebookLM sources from Drive folder).
**Delivers:** `mote auth google`, Google Drive upload destination, `destinations/drive.py`, delivery hooked into `_run_transcription()`.
**Addresses:** Drive upload (INT-04), `mote auth google` (INT-04a).
**Avoids:** OAuth refresh token missing (Pitfall 4 — `access_type='offline'`, `prompt='consent'`), OOB flow deprecation (Pitfall 6 — `run_local_server(port=0)` only), unverified app warning (Pitfall 5 — document with instructions), hardcoded token paths (Architecture Anti-Pattern 2 — use `get_config_dir()`).
**Research flag:** None — InstalledAppFlow with all parameters specified; `drive.file` scope and token persistence fully documented.

### Phase 4: NotebookLM Integration (Optional, Experimental)
**Rationale:** Lowest confidence, highest fragility. Should follow Drive so the registry pattern is established and tested. Gate as explicit opt-in. Check library health before starting.
**Delivers:** `mote auth notebooklm`, NotebookLM destination (experimental, marked as best-effort in CLI help text).
**Addresses:** NotebookLM upload (INT-05).
**Avoids:** Undocumented API breakage (Pitfall 7 — try/except all calls, warn not error), session cookie expiry (Pitfall 8 — clear re-auth message, detect 401/403 proactively), async/sync mismatch (Architecture Anti-Pattern 4 — use `asyncio.run()`).
**Research flag:** Check notebooklm-py GitHub issues before starting; if library is broken or unmaintained, skip this phase entirely and document Drive-as-intermediary as the recommended workflow.

### Phase 5: Web UI (Future)
**Rationale:** Substantial scope; builds on stable CLI foundation. Requires Flask SSE, threaded server, queue-based event delivery.
**Delivers:** Browser-based recording and transcript UI with live status via SSE.
**Avoids:** Flask single-threaded SSE block (Pitfall 14 — `threaded=True` + waitress from first SSE implementation).
**Research flag:** Needs phase research — SSE queue design, waitress configuration, Flask threading model for concurrent CLI + web use.

### Phase 6: Chrome Extension (Future)
**Rationale:** Depends on web UI server being operational. NativeMessagingHost is a thin dispatcher over SessionManager.
**Delivers:** One-click recording trigger from browser during meetings.
**Avoids:** stdout corruption in native messaging (Pitfall 16 — all logging to stderr), manifest path and extension ID mismatch (Pitfall 17 — generated at install time with absolute path).
**Research flag:** Needs phase research — nativemessaging-ng manifest install automation, dev vs production extension ID handling, Chrome Manifest V3 native messaging constraints.

### Phase Ordering Rationale

- Phase 1 before everything: `_run_transcription()` extraction is a prerequisite for destinations; config validation must be backward-compatible before it ships; JSON output proves the output extension pattern at zero risk.
- Phase 2 before Phase 3: audio module changes are independent of Drive; combining them would increase review complexity without benefit; silence detection and routing share the same module and reviewer context.
- Phase 3 before Phase 4: Drive is the reliable primary delivery path; NotebookLM is better as a post-Drive enhancement; registry pattern tested with a stable API before applying it to an unstable one.
- Phases 5-6 deferred: substantially larger scope than the v2.0 integration milestone; web server adds new architectural concerns (threading, SSE, request context) that should not be mixed with the integration work.

### Research Flags

Needs deeper research during planning:
- **Phase 5 (Web UI):** Flask SSE queue design for concurrent CLI + web access, waitress vs other WSGI options for local single-user deployment, thread-safe WhisperModel access pattern.
- **Phase 6 (Chrome Extension):** Chrome Manifest V3 native messaging changes since Manifest V2, nativemessaging-ng manifest install CLI behavior, dev vs production extension ID management and CWS submission.

Standard patterns (skip research-phase):
- **Phase 1:** All standard Python/Click/tomlkit patterns; fully specified in research with code examples.
- **Phase 2:** subprocess + numpy RMS patterns fully specified; all edge cases (SwitchAudioSource absent, SIGKILL) documented with solutions.
- **Phase 3:** InstalledAppFlow with exact parameters specified; google-api-python-client patterns fully documented.
- **Phase 4:** Patterns specified, but library health check before starting is mandatory.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions confirmed on PyPI; KBLab model format confirmed on HuggingFace; compatibility matrix validated against official sources |
| Features | HIGH | v1 inventory from direct codebase inspection; v2 features from official API docs; NotebookLM is MEDIUM due to unofficial API |
| Architecture | HIGH | Based on direct codebase inspection + verified library documentation; build order is explicit and dependency-ordered with code examples |
| Pitfalls | HIGH | All critical pitfalls verified against official docs or primary issue trackers; prevention strategies are specific and testable |

**Overall confidence:** HIGH for Phases 1-3; MEDIUM for Phase 4 (NotebookLM)

### Gaps to Address

- **NotebookLM API stability:** Check notebooklm-py GitHub issues and recent commits before starting Phase 4. If the library is broken or unmaintained, skip Phase 4 and recommend Drive-as-intermediary pattern only — NotebookLM can source from a Google Drive folder natively in its web UI.
- **GCP credential distribution:** Users must create their own Google Cloud project and provide their own `client_secret.json`. This is setup friction that could block Drive adoption. Document the setup steps clearly in README; consider whether a pre-built OAuth app is worth pursuing (requires Google verification for published apps).
- **SwitchAudioSource on current macOS:** The tool is documented as tested through macOS 11.2 officially; verify it works on macOS 14/15 before shipping Phase 2.
- **Default model size:** Research recommends `kb-whisper-medium` on Apple Silicon for speed/quality balance. Validate this against actual M-series performance during Phase 1 or 2 before setting it as the config default.

## Sources

### Primary (HIGH confidence)
- https://github.com/SYSTRAN/faster-whisper/releases — faster-whisper 1.2.1 confirmed (Oct 31, 2025)
- https://huggingface.co/KBLab/kb-whisper-large — KBLab model formats, ctranslate2 availability, 5 sizes
- https://kb-labb.github.io/posts/2025-03-07-welcome-KB-Whisper/ — 47% WER reduction, 50K hours training data
- https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html — InstalledAppFlow pattern, drive.file scope
- https://developers.google.com/workspace/drive/api/quickstart/python — Drive API v3 Python quickstart
- https://pypi.org/project/sounddevice/ — sounddevice 0.5.5 (Jan 23, 2026)
- https://pypi.org/project/click/ — Click 8.3.0 (Nov 15, 2025)
- https://pypi.org/project/Flask/ — Flask 3.1.3 (Feb 19, 2026)
- https://pypi.org/project/google-api-python-client/ — 2.193.0 (Mar 17, 2026)
- https://maxhalford.github.io/blog/flask-sse-no-deps/ — SSE without Redis pattern
- https://docs.astral.sh/uv/concepts/build-backend/ — hatchling as build backend for pip-installable packages
- Direct codebase inspection: src/mote/cli.py, audio.py, output.py, config.py, transcribe.py (2026-03-28)

### Secondary (MEDIUM confidence)
- https://pypi.org/project/notebooklm-py/ — notebooklm-py 0.3.4 (Mar 12, 2026); unofficial Google API wrapper
- https://github.com/teng-lin/notebooklm-py — auth flow, cookie storage, unofficial API warning confirmed
- https://github.com/deweller/switchaudio-osx — SwitchAudioSource CLI tool; brew install, flag usage confirmed

### Tertiary (LOW confidence)
- Mistral Voxtral Swedish support: Swedish confirmed absent from 13-language list — do not use for Swedish transcription

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
