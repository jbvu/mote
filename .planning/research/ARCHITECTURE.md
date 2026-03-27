# Architecture Research

**Domain:** macOS desktop audio transcription tool (Python)
**Researched:** 2026-03-27
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Interface Layer                           │
├────────────────┬───────────────────────┬────────────────────────┤
│   CLI (Click)  │  Web UI (Flask+Jinja)  │  Chrome Extension      │
│  mote record   │  localhost:5000        │  popup.js              │
│  mote transcribe│  /  /settings /models │  background.js         │
└───────┬────────┴──────────┬────────────┴──────────┬─────────────┘
        │                   │ HTTP/SSE               │ native msg
        │                   │                        │ (stdin/stdout)
        └─────────┬─────────┘                        │
                  ▼                                   │
┌─────────────────────────────────────────────────────────────────┐
│                      Application Core                           │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │ SessionManager│  │ ConfigManager  │  │ NativeMessagingHost │  │
│  │ (state, WAV) │  │ (TOML r/w)     │  │ (stdin/stdout loop) │  │
│  └──────┬───────┘  └───────┬────────┘  └──────────┬──────────┘  │
│         │                  │                        │             │
│  ┌──────▼───────┐  ┌───────▼────────┐  ┌──────────▼──────────┐  │
│  │ AudioRecorder │  │ ModelManager  │  │ EventBus (SSE queue) │  │
│  │ (sounddevice) │  │ (hf_hub)      │  │ (thread-safe queue)  │  │
│  └──────┬───────┘  └────────────────┘  └──────────┬──────────┘  │
│         │                                           │             │
│  ┌──────▼───────────────────────────────────────────▼──────────┐ │
│  │                  TranscriptionService                        │ │
│  │         (AbstractEngine → LocalEngine | APIEngine)          │ │
│  └──────────────────────────────┬───────────────────────────────┘ │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│                        Output Layer                              │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────────┐ │
│  │ OutputFormatter│  │ GoogleDriveClient│  │ FileStore          │ │
│  │ (md/txt/json)  │  │ (OAuth2 + upload)│  │ (WAV, transcripts) │ │
│  └────────────────┘  └─────────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| CLI (Click) | Entry points: record, transcribe, models, config, serve | Thin — delegates all logic to core |
| Flask Web Server | HTTP routes, SSE stream, Jinja templates | Runs in daemon thread when `mote serve` is called |
| Chrome Extension | Popup UI, start/stop button via native messaging | Communicates with NativeMessagingHost subprocess only |
| NativeMessagingHost | Bridge: Chrome extension ↔ SessionManager | Registered in Chrome manifest; stdin/stdout JSON protocol |
| SessionManager | Owns recording state machine (idle → recording → transcribing → done) | Single source of truth; shared across CLI and web UI |
| AudioRecorder | Opens BlackHole device via sounddevice, writes WAV chunks | Runs in background thread; signals SessionManager on stop |
| ConfigManager | Reads/writes `~/.config/mote/config.toml`; provides defaults | Loaded once at startup; write-through on changes |
| ModelManager | Lists, downloads, deletes local faster-whisper model files via huggingface_hub | Emits progress events to EventBus during download |
| TranscriptionService | Selects engine, runs transcription on WAV file, returns segments | Called synchronously from CLI; from background thread for web |
| AbstractEngine | Interface: `transcribe(wav_path, language) -> segments` | Implemented by LocalEngine and APIEngine |
| LocalEngine | Loads faster-whisper WhisperModel, runs CTranslate2 inference | Model loaded lazily, cached for session |
| APIEngine | Calls OpenAI or Voxtral HTTP API with WAV file | Selects API by config; handles chunking if needed |
| OutputFormatter | Converts segment list to Markdown / plain text / JSON | Pure function — no side effects |
| GoogleDriveClient | OAuth2 flow (installed-app), token refresh, file upload | Stores token in `~/.config/mote/gdrive_token.json` |
| EventBus | Thread-safe `queue.Queue` for SSE events | Flask SSE route consumes via `generator.send()` |
| FileStore | Manages temp WAV path, transcript output dir, cleanup | Centralises all path construction |

## Recommended Project Structure

