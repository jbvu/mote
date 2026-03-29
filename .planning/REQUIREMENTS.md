# Requirements: Mote

**Defined:** 2026-03-27
**Core Value:** Accurate Swedish-language meeting transcription that actually works

## v1 Requirements

### Audio Capture

- [x] **AUD-01**: User can capture system audio from virtual meetings via BlackHole
- [x] **AUD-02**: User can start and stop recording via CLI command
- [x] **AUD-03**: User sees real-time audio level indicator during recording
- [x] **AUD-04**: User sees elapsed recording time during recording

### Transcription

- [x] **TRX-01**: User can transcribe recorded audio using local KBLab KB-Whisper models
- [x] **TRX-02**: User can transcribe recorded audio using OpenAI Whisper API
- [x] **TRX-03**: User can select transcription engine via config or CLI flag
- [x] **TRX-04**: User can select language (sv, no, da, fi, en) via config or CLI flag
- [x] **TRX-05**: User sees transcription progress as percentage during processing
- [x] **TRX-06**: Transcription runs automatically after recording stops

### Model Management

- [x] **MOD-01**: User can list available and downloaded models
- [x] **MOD-02**: User can download a specific KB-Whisper model with progress display
- [x] **MOD-03**: User can delete a downloaded model
- [x] **MOD-04**: Tool refuses to transcribe locally if no model is downloaded and shows clear instructions

### Output

- [x] **OUT-01**: Transcripts are saved as Markdown files with timestamps
- [x] **OUT-02**: Transcripts are saved as plain text files
- [x] **OUT-03**: Output files use timestamped filenames with optional user-provided name
- [x] **OUT-04**: Temporary WAV files are cleaned up after successful transcription

### Configuration

- [x] **CFG-01**: User can configure defaults via TOML file at ~/.mote/config.toml
- [x] **CFG-02**: Config file is created with sensible defaults on first run
- [x] **CFG-03**: API keys can be set via environment variables or config file
- [x] **CFG-04**: Config file has restrictive permissions (600)

### CLI

- [ ] **CLI-01**: `mote record` starts recording with live status display
- [x] **CLI-02**: `mote models list/download/delete` manages transcription models
- [x] **CLI-03**: `mote config` views or edits configuration
- [ ] **CLI-04**: `mote status` shows current recording/transcription state
- [x] **CLI-05**: `mote list` shows recent transcripts
- [ ] **CLI-06**: Ctrl+C during recording gracefully stops and triggers transcription

### Project Setup

- [x] **SET-01**: Installable via `pip install` from GitHub repository
- [x] **SET-02**: pyproject.toml with all dependencies and entry point
- [x] **SET-03**: Makefile for common operations (setup, run, test, clean)
- [x] **SET-04**: pytest test suite with fixtures

## v2.0 Requirements

### CLI & Reliability

- [x] **CLI-07**: User can transcribe an existing WAV file via `mote transcribe <file>` with same engine/language flags as `mote record`
- [ ] **CLI-08**: On transcription failure, user is prompted to retry with kept WAV; orphaned WAVs detected on next `mote record` and offered for transcription
- [x] **REL-01**: Config is validated on startup — invalid engine names, missing models, malformed paths caught early; absent v2 keys in v1 configs get silent defaults
- [x] **INT-02**: User can get JSON output format alongside Markdown and plain text

### Audio

- [ ] **AUD-05**: Audio output auto-switches to BlackHole before recording and restores original after; graceful degradation if SwitchAudioSource not installed
- [ ] **AUD-06**: User is warned if sustained silence (>30s) detected during recording; does not stop recording

### Integration

- [ ] **INT-03**: User can configure transcript destinations via `[destinations]` config section and `--destination` flag
- [ ] **INT-04**: User can upload transcripts to Google Drive via `mote auth google` (one-time OAuth2 browser consent) + automatic upload after transcription
- [ ] **INT-05**: User can upload transcripts to NotebookLM via `mote auth notebooklm` (experimental — unofficial API via notebooklm-py, sessions expire weekly)

## v3+ Requirements

### Cloud Engines

- **VXT-01**: User can transcribe using Mistral Voxtral API (pending Swedish WER verification)

### Web Interface

- **WEB-01**: Web dashboard with recording controls and live status via SSE
- **WEB-02**: Settings page for configuration management
- **WEB-03**: Model management page with download progress

### Chrome Extension

- **EXT-01**: Chrome extension for one-click recording control
- **EXT-02**: Native messaging host for extension-to-tool communication

### Speaker Identification

- **SPK-01**: Speaker diarization — identify and label different speakers in transcripts

### Language

- **LNG-01**: Norwegian, Danish, Finnish language support with appropriate models

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time live transcription | Doubles complexity; faster-whisper optimized for batch, not streaming |
| Speaker diarization | Moved to v3+ (SPK-01) — Swedish accuracy and processing time concerns remain |
| Multi-user auth for web UI | Binds to localhost; zero threat model for personal tool |
| Auto-start on meeting detection | Fragile OS-level hooks; privacy/consent concerns |
| Auto-download models | Large files (up to 3 GB) without consent is bad UX |
| Video/screen recording | 50-100x file sizes; irrelevant for transcription |
| Cloud SaaS version | Different product entirely; defeats privacy advantage |
| In-person mic capture | Different audio routing; deferred to future milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SET-01 | Phase 1 | Complete |
| SET-02 | Phase 1 | Complete |
| SET-03 | Phase 1 | Complete |
| SET-04 | Phase 1 | Complete |
| CFG-01 | Phase 1 | Complete |
| CFG-02 | Phase 1 | Complete |
| CFG-03 | Phase 1 | Complete |
| CFG-04 | Phase 1 | Complete |
| AUD-01 | Phase 2 | Complete |
| AUD-02 | Phase 2 | Complete |
| AUD-03 | Phase 2 | Complete |
| AUD-04 | Phase 2 | Complete |
| CLI-01 | Phase 2 | Pending |
| CLI-04 | Phase 2 | Pending |
| CLI-06 | Phase 2 | Pending |
| MOD-01 | Phase 3 | Complete |
| MOD-02 | Phase 3 | Complete |
| MOD-03 | Phase 3 | Complete |
| MOD-04 | Phase 3 | Complete |
| CLI-02 | Phase 3 | Complete |
| TRX-01 | Phase 4 | Complete |
| TRX-02 | Phase 4 | Complete |
| TRX-03 | Phase 4 | Complete |
| TRX-04 | Phase 4 | Complete |
| TRX-05 | Phase 4 | Complete |
| TRX-06 | Phase 4 | Complete |
| CLI-03 | Phase 4 | Complete |
| OUT-01 | Phase 5 | Complete |
| OUT-02 | Phase 5 | Complete |
| OUT-03 | Phase 5 | Complete |
| OUT-04 | Phase 5 | Complete |
| CLI-05 | Phase 5 | Complete |
| REL-01 | Phase 6 | Complete |
| INT-02 | Phase 6 | Complete |
| CLI-07 | Phase 6 | Complete |
| CLI-08 | Phase 6 | Pending |
| AUD-05 | Phase 7 | Pending |
| AUD-06 | Phase 7 | Pending |
| INT-03 | Phase 8 | Pending |
| INT-04 | Phase 8 | Pending |
| INT-05 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 32 total, all complete
- v2.0 requirements: 9 total, pending
- Mapped to phases: 32 (v1), 9 (v2.0)

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-28 — v2.0 traceability mapped to phases 6-9*
