# Requirements: Mote

**Defined:** 2026-03-27
**Core Value:** Accurate Swedish-language meeting transcription that actually works

## v1 Requirements

### Audio Capture

- [ ] **AUD-01**: User can capture system audio from virtual meetings via BlackHole
- [ ] **AUD-02**: User can start and stop recording via CLI command
- [ ] **AUD-03**: User sees real-time audio level indicator during recording
- [ ] **AUD-04**: User sees elapsed recording time during recording

### Transcription

- [ ] **TRX-01**: User can transcribe recorded audio using local KBLab KB-Whisper models
- [ ] **TRX-02**: User can transcribe recorded audio using OpenAI Whisper API
- [ ] **TRX-03**: User can select transcription engine via config or CLI flag
- [ ] **TRX-04**: User can select language (sv, no, da, fi, en) via config or CLI flag
- [ ] **TRX-05**: User sees transcription progress as percentage during processing
- [ ] **TRX-06**: Transcription runs automatically after recording stops

### Model Management

- [ ] **MOD-01**: User can list available and downloaded models
- [ ] **MOD-02**: User can download a specific KB-Whisper model with progress display
- [ ] **MOD-03**: User can delete a downloaded model
- [ ] **MOD-04**: Tool refuses to transcribe locally if no model is downloaded and shows clear instructions

### Output

- [ ] **OUT-01**: Transcripts are saved as Markdown files with timestamps
- [ ] **OUT-02**: Transcripts are saved as plain text files
- [ ] **OUT-03**: Output files use timestamped filenames with optional user-provided name
- [ ] **OUT-04**: Temporary WAV files are cleaned up after successful transcription

### Configuration

- [ ] **CFG-01**: User can configure defaults via TOML file at ~/.mote/config.toml
- [ ] **CFG-02**: Config file is created with sensible defaults on first run
- [ ] **CFG-03**: API keys can be set via environment variables or config file
- [ ] **CFG-04**: Config file has restrictive permissions (600)

### CLI

- [ ] **CLI-01**: `mote record` starts recording with live status display
- [ ] **CLI-02**: `mote models list/download/delete` manages transcription models
- [ ] **CLI-03**: `mote config` views or edits configuration
- [ ] **CLI-04**: `mote status` shows current recording/transcription state
- [ ] **CLI-05**: `mote list` shows recent transcripts
- [ ] **CLI-06**: Ctrl+C during recording gracefully stops and triggers transcription

### Project Setup

- [ ] **SET-01**: Installable via `pip install` from GitHub repository
- [ ] **SET-02**: pyproject.toml with all dependencies and entry point
- [ ] **SET-03**: Makefile for common operations (setup, run, test, clean)
- [ ] **SET-04**: pytest test suite with fixtures

## v2 Requirements

### Cloud Engines

- **VXT-01**: User can transcribe using Mistral Voxtral API (pending Swedish WER verification)

### Web Interface

- **WEB-01**: Web dashboard with recording controls and live status via SSE
- **WEB-02**: Settings page for configuration management
- **WEB-03**: Model management page with download progress

### Chrome Extension

- **EXT-01**: Chrome extension for one-click recording control
- **EXT-02**: Native messaging host for extension-to-tool communication

### Integration

- **INT-01**: Push completed transcripts to Google Drive via API
- **INT-02**: JSON output format for machine consumption

### Language

- **LNG-01**: Norwegian, Danish, Finnish language support with appropriate models

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time live transcription | Doubles complexity; faster-whisper optimized for batch, not streaming |
| Speaker diarization | Poor Swedish accuracy, gated model access, 2-4x processing time |
| Multi-user auth for web UI | Binds to localhost; zero threat model for personal tool |
| Auto-start on meeting detection | Fragile OS-level hooks; privacy/consent concerns |
| Auto-download models | Large files (up to 3 GB) without consent is bad UX |
| Video/screen recording | 50-100x file sizes; irrelevant for transcription |
| Cloud SaaS version | Different product entirely; defeats privacy advantage |
| In-person mic capture | Different audio routing; deferred to future milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SET-01 | Phase 1 | Pending |
| SET-02 | Phase 1 | Pending |
| SET-03 | Phase 1 | Pending |
| SET-04 | Phase 1 | Pending |
| CFG-01 | Phase 1 | Pending |
| CFG-02 | Phase 1 | Pending |
| CFG-03 | Phase 1 | Pending |
| CFG-04 | Phase 1 | Pending |
| AUD-01 | Phase 2 | Pending |
| AUD-02 | Phase 2 | Pending |
| AUD-03 | Phase 2 | Pending |
| AUD-04 | Phase 2 | Pending |
| CLI-01 | Phase 2 | Pending |
| CLI-04 | Phase 2 | Pending |
| CLI-06 | Phase 2 | Pending |
| MOD-01 | Phase 3 | Pending |
| MOD-02 | Phase 3 | Pending |
| MOD-03 | Phase 3 | Pending |
| MOD-04 | Phase 3 | Pending |
| CLI-02 | Phase 3 | Pending |
| TRX-01 | Phase 4 | Pending |
| TRX-02 | Phase 4 | Pending |
| TRX-03 | Phase 4 | Pending |
| TRX-04 | Phase 4 | Pending |
| TRX-05 | Phase 4 | Pending |
| TRX-06 | Phase 4 | Pending |
| CLI-03 | Phase 4 | Pending |
| OUT-01 | Phase 5 | Pending |
| OUT-02 | Phase 5 | Pending |
| OUT-03 | Phase 5 | Pending |
| OUT-04 | Phase 5 | Pending |
| CLI-05 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 after roadmap creation*
