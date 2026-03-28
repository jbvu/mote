# Roadmap: Möte

## Overview

Möte is built in five phases, each delivering a coherent, independently verifiable capability. The order is forced by dependencies: the project foundation comes first (config, packaging, test harness), then audio capture (the physical pipeline into BlackHole), then model management (models must exist before local transcription runs), then the transcription engine (the core differentiator), and finally output formatting and transcript management (completing the capture-to-file workflow). After all five phases, `mote record` captures a meeting, transcribes it in Swedish via KB-Whisper or OpenAI, and writes Markdown/text output ready for Google Drive.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Project scaffolding and configuration system
- [x] **Phase 2: Audio Capture** - BlackHole recording with live status feedback (completed 2026-03-27)
- [x] **Phase 3: Model Management** - Download, list, and delete KB-Whisper models (completed 2026-03-28)
- [x] **Phase 4: Transcription Engine** - Local KB-Whisper and OpenAI Whisper transcription (completed 2026-03-28)
- [ ] **Phase 5: Output and Transcript Management** - Formatted output files and transcript listing

## Phase Details

### Phase 1: Foundation
**Goal**: The project is installable, testable, and has a working configuration system that all later phases can build on
**Depends on**: Nothing (first phase)
**Requirements**: SET-01, SET-02, SET-03, SET-04, CFG-01, CFG-02, CFG-03, CFG-04
**Success Criteria** (what must be TRUE):
  1. User can install Möte from GitHub with `pip install git+https://github.com/...` and run `mote --help`
  2. On first run, `~/.mote/config.toml` is created with sensible defaults and permissions 600
  3. User can view and edit configuration via `mote config` command
  4. `make test` runs the pytest suite and all tests pass in a clean environment
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffolding: pyproject.toml, CLI skeleton, Makefile, test harness
- [x] 01-02-PLAN.md — Configuration system: config module, CLI config commands, full test coverage
- [x] 01-03-PLAN.md — Gap closure: fix make test failure on iCloud Drive paths with spaces

### Phase 2: Audio Capture
**Goal**: User can record a meeting's system audio via BlackHole with live feedback confirming audio is flowing
**Depends on**: Phase 1
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04, CLI-01, CLI-04, CLI-06
**Success Criteria** (what must be TRUE):
  1. `mote record` starts recording and shows a live audio level indicator and elapsed time in the terminal
  2. Pressing Ctrl+C stops recording gracefully and a WAV file is written to disk
  3. `mote status` shows whether a recording is in progress or idle
  4. If BlackHole 2ch is not detected, recording refuses to start with a clear error message
**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — Audio core module: BlackHole detection, recording engine, WAV writing, PID management, display helpers
- [x] 02-02-PLAN.md — CLI commands: mote record and mote status with hardware verification checkpoint

### Phase 3: Model Management
**Goal**: User can manage KB-Whisper models on disk so local transcription has a model to use
**Depends on**: Phase 1
**Requirements**: MOD-01, MOD-02, MOD-03, MOD-04, CLI-02
**Success Criteria** (what must be TRUE):
  1. `mote models list` shows all available KB-Whisper model sizes and marks which are downloaded
  2. `mote models download <name>` downloads the chosen model with a progress bar showing size and percentage
  3. `mote models delete <name>` removes a downloaded model from disk
  4. Attempting local transcription with no model downloaded shows a clear error with download instructions
**Plans:** 1/1 plans complete

Plans:
- [x] 03-01-PLAN.md — Model management: list/download/delete KB-Whisper models with Rich UI

### Phase 4: Transcription Engine
**Goal**: User can transcribe a recorded WAV file into Swedish text using local KB-Whisper or OpenAI Whisper as fallback
**Depends on**: Phase 2, Phase 3
**Requirements**: TRX-01, TRX-02, TRX-03, TRX-04, TRX-05, TRX-06, CLI-03
**Success Criteria** (what must be TRUE):
  1. After `mote record` stops, transcription starts automatically and shows progress as a percentage
  2. `mote config` lets user select between local KB-Whisper and OpenAI Whisper API as the active engine
  3. User can override the engine per-recording with a CLI flag (e.g., `mote record --engine openai`)
  4. User can set the language (sv, no, da, fi, en) via config or a CLI flag
  5. Transcription completes and produces a result file without leaving the WAV file on disk
**Plans:** 2/2 plans complete

Plans:
- [x] 04-01-PLAN.md — Core transcription module: transcribe.py with local/OpenAI engines, config fix, openai dependency
- [x] 04-02-PLAN.md — CLI integration: wire transcription into record command with engine/language/no-transcribe flags

### Phase 5: Output and Transcript Management
**Goal**: Transcription results are written as well-named Markdown and plain text files, and the user can list past transcripts
**Depends on**: Phase 4
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. After transcription, a Markdown file with timestamps and a plain text file are written to the output directory
  2. Output filenames include a timestamp and optionally a user-provided name (e.g., `2026-03-27_standup.md`)
  3. `mote list` shows recent transcripts with their filenames and timestamps
  4. The temporary WAV file is deleted after successful transcription and not left on disk after any exit path
**Plans:** 1 plan

Plans:
- [ ] 05-01-PLAN.md — Output formatting and transcript management (TBD)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/3 | Gap closure planned | - |
| 2. Audio Capture | 2/2 | Complete   | 2026-03-27 |
| 3. Model Management | 1/1 | Complete   | 2026-03-28 |
| 4. Transcription Engine | 2/2 | Complete   | 2026-03-28 |
| 5. Output and Transcript Management | 0/TBD | Not started | - |
