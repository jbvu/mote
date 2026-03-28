---
phase: 04-transcription-engine
plan: 01
subsystem: transcription
tags: [transcription, faster-whisper, openai, kblab, wav-chunking, config]
dependency_graph:
  requires: []
  provides: [transcribe_file, transcribe_local, transcribe_openai, get_wav_duration, _split_wav]
  affects: [src/mote/transcribe.py, src/mote/config.py, pyproject.toml]
tech_stack:
  added: [openai>=2.29.0]
  patterns: [lazy-imports, try-finally-cleanup, rich-progress-bar, stdlib-wave-chunking]
key_files:
  created:
    - src/mote/transcribe.py
    - tests/test_transcribe.py
  modified:
    - pyproject.toml
    - src/mote/config.py
    - tests/test_config.py
decisions:
  - Lazy imports for WhisperModel and OpenAI inside functions to avoid slow startup and missing-dep errors at import time
  - Segments concatenated with empty join (not space-join) since faster-whisper segments include their own leading space
  - OpenAI chunks joined with space-join after stripping to handle chunk boundary text cleanly
  - 830s threshold used in tests (not 800s) because 25MB = 819.2s at 16kHz mono 16-bit
metrics:
  duration: 309s
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_changed: 5
---

# Phase 4 Plan 1: Transcription Engine Core — Summary

**One-liner:** Local KB-Whisper and OpenAI Whisper engines with WAV chunking, Rich progress display, and fixed api_keys config section.

## What Was Built

### src/mote/transcribe.py
Full transcription module with five exported functions:
- `get_wav_duration(wav_path)` — reads WAV duration via stdlib `wave`
- `transcribe_local(wav_path, model_alias, language)` — KB-Whisper via faster-whisper with Rich progress bar, `device="cpu"`, `compute_type="int8"`
- `transcribe_openai(wav_path, language, api_key)` — OpenAI whisper-1 API with auto-chunking for files > 25MB, try/finally cleanup
- `_split_wav(wav_path, chunk_frames)` — stdlib WAV splitting into temp files
- `transcribe_file(wav_path, engine, language, model_alias, openai_api_key)` — dispatcher routing to local/openai, raises ClickException for unknown engine or missing API key

### pyproject.toml
Added `openai>=2.29.0` dependency. Installed as 2.30.0.

### src/mote/config.py
- Replaced commented-out `[api_keys]` block with real TOML table (`openai=""`, `mistral=""`)
- Added `transcription.language = "sv"` default to the transcription section
- Both changes make `mote config set api_keys.openai sk-...` work correctly (CLI-03 requirement)

### tests/test_transcribe.py
19 tests covering all behaviors from the plan including edge cases (chunking threshold, cleanup on failure, progress update values, unknown engine, missing API key).

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Lazy imports (WhisperModel, OpenAI inside functions) | Plan requirement; avoids slow startup and missing-dep errors at import time |
| `"".join(texts).strip()` for local segments | faster-whisper segments include leading space; space-joining produces double spaces |
| `" ".join(t.strip() for t in texts)` for OpenAI chunks | Cross-chunk text needs separator; strip each chunk's result cleanly |
| Test chunking threshold at 830s not 800s | 25MB = 819.2s at 16kHz/16bit; 800s = 24.4MB which is under the limit |
| Patch at source module paths | Lazy imports mean `mote.transcribe.WhisperModel` doesn't exist; patch `faster_whisper.WhisperModel` and `openai.OpenAI` directly |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed double-space in local transcription join**
- **Found during:** Task 2 GREEN phase testing
- **Issue:** `" ".join(texts).strip()` produces double spaces when faster-whisper segments include leading whitespace (e.g. `" världen"`)
- **Fix:** Changed to `"".join(texts).strip()` — preserves natural segment spacing
- **Files modified:** src/mote/transcribe.py
- **Commit:** 9876e8b

**2. [Rule 1 - Bug] Fixed chunking test threshold (800s < 25MB)**
- **Found during:** Task 2 GREEN phase testing
- **Issue:** 800s * 16000Hz * 2 bytes = 25,600,000 bytes < 26,214,400 bytes (25 * 1024 * 1024) — test WAV did not trigger chunking path
- **Fix:** Updated test to use 830s (> 819.2s threshold) and updated comments
- **Files modified:** tests/test_transcribe.py
- **Commit:** 9876e8b

**3. [Rule 1 - Bug] Fixed test patch targets for lazy imports**
- **Found during:** Task 2 GREEN phase testing
- **Issue:** `@patch("mote.transcribe.WhisperModel")` fails because WhisperModel is imported inside the function at call time, not at module load time
- **Fix:** Changed patch targets to source modules: `faster_whisper.WhisperModel`, `openai.OpenAI`, `mote.models.require_model_downloaded`
- **Files modified:** tests/test_transcribe.py
- **Commit:** 9876e8b

**4. [Rule 2 - Missing critical functionality] Updated test_env_var_does_not_persist_to_file**
- **Found during:** Task 1 — adding real api_keys table to config
- **Issue:** Existing test asserted `"api_keys" not in raw` which would fail once the config has a real api_keys section; the intent was to check env vars don't persist, not that the section is absent
- **Fix:** Updated assertion to `raw.get("api_keys", {}).get("openai", "") != "sk-should-not-be-written"`
- **Files modified:** tests/test_config.py
- **Commit:** 2c00ddc

## Test Results

- **Before:** 102 tests (phases 1-3)
- **After:** 121 tests (19 new in tests/test_transcribe.py)
- **Result:** All 121 pass

## Known Stubs

None — all functions are fully implemented with real logic.

## Self-Check: PASSED
