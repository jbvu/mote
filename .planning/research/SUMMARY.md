# Project Research Summary

**Project:** Möte — macOS Swedish meeting transcription tool
**Domain:** macOS desktop audio capture and local speech-to-text, Swedish/Scandinavian focus
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

Möte is a local-first macOS meeting transcription tool built around a clear and well-documented stack. The core value proposition is KBLab's KB-Whisper model suite — Swedish-optimized Whisper variants that deliver 47% lower word-error rate than OpenAI's generic whisper-large-v3. The recommended architecture pairs faster-whisper (CTranslate2 backend) with BlackHole virtual audio capture, a Click CLI as the primary interface, and an optional Flask web dashboard with Server-Sent Events for live status. The full stack is verifiable, current as of March 2026, and the build order is unambiguous: foundation services first (config, file store, event bus), then audio capture, then transcription engines, then output and Drive integration, then web UI and Chrome extension.

The product falls into a well-understood category — local audio recorder and batch transcriber — but with two sources of real technical complexity. First, BlackHole audio routing is fragile: macOS provides no API to automate system output switching, and the Multi-Output device configuration on Apple Silicon has a documented clock-drift bug that degrades audio after 20–30 minutes. Second, the Chrome native messaging integration has several silent-failure modes (stdout byte corruption, absolute path requirements, extension ID mismatches) that are easy to introduce and hard to diagnose. Both risk areas are fully documented with prevention strategies and must be addressed in the first working iteration of each feature, not as retrofits.

The MVP is tightly scoped: CLI recording, local KB-Whisper transcription, Markdown/text output, model management, audio level monitoring, and Google Drive push. The web dashboard and Chrome extension are deliberate v1.x additions after the CLI proves the pipeline. Speaker diarization, real-time streaming transcription, and multi-language Scandinavian support are correctly deferred to v2+. Mistral Voxtral must not be treated as a Swedish engine — Swedish is absent from its confirmed language list.

## Key Findings

### Recommended Stack

The stack is Python 3.11+, faster-whisper 1.2.1, sounddevice 0.5.5, Click 8.3.0, Flask 3.1.3, and tomlkit. These are all current, pip-installable from GitHub via hatchling, and free of significant version conflicts. The only non-pip system dependency is BlackHole 2ch via Homebrew. faster-whisper loads KBLab ctranslate2-format models directly by HuggingFace repo ID — no format conversion needed.

For Apple Silicon, use `device="cpu"` and `compute_type="int8"` in WhisperModel. CTranslate2's MPS (Metal) support is experimental; CPU with int8 quantization is faster and more reliable. Flask SSE requires no additional package — a plain streaming response with a `queue.Queue` backend eliminates the Redis dependency that Flask-SSE introduces. tomlkit (not the stdlib tomllib) is required because the settings UI must write config values while preserving comments.

**Core technologies:**
- faster-whisper 1.2.1: local transcription engine — CTranslate2 backend, 4x faster than openai/whisper, loads KBLab models natively
- KBLab/kb-whisper-*: Swedish transcription model — 47% lower WER vs. whisper-large-v3, trained on 50K hours Swedish speech
- sounddevice 0.5.5: BlackHole audio capture — NumPy-native API, cleaner than PyAudio, bundles PortAudio via pip
- Click 8.3.0: CLI framework — decorator-based, composable commands, clean help generation
- Flask 3.1.3: web UI server — built-in streaming for dependency-free SSE, Jinja2 templates, single-user localhost tool
- tomlkit: TOML config read/write — preserves comments and formatting, required for write-through settings
- nativemessaging-ng 1.3.3: Chrome native messaging — handles 4-byte length framing, installs browser manifest via CLI
- google-api-python-client + google-auth-oauthlib: Google Drive integration — OAuth2 installed-app flow, token persistence

**Avoid:** Mistral Voxtral as Swedish engine (Swedish not in confirmed language list), Flask-SSE pip package (Redis dependency), oauth2client (deprecated 2019), openai-whisper original package (CPU-only, no CTranslate2), PyAudio (harder install), threading for concurrent audio + transcription.

### Expected Features