```
mote/
├── __init__.py
├── cli.py                  # Click command group and all subcommands
├── server.py               # Flask app factory, routes, SSE endpoint
├── native_host.py          # Chrome native messaging host (stdin/stdout loop)
├── session.py              # SessionManager — state machine and WAV lifecycle
├── audio/
│   ├── __init__.py
│   └── recorder.py         # AudioRecorder using sounddevice + BlackHole
├── transcription/
│   ├── __init__.py
│   ├── service.py          # TranscriptionService — engine selection + run
│   ├── base.py             # AbstractEngine ABC
│   ├── local_engine.py     # LocalEngine via faster-whisper
│   └── api_engine.py       # APIEngine for OpenAI / Voxtral
├── models/
│   ├── __init__.py
│   └── manager.py          # ModelManager via huggingface_hub
├── config/
│   ├── __init__.py
│   └── manager.py          # ConfigManager — TOML read/write with defaults
├── output/
│   ├── __init__.py
│   └── formatter.py        # OutputFormatter — md/txt/json
├── gdrive/
│   ├── __init__.py
│   └── client.py           # GoogleDriveClient — OAuth2 + upload
├── events.py               # EventBus — thread-safe queue for SSE
└── store.py                # FileStore — path resolution and temp cleanup

chrome-extension/
├── manifest.json
├── background.js
├── popup.html
└── popup.js

templates/                  # Flask Jinja2 templates
├── base.html
├── index.html              # Dashboard: record/stop, recent transcripts
├── settings.html
└── models.html

static/
├── app.js                  # SSE EventSource subscriber
└── style.css

pyproject.toml
```

### Structure Rationale

