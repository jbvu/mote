# Möte

## What This Is

Möte is a macOS meeting transcription tool built for Swedish and Scandinavian languages. It captures system audio from virtual meetings (Teams, Zoom, etc.) via BlackHole, transcribes using local or cloud-based engines, and delivers transcripts to Google Drive for further use in tools like NotebookLM. It provides a CLI, web UI, and Chrome extension as interfaces.

## Core Value

Accurate Swedish-language meeting transcription that actually works — no existing tool handles Swedish natively.

## Requirements

### Validated

- [x] TOML-based configuration with sensible defaults — Validated in Phase 1: Foundation
- [x] CLI entry point with command groups — Validated in Phase 1: Foundation
- [x] Manage local whisper models (download, delete, list) — Validated in Phase 3: Model Management
- [x] Transcribe Swedish audio using local KBLab whisper models — Validated in Phase 4: Transcription Engine
- [x] Transcribe via OpenAI Whisper API as alternative engine — Validated in Phase 4: Transcription Engine
- [x] Support Norwegian, Danish, Finnish, English alongside Swedish — Validated in Phase 4: Transcription Engine
- [x] Transcription progress reporting — Validated in Phase 4: Transcription Engine
- [x] Output transcripts as Markdown and plain text — Validated in Phase 5: Output and Transcript Management
- [x] List past transcripts via CLI — Validated in Phase 5: Output and Transcript Management

### Active (v2.0)

- [ ] Configurable transcript destinations (Google Drive, NotebookLM) via config + flag
- [ ] Google Drive upload via official API with OAuth2 (`mote auth google`)
- [ ] NotebookLM upload via `notebooklm-py` (`mote auth notebooklm`)
- [ ] `mote transcribe <file>` for existing WAV files
- [ ] Retry failed transcriptions + orphaned WAV detection
- [ ] Auto-switch BlackHole audio routing before/after recording
- [ ] Silence detection warning during recording
- [ ] Config validation on startup
- [ ] JSON output format

### Future (v3+)

- [ ] Web UI dashboard with recording controls and live status
- [ ] Web UI settings page for configuration
- [ ] Web UI model management with download progress
- [ ] Chrome extension for quick recording control
- [ ] Mistral Voxtral engine (pending Swedish support)
- [ ] Speaker diarization

### Out of Scope

- In-person meeting capture via Mac microphone — deferred to future milestone
- Real-time/live transcription during recording — batch only after stop
- Multi-speaker diarization — may revisit later
- Mobile app — macOS desktop only
- Authentication for web UI — binds to localhost only
- Auto-downloading models — explicit user action required

## Context

- The user regularly attends Swedish-language meetings on video conferencing platforms
- No existing transcription tool handles Swedish well as a first-class language
- KBLab provides Swedish-optimized whisper models (CTranslate2 format via faster-whisper)
- BlackHole is the standard macOS virtual audio device for capturing system audio
- Transcripts go to Google Drive for further processing (e.g., NotebookLM)
- This is a personal/developer tool — single user, local machine
- Distributed via GitHub — must be reproducible on other users' macOS setups
- Google Drive integration needs proper OAuth flow (not hardcoded credentials)

## Constraints

- **Platform**: macOS only — relies on BlackHole virtual audio device
- **Audio**: BlackHole 2ch must be installed (`brew install blackhole-2ch`)
- **Security**: Web UI binds to 127.0.0.1 only, config file permissions 600, no auth
- **Tech stack**: Python, Click CLI, Flask web server, faster-whisper for local models
- **Distribution**: Installable via `pip install` from GitHub; all dependencies in pyproject.toml
- **Storage**: WAV files ~1.9MB/min at 16kHz mono 16-bit; temp files cleaned after transcription

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| BlackHole for audio capture | Standard macOS virtual audio device, no kernel extensions | — Pending |
| faster-whisper over whisper.cpp | Python-native, CTranslate2 backend, good performance | Validated (Phase 4) |
| Flask over FastAPI | Simpler for SSE + template rendering, sufficient for single-user tool | — Pending |
| TOML config over YAML/JSON | Human-readable, good Python support, standard for Python tools | Validated (Phase 1) |
| SSE over WebSocket | Simpler for one-way server→client updates, no extra dependencies | — Pending |
| Google Drive API upload | Explicit push to GDrive rather than relying on local sync folder | — Pending |
| Distribute via GitHub | Tool should be reproducible on any macOS setup via pip install | — Pending |
| No auto-download of models | User should explicitly choose which models to download | Validated (Phase 3) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

## Current Milestone: v2.0 Integration & Polish

**Goal:** Connect Mote to external services (Google Drive, NotebookLM) and improve the CLI experience with transcribe-from-file, retry, auto-routing, and validation.

**Target features:**
- Configurable transcript destinations (Google Drive, NotebookLM)
- `mote transcribe <file>` for existing WAV files
- Retry failed transcriptions + orphaned WAV detection
- Auto-switch BlackHole audio routing
- Silence detection warning
- Config validation on startup
- JSON output format

---
*Last updated: 2026-03-29 — v2.0 milestone started, 152 passing tests from v1*