**Must have (table stakes):**
- BlackHole 2ch system audio capture — without this, nothing else works
- CLI start/stop recording (with PID/socket state persistence) — expected by any recorder
- Local transcription via faster-whisper + KB-Whisper — the core differentiator
- Output as Markdown and plain text — primary consumption formats
- TOML configuration at `~/.config/mote/config.toml` — persistent settings
- Model management CLI (download/list/delete) — model must exist before transcription
- Real-time audio level monitoring — confirms BlackHole routing before meeting starts
- Transcription progress reporting — silence during multi-minute processing causes abandonment
- Temp file cleanup after successful transcription — storage hygiene expected
- Google Drive auto-push — completes the capture-to-NotebookLM workflow

**Should have (competitive):**
- OpenAI Whisper API as cloud fallback — for machines without downloaded local model
- Web dashboard (Flask + SSE) — lowers barrier for non-developer colleagues
- Chrome extension — one-click start/stop without window-switching during meetings
- Model management web UI with download progress (size shown before download)
- JSON output format — for downstream tooling and search indexing

**Defer (v2+):**
- Norwegian, Danish, Finnish language support — KB-Whisper is Swedish-only; requires different model strategy
- Speaker diarization — pyannote.audio has poor Swedish accuracy and adds heavy dependencies
- Transcript search history (SQLite FTS) — only valuable once transcript archive grows
- Scandinavian language auto-detect — requires multi-language model

**Anti-features to avoid building:**
- Real-time streaming transcription — doubles complexity, conflicts with batch model loading, unnecessary
- Auto-detect meeting start — fragile OS hooks, privacy concerns
- Auto-download models on first run — silent large download, bad UX
- Multi-user auth for web UI — overkill for localhost personal tool
- SaaS / cloud-hosted version — different product entirely

### Architecture Approach

The architecture is a three-layer system: an interface layer (CLI, Flask web server, Chrome extension), an application core (SessionManager, AudioRecorder, TranscriptionService, ModelManager, ConfigManager, EventBus), and an output layer (OutputFormatter, GoogleDriveClient, FileStore). All state flows through SessionManager, which owns the recording lifecycle state machine (`idle → recording → transcribing → done → error`). Background workers communicate status to the browser via a `queue.Queue` EventBus consumed by a Flask SSE generator — no Redis, no polling. The transcription engine is abstracted behind an `AbstractEngine` ABC, making it straightforward to add new backends without touching callers.

The build order is strictly tier-based: ConfigManager, FileStore, and EventBus first (Tier 1), then AudioRecorder, ModelManager, OutputFormatter, and GoogleDriveClient (Tier 2), then LocalEngine/APIEngine and TranscriptionService (Tier 3), then SessionManager (Tier 4), then CLI and Flask server (Tier 5), then Chrome extension last. This order is forced by dependency relationships — do not short-circuit it.

**Major components:**
1. SessionManager — single source of truth for recording state; thread-safe; shared by CLI and web server
2. AudioRecorder — opens BlackHole via sounddevice; callback writes only to queue (never blocks); consumer thread writes WAV
3. TranscriptionService + AbstractEngine — engine selection (local/openai/voxtral) and isolated transcription execution
4. EventBus — `queue.Queue` shared between background threads (producers) and Flask SSE route (consumer)
5. GoogleDriveClient — OAuth2 installed-app flow; token stored at `~/.config/mote/gdrive_token.json`; refresh before every call
6. NativeMessagingHost — lightweight dispatcher only; calls into SessionManager; all logging redirected to stderr

### Critical Pitfalls

1. **BlackHole Multi-Output clock drift on Apple Silicon** — audio degrades after 20–30 minutes on M1/M2 due to a known BlackHole bug. Prevention: set BlackHole 2ch as primary/clock device in Aggregate Device config; for capture-only use, skip Multi-Output entirely and route system output directly to BlackHole.

2. **sounddevice callback must never block** — any blocking operation (file I/O, print, lock acquisition) inside the InputStream callback causes silent audio gaps. Prevention: callback does exactly one thing — `q.put_nowait(indata.copy())`; a separate consumer thread writes to WAV.