- **audio/ transcription/ models/**: Grouped by domain, not by layer. Each subdomain owns its complexity. Easier to understand and test independently.
- **transcription/base.py**: ABC forces engine implementors to provide the same interface. Adding a new engine (e.g., AssemblyAI) requires only a new file in `transcription/`.
- **events.py**: Single shared EventBus module. Both `server.py` (SSE consumer) and `session.py`/`models/manager.py` (producers) import it without circular dependency.
- **native_host.py at root**: The Chrome native messaging host is a standalone entry point registered in the host manifest. It must be importable as `python -m mote.native_host`.
- **gdrive/ isolated**: Google OAuth credentials and token file handling is complex enough to deserve its own module boundary.

## Architectural Patterns

### Pattern 1: Engine Abstraction (Strategy Pattern)

**What:** `AbstractEngine` defines `transcribe(wav_path, language) -> list[Segment]`. `LocalEngine` and `APIEngine` implement it. `TranscriptionService` selects which engine to instantiate based on config.
**When to use:** Any time the transcription backend needs to be swappable — switching from local to API mid-session, A/B testing, or adding a new vendor.
**Trade-offs:** Small overhead for a two-engine system now, but pays off immediately when Voxtral or another vendor needs to be added without touching the caller.

```python
# transcription/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Segment:
    start: float
    end: float
    text: str

class AbstractEngine(ABC):
    @abstractmethod
    def transcribe(self, wav_path: str, language: str) -> list[Segment]:
        ...

# transcription/service.py
class TranscriptionService:
    def __init__(self, config: ConfigManager, event_bus: EventBus):
        self._config = config
        self._bus = event_bus

    def run(self, wav_path: str) -> list[Segment]:
        engine = self._select_engine()
        self._bus.put({"type": "transcription_started"})
        segments = engine.transcribe(wav_path, self._config.language)
        self._bus.put({"type": "transcription_done", "count": len(segments)})
        return segments

    def _select_engine(self) -> AbstractEngine:
        backend = self._config.backend  # "local" | "openai" | "voxtral"
        if backend == "local":
            return LocalEngine(self._config)
        return APIEngine(self._config, backend)
```

### Pattern 2: Event Bus for SSE Decoupling

**What:** A `queue.Queue` instance shared across threads. Background workers (recorder, transcription, model download) push JSON-serialisable dicts. The Flask SSE route pops from the queue in a generator and yields `data:` lines.
**When to use:** Any time a background thread needs to push a status update to the browser without the browser polling.
**Trade-offs:** Queue is in-process — single browser client only, which matches the single-user requirement. No Redis needed. If the SSE client disconnects, events accumulate briefly then get dropped on reconnect.

```python
# events.py
import queue
_bus: queue.Queue = queue.Queue(maxsize=200)

def put(event: dict) -> None:
    try:
        _bus.put_nowait(event)
    except queue.Full:
        pass  # drop — UI will recover on reconnect

def stream():
    """Generator consumed by Flask SSE route."""
    import json
    while True:
        event = _bus.get()
        yield f"data: {json.dumps(event)}\n\n"
```

### Pattern 3: SessionManager as Single State Source

**What:** `SessionManager` owns the recording lifecycle state: `idle | recording | transcribing | done | error`. Both the CLI commands and the Flask routes mutate state through `SessionManager`, never directly. This ensures the web UI always reflects accurate state even when the CLI triggered the action.
**When to use:** Required because two interfaces (CLI and web server) can interact with the same running session. Without a single owner, state diverges.
**Trade-offs:** SessionManager must be thread-safe (use `threading.Lock` on state transitions). Slightly more indirection than calling the recorder directly.

## Data Flow

### Recording Session Flow

```
User action (CLI or Web UI)
    │
    ▼
SessionManager.start_recording()
    │  validates: not already recording, BlackHole device present
    ├──► AudioRecorder.start()         runs in background thread
    │        writes chunks → temp WAV file
    │        emits audio_level events → EventBus
    │
User action: stop
    │
    ▼
SessionManager.stop_recording()
    ├──► AudioRecorder.stop()          joins recording thread
    │        finalises WAV file
    ├──► TranscriptionService.run()    runs in background thread
    │        emits transcription_progress → EventBus
    │        returns list[Segment]
    ├──► OutputFormatter.format()      produces md/txt/json strings
    ├──► FileStore.save()              writes transcript files
    └──► GoogleDriveClient.upload()    if auto-upload enabled in config
             emits upload_done → EventBus
```

### SSE Event Flow (Web UI)

```
Background thread (recorder/transcription/model download)
    │
    ▼
EventBus.put({"type": "...", ...})
    │
    ▼
Flask /events route (generator)
    │  yields "data: {...}\n\n" to HTTP response
    │
    ▼
Browser EventSource listener (app.js)
    │  dispatches DOM updates by event type
    ▼
UI state update (progress bar, status badge, log entry)
```

### Chrome Extension Flow

```
User clicks extension popup button
    │
    ▼
popup.js → chrome.runtime.sendMessage("toggle_recording")
    │
    ▼
background.js → chrome.runtime.connectNative("com.mote.host")
    │  sends JSON: {"action": "start"} or {"action": "stop"}
    │
    ▼
NativeMessagingHost (native_host.py, stdin/stdout)
    │  reads 4-byte length + JSON body from stdin
    ├──► SessionManager.start_recording() or .stop_recording()
    │  writes 4-byte length + JSON response to stdout
    │
    ▼
background.js receives response → updates extension badge
```

### Model Download Flow

```
User action (Web UI /models or CLI `mote models download <id>`)
    │
    ▼
ModelManager.download(model_id)
    │  calls huggingface_hub.snapshot_download()
    │  with tqdm progress callback → EventBus.put(download_progress)
    ▼
Files land in ~/.cache/huggingface/hub/...
ModelManager.list() re-scans and marks model available
```

## Build Order

The component dependency graph determines a natural build order:

```
Tier 1 — No dependencies (build first)
  ConfigManager       ← everything reads config
  FileStore           ← everything reads/writes paths
  EventBus            ← everything emits events

Tier 2 — Depends only on Tier 1
  AudioRecorder       ← uses FileStore for WAV path
  ModelManager        ← uses ConfigManager for model dir, EventBus for progress
  OutputFormatter     ← pure function, no deps
  GoogleDriveClient   ← uses ConfigManager for token path

Tier 3 — Depends on Tier 1 + 2
  LocalEngine         ← uses ModelManager (model path), ConfigManager
  APIEngine           ← uses ConfigManager (API key)
  TranscriptionService ← selects and runs LocalEngine or APIEngine, uses EventBus

Tier 4 — Orchestration
  SessionManager      ← owns AudioRecorder + TranscriptionService + FileStore

Tier 5 — Interfaces (build last)
  CLI (Click)         ← thin wrapper around SessionManager, ModelManager, etc.
  Flask Server        ← routes delegate to SessionManager; SSE consumes EventBus
  NativeMessagingHost ← calls SessionManager; can reuse CLI's core functions
  Chrome Extension    ← static files, communicates only with NativeMessagingHost
```

**Rationale for this order:**
- ConfigManager and FileStore must be stable before any other component is built — they are imported everywhere.
- EventBus shape (event dict schema) should be defined in Tier 1 even if nothing consumes it yet, so producers and consumers agree on format from the start.
- Build and test AudioRecorder in isolation (Tier 2) before introducing the SessionManager coordination layer.
- Implement and test one engine (LocalEngine) before TranscriptionService — validate that the ABC works before adding the second engine.
- CLI is the integration harness for all Tier 1-4 components. Build it before the web server so you have a working tool before adding the server complexity.
- Flask SSE and Chrome extension are incremental additions on top of a working CLI.

## Anti-Patterns

### Anti-Pattern 1: Sharing State via Global Variables

**What people do:** Use module-level variables (`is_recording = False`) instead of a SessionManager to track recording state.
**Why it's wrong:** Both the CLI and the Flask server run in the same process. A global variable is not thread-safe. The Flask server runs request handlers in threads; concurrent access to an unprotected global causes race conditions and incorrect state.
**Do this instead:** Route all state reads and mutations through `SessionManager` which uses `threading.Lock` internally.

### Anti-Pattern 2: Running Flask in Threaded Mode Without SSE-Safe Generator Teardown

**What people do:** Start `app.run(threaded=True)` and write an SSE generator that loops forever without checking if the client disconnected.
**Why it's wrong:** Each SSE connection holds a thread. If the client disconnects, the generator never terminates, leaking the thread and eventually exhausting the server's thread pool.
**Do this instead:** The SSE generator must catch `GeneratorExit` (raised when Flask tears down the response) and clean up. Use `try/finally` around the queue poll loop.

### Anti-Pattern 3: Loading the Whisper Model on Every Transcription Call

**What people do:** Instantiate `WhisperModel(...)` inside `transcribe()` so the model always loads fresh.
**Why it's wrong:** Loading a faster-whisper model takes 2-15 seconds depending on size. For a CLI with repeated use or the web UI triggering multiple transcriptions, this is unacceptable.
**Do this instead:** `LocalEngine` loads the model lazily on first call and caches it as an instance variable. The instance is kept alive in `TranscriptionService` across calls within the same process lifetime.

### Anti-Pattern 4: Native Messaging Host Doing Heavy Work

**What people do:** Put transcription or audio recording logic directly inside the native messaging host process.
**Why it's wrong:** Chrome starts and stops the native host process on demand. The host is not a long-lived daemon — it should be a lightweight dispatcher only.
**Do this instead:** The NativeMessagingHost calls into SessionManager which manages the long-lived recording and transcription state. The host just translates Chrome messages into SessionManager method calls.

### Anti-Pattern 5: Hardcoding Google OAuth Credentials in Source

**What people do:** Paste `client_id` and `client_secret` directly into `gdrive/client.py`.
**Why it's wrong:** Breaks distribution — other users cannot use the same OAuth app credentials safely, and secrets must not be in version control.
**Do this instead:** Distribute `client_secret.json` as a user-provided file placed at `~/.config/mote/gdrive_client_secret.json` (path configurable). Document the one-time setup in README. `GoogleDriveClient` reads from this path at runtime.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| BlackHole virtual audio | sounddevice device enumeration by name | Device name is "BlackHole 2ch"; must be installed via Homebrew |
| HuggingFace Hub | `huggingface_hub.snapshot_download()` with tqdm callback | KBLab models are at `KBLab/kb-whisper-*`; cache in `~/.cache/huggingface` |
| OpenAI Whisper API | `openai.audio.transcriptions.create()` with file upload | 25 MB file limit; WAV at 1.9 MB/min stays well under limit |
| Mistral Voxtral API | HTTP POST to Mistral API endpoint | Verify endpoint URL and language support before building; mark HIGH risk |
| Google Drive API v3 | `googleapiclient.discovery.build("drive", "v3")` with OAuth2 | InstalledAppFlow for desktop; token stored locally; refresh automatic |
| Chrome Extension | Native messaging host registered in `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/` | Requires `manifest.json` host config file at install time |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ SessionManager | Direct method calls (same thread) | CLI is synchronous; blocks until operation completes |
| Flask routes ↔ SessionManager | Direct method calls (Flask thread → SessionManager with Lock) | SessionManager must be thread-safe |
| Flask SSE route ↔ EventBus | `queue.Queue.get(timeout=30)` in generator | Timeout prevents thread leak on client disconnect |
| Background threads ↔ EventBus | `queue.Queue.put_nowait()` | Non-blocking put; drops event if queue full (acceptable for UI updates) |
| NativeMessagingHost ↔ SessionManager | Direct import and method call | Host runs in same Python process as the rest of the tool |
| TranscriptionService ↔ Engines | ABC method call (`engine.transcribe()`) | Engine instance cached; no subprocess boundary |
| GoogleDriveClient ↔ FileStore | Receives `wav_path` and `transcript_path` strings | Drive client does not know about SessionManager |

## Sources

- [sounddevice documentation](https://python-sounddevice.readthedocs.io/)
- [Chrome native messaging protocol](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Flask SSE without extra dependencies — Max Halford](https://maxhalford.github.io/blog/flask-sse-no-deps/)
- [faster-whisper on PyPI](https://pypi.org/project/faster-whisper/)
- [huggingface_hub download guide](https://huggingface.co/docs/huggingface_hub/guides/download)
- [Google Drive API Python quickstart](https://developers.google.com/drive/api/quickstart/python)
- [Recording macOS system audio with BlackHole — Medium](https://medium.com/@mehsamadi/how-to-record-mac-system-audio-using-python-and-blackhole-a45d06eaad0f)

---
*Architecture research for: Möte — macOS Swedish meeting transcription tool*
*Researched: 2026-03-27*