3. **Flask SSE blocks all requests with single-threaded server** — one open SSE connection starves all other routes. Prevention: always run with `app.run(threaded=True)` minimum; use Waitress for the deployed form; wrap SSE generator with `stream_with_context()` and `q.get(timeout=30)` to handle client disconnect.

4. **Chrome native messaging stdout corruption** — any byte written to stdout (print(), logging, exception tracebacks) corrupts the binary message stream. Chrome disconnects silently. Prevention: redirect all logging to stderr at process start; use `sys.stdout.buffer.write(struct.pack('<I', len(msg)) + msg.encode())` exclusively.

5. **Google Drive OAuth refresh token missing** — access tokens expire after 1 hour; without `access_type='offline'` and `prompt='consent'` in the auth flow, no refresh token is issued and uploads fail on the second run. Prevention: always pass both parameters; check `credentials.refresh_token is None` after loading token.json and re-authorize if missing.

6. **KBLab tokenizer version mismatch** — older faster-whisper releases raise `Exception: data did not match any variant of untagged enum ModelWrapper` when loading KB-Whisper models. Prevention: pin `faster-whisper>=1.0.0` and `tokenizers>=0.19.0`; add a model load smoke-test to the test suite.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation Services
**Rationale:** ConfigManager, FileStore, and EventBus are imported by every other component. Building them first gives all subsequent phases a stable base. Getting their contracts right (especially EventBus event schema) prevents refactoring later.
**Delivers:** Working config read/write (TOML), canonical path resolution for WAV and transcript files, thread-safe event queue with defined event schema.
**Addresses:** Configuration (table stakes), sets up temp file cleanup pattern.
**Avoids:** Pitfall 10 (WAV disk space) — FileStore establishes the disk-space-check pattern from day one; Pitfall 11 (signal handling and temp cleanup) — FileStore owns WAV lifecycle.

### Phase 2: Audio Capture
**Rationale:** Everything depends on a reliable WAV file. Audio capture is the first integration with hardware (BlackHole) and the first place silent failure can occur. Validate this in isolation before adding transcription complexity.
**Delivers:** CLI `mote record start/stop`, WAV written incrementally to disk, real-time audio level monitoring, device validation at recording start (refuse to record if BlackHole not detected).
**Addresses:** BlackHole audio capture, start/stop recording, audio level monitoring (all P1 table stakes).
**Avoids:** Pitfall 1 (BlackHole drift — document clock device setup), Pitfall 2 (silent recording — device detection at start), Pitfall 6 (callback blocking — queue-based consumer pattern from day one), Pitfall 10 (WAV size — incremental write, disk check).
**Research flag:** None — well-documented patterns, BlackHole setup is fully researched.

### Phase 3: Transcription Engine
**Rationale:** Core differentiator. Builds on WAV output from Phase 2. Establish the AbstractEngine ABC and LocalEngine before adding APIEngine so the abstraction is validated against a real implementation first.
**Delivers:** `mote transcribe`, LocalEngine (faster-whisper + KB-Whisper), APIEngine (OpenAI Whisper), CLI progress reporting, Markdown/text output, temp WAV cleanup after successful transcription.
**Addresses:** Local transcription (P1), OpenAI fallback (P1), output formats MD/TXT (P1), progress reporting (P1), temp file cleanup (table stakes).
**Avoids:** Pitfall 3 (WhisperModel thread safety — lock from day one), Pitfall 4 (KBLab tokenizer — pin versions, smoke-test), anti-pattern 3 (lazy model load, cached singleton).
**Research flag:** None — faster-whisper and KBLab patterns are fully documented with known version constraints.

### Phase 4: Model Management CLI
**Rationale:** Local transcription cannot be used without a model on disk. Model management (download with progress, list, delete) must exist before local transcription is usable in practice. Logically precedes any user-facing release.
**Delivers:** `mote models download/list/delete`, huggingface_hub integration, progress reporting to stdout (EventBus events for later SSE reuse), disk usage display, model size shown before download.
**Addresses:** Model management CLI (P1), prevents silent failure when model is missing.
**Avoids:** Anti-feature "auto-download on first run" — explicit download with size shown.
**Research flag:** None — huggingface_hub.snapshot_download pattern is standard.

### Phase 5: Google Drive Integration
**Rationale:** Completes the core workflow: capture → transcribe → push to Drive for NotebookLM. This is the last P1 feature. Implement as a discrete, testable component (GoogleDriveClient) before the web UI exists, so it can be exercised from the CLI.
**Delivers:** `mote push` / auto-upload config option, OAuth2 installed-app flow, token persistence, Drive URL returned after upload.
**Addresses:** Google Drive auto-push (P1).
**Avoids:** Pitfall 9 (OAuth refresh token — `access_type='offline'`, `prompt='consent'` required), security mistake (credentials.json/token.json in .gitignore, chmod 600).
**Research flag:** Moderate — OAuth installed-app flow is documented but has several sharp edges (refresh token, client secret distribution). No additional research needed; pitfalls are fully captured.

### Phase 6: Web Dashboard
**Rationale:** Once the CLI validates the full pipeline (Phases 1–5), the web dashboard adds a visual interface without changing core logic. Flask routes are thin wrappers over the same SessionManager methods the CLI uses. Build SSE infrastructure here — it is reused by the model download progress in Phase 7.
**Delivers:** Flask server (`mote serve`), dashboard (recording controls, live audio meter, job history), settings page, SSE event stream, threaded mode / Waitress configuration.
**Addresses:** Web dashboard (P2), SSE progress stream (enhances P1 progress reporting).
**Avoids:** Pitfall 5 (Flask single-threaded SSE — threaded=True/Waitress from first implementation), anti-pattern 1 (global variables — SessionManager owns all state), anti-pattern 2 (SSE generator teardown — `try/finally` with `GeneratorExit`).
**Research flag:** SSE without dependencies is well-documented (Max Halford pattern). Waitress for production serve is standard. No additional research needed.

### Phase 7: Chrome Extension
**Rationale:** Extension is built last because it depends on the Flask server (Phase 6) and the NativeMessagingHost, which must be a thin dispatcher over the already-stable SessionManager. Native messaging has the highest concentration of silent-failure pitfalls — building it after the rest of the system is stable reduces debug surface.
**Delivers:** Manifest V3 extension, popup UI (start/stop button, status badge), NativeMessagingHost (stdin/stdout dispatcher), `mote install-extension` CLI command (writes manifest with absolute path, prompts for extension ID).
**Addresses:** Chrome extension (P2).
**Avoids:** Pitfall 7 (stdout corruption — stderr logging, binary stdout writes only), Pitfall 8 (absolute path and extension ID — generated at install time), anti-pattern 4 (NativeMessagingHost does heavy work — calls SessionManager only).
**Research flag:** Chrome native messaging has sparse edge-case documentation. If bidirectional message flow proves unreliable, consult Chrome extension issue tracker directly.

### Phase Ordering Rationale

- Foundation before everything because ConfigManager and EventBus are imported everywhere — their interface must be stable before any consumer is built.
- Audio capture before transcription because transcription requires a WAV file; testing the engine against a real captured file validates the full pipeline.
- Transcription before model management UI because CLI model management is simpler and must exist before the web UI model page is designed.
- Drive integration before web UI because it is a P1 feature and exercising it from the CLI first validates the OAuth flow without web UI complexity.
- Web dashboard before Chrome extension because the extension's NativeMessagingHost calls into SessionManager, and the SessionManager is most thoroughly exercised by the web dashboard (concurrent threads, SSE events, thread-safety).
- Chrome extension last because it has the most isolated and well-scoped interface (start/stop only) and the most fragile platform integration (native messaging) — it is safest to add when the rest of the system is stable.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Google Drive):** OAuth installed-app flow for distribution to other users requires users to create their own Google Cloud project and provide their own `client_secret.json`. The UX for this setup step needs careful thought during planning.
- **Phase 7 (Chrome Extension):** The extension ID changes between unpacked dev build and Chrome Web Store publication. If CWS publication is in scope, manifest generation and the `mote install-extension` command need to handle both IDs. Research CWS submission process at planning time.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** ConfigManager with tomlkit and FileStore are standard Python patterns. No research needed.
- **Phase 2 (Audio capture):** BlackHole + sounddevice callback pattern is fully documented with verified code examples.
- **Phase 3 (Transcription):** faster-whisper + KBLab loading is verified; version constraints are pinned.
- **Phase 4 (Model management):** huggingface_hub.snapshot_download with tqdm callback is documented.
- **Phase 6 (Web dashboard):** Flask SSE without dependencies is a proven pattern with published reference implementation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified against PyPI and official sources as of March 2026; KBLab model format confirmed on HuggingFace |
| Features | HIGH | Table stakes derived from competitor analysis and domain research; MVP scope conservative and validated against project goals |
| Architecture | HIGH | Patterns (Strategy, EventBus, SessionManager state machine) are well-established; component boundaries are unambiguous |
| Pitfalls | HIGH | All critical pitfalls traced to primary sources (GitHub issues, official docs); prevention strategies are specific and testable |

**Overall confidence:** HIGH

### Gaps to Address

- **Mistral Voxtral Swedish support:** Swedish is not in Voxtral's confirmed 13-language list. Include as an optional engine but benchmark WER against KB-Whisper before promoting it. This gap is low-risk — it affects only an optional engine, not the core product.
- **Google OAuth client secret distribution:** The intended user audience (others installing from GitHub) must create their own Google Cloud project. The setup UX for this is not fully designed. Address during Phase 5 planning — document whether Möte ships its own OAuth app or requires users to bring their own credentials.
- **Chrome Web Store publication scope:** If the extension will be published to CWS rather than only installed in developer mode, the extension ID management and CWS submission process need a dedicated planning task in Phase 7.
- **KB-Whisper performance on Intel Mac:** Research confirms Apple Silicon int8 CPU recommendations. Intel Mac guidance (use `kb-whisper-small` for responsiveness) is reasonable but not benchmarked. Low risk given the Apple Silicon prevalence in the target audience.

## Sources

### Primary (HIGH confidence)
- https://github.com/SYSTRAN/faster-whisper/releases — faster-whisper 1.2.1 confirmed
- https://huggingface.co/KBLab/kb-whisper-large — KBLab model formats, ctranslate2 availability, 5 sizes
- https://kb-labb.github.io/posts/2025-03-07-welcome-KB-Whisper/ — 47% WER reduction, 50K hours training data
- https://pypi.org/project/sounddevice/ — sounddevice 0.5.5 (Jan 23, 2026)
- https://pypi.org/project/Flask/ — Flask 3.1.3 (Feb 19, 2026)
- https://pypi.org/project/click/ — Click 8.3.0 (Nov 15, 2025), Python >=3.10 required
- https://pypi.org/project/openai/ — openai 2.29.0 (Mar 17, 2026)
- https://pypi.org/project/mistralai/ — mistralai 2.0.1 (Mar 12, 2026)
- https://pypi.org/project/google-api-python-client/ — 2.193.0 (Mar 17, 2026)
- https://github.com/roelderickx/nativemessaging-ng — nativemessaging-ng 1.3.3, actively maintained
- https://github.com/ExistentialAudio/BlackHole/issues/274 — BlackHole drift distortion on M1/M2 confirmed
- https://huggingface.co/KBLab/kb-whisper-large/discussions/15 — KBLab tokenizer version mismatch confirmed
- https://github.com/SYSTRAN/faster-whisper/discussions/406 — WhisperModel concurrency not thread-safe confirmed
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging — Chrome native messaging protocol
- https://developers.google.com/identity/protocols/oauth2 — OAuth2 refresh token requirements

### Secondary (MEDIUM confidence)
- https://maxhalford.github.io/blog/flask-sse-no-deps/ — Flask SSE without Redis pattern (community reference)
- https://mistral.ai/news/voxtral — Voxtral language list; Swedish absence noted but general multilingual claims made
- https://kb-labb.github.io/posts/2026-02-26-easytranscriber/ — KBLab reference implementation for similar tool
- Competitor feature analysis (Otter.ai, Jamie, trnscrb) — feature landscape and differentiation

### Tertiary (LOW confidence)
- Voxtral Swedish WER vs. KB-Whisper — not benchmarked; treat as unknown until tested
- Intel Mac performance with KB-Whisper — recommendation based on architecture reasoning, not measured benchmarks

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
