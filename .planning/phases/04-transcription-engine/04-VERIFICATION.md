---
phase: 04-transcription-engine
verified: 2026-03-28T00:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 4: Transcription Engine Verification Report

**Phase Goal:** User can transcribe a recorded WAV file into Swedish text using local KB-Whisper or OpenAI Whisper as fallback
**Verified:** 2026-03-28
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths — Plan 01

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `transcribe_local()` calls WhisperModel with device=cpu, compute_type=int8, correct KBLab repo ID, returns joined segment text | VERIFIED | `transcribe.py:38` — `WhisperModel(MODELS[model_alias], device="cpu", compute_type="int8")`; `test_transcribe_local_calls_model` asserts exact call args and result |
| 2 | `transcribe_openai()` calls client.audio.transcriptions.create with whisper-1 model and correct language | VERIFIED | `transcribe.py:69-71` — `model="whisper-1", file=f, language=language`; tested by `test_transcribe_openai_calls_api` |
| 3 | `transcribe_openai()` splits WAV into 12-min chunks when file exceeds 25MB and concatenates results | VERIFIED | `transcribe.py:75-97` — checks `file_size > OPENAI_LIMIT_BYTES`, calls `_split_wav(wav_path, OPENAI_CHUNK_FRAMES)`; tested by `test_transcribe_openai_chunking` |
| 4 | `transcribe_file()` dispatches to local or openai engine based on engine parameter | VERIFIED | `transcribe.py:132-143` — branches on `engine == "local"` / `engine == "openai"`; tested by `test_transcribe_file_dispatches_local` and `test_transcribe_file_dispatches_openai` |
| 5 | Missing OpenAI API key raises ClickException with instructions | VERIFIED | `transcribe.py:135-140` — raises `click.ClickException("OpenAI API key not set...")` when `not openai_api_key`; tested by `test_transcribe_openai_no_key` and `test_transcribe_openai_no_key_empty_string` |
| 6 | Missing local model raises ClickException via require_model_downloaded() | VERIFIED | `transcribe.py:35` — `require_model_downloaded(model_alias)` called before WhisperModel; tested by `test_transcribe_local_no_model` |
| 7 | `mote config set api_keys.openai` works without KeyError | VERIFIED | `config.py:87-91` — real `[api_keys]` table with `openai=""` and `mistral=""`; `set_config_value` traverses real table without KeyError |

### Observable Truths — Plan 02

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8 | `mote record` auto-transcribes after recording stops and shows progress | VERIFIED | `cli.py:149-157` — calls `transcribe_file()` then echoes `"Transcription complete (M:SS, N,NNN words)"`; tested by `test_record_auto_transcribes` |
| 9 | `mote record --engine openai` overrides config default engine | VERIFIED | `cli.py:139` — `resolved_engine = engine or cfg.get(...)`; tested by `test_record_engine_flag` asserting `call_args[0][1] == "openai"` |
| 10 | `mote record --language en` overrides config default language | VERIFIED | `cli.py:140` — `resolved_language = language or cfg.get(...)`; tested by `test_record_language_flag` asserting `call_args[0][2] == "en"` |
| 11 | `mote record --no-transcribe` saves WAV without transcribing | VERIFIED | `cli.py:135-136` — `if no_transcribe: return` before transcription block; tested by `test_record_no_transcribe_flag` asserting `mock_tx.assert_not_called()` and `wav.exists()` |
| 12 | WAV is deleted after successful transcription | VERIFIED | `cli.py:154` — `wav_path.unlink(missing_ok=True)` after `transcribe_file` returns; tested by `test_record_deletes_wav_on_success` asserting `not wav.exists()` |
| 13 | WAV is kept on disk if transcription fails | VERIFIED | `cli.py:158-163` — `except Exception as e: raise click.ClickException(f"...WAV kept at: {wav_path}")` without unlinking; tested by `test_record_keeps_wav_on_failure` asserting `wav.exists()` and `"WAV kept at" in result.output` |
| 14 | Summary line shows word count after transcription completes | VERIFIED | `cli.py:155-157` — `word_count = len(transcript.split())`, echoes `f"Transcription complete ({mins}:{secs:02d}, {word_count:,} words)"` |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mote/transcribe.py` | Engine functions and dispatcher | VERIFIED | 144 lines; exports `transcribe_file`, `transcribe_local`, `transcribe_openai`, `get_wav_duration`, `_split_wav` |
| `tests/test_transcribe.py` | Unit tests for all transcription functions (min 100 lines) | VERIFIED | 392 lines; 19 test functions covering all behaviors |
| `src/mote/config.py` | Fixed default config with real api_keys table | VERIFIED | Lines 87-91: real `[api_keys]` table; `transcription.language = "sv"` at line 78 |
| `src/mote/cli.py` | record_command with --engine, --language, --no-transcribe and auto-transcription | VERIFIED | Lines 80-163; contains all three options and full transcription flow |
| `tests/test_cli.py` | Tests for new CLI flags and auto-transcription behavior | VERIFIED | 6 new test functions at lines 204-304 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mote/transcribe.py` | `src/mote/models.py` | `from mote.models import` | WIRED | `transcribe.py:33` — `from mote.models import MODELS, require_model_downloaded` (lazy, inside function) |
| `src/mote/transcribe.py` | `faster_whisper` | `WhisperModel` import | WIRED | `transcribe.py:31` — `from faster_whisper import WhisperModel` (lazy, inside function) |
| `src/mote/transcribe.py` | `openai` | `OpenAI` client | WIRED | `transcribe.py:60` — `from openai import OpenAI` (lazy, inside function) |
| `src/mote/cli.py` | `src/mote/transcribe.py` | `transcribe_file` import and call | WIRED | `cli.py:25` — `from mote.transcribe import transcribe_file, get_wav_duration`; called at `cli.py:151` |
| `src/mote/cli.py` | `src/mote/models.py` | `config_value_to_alias` | WIRED | `cli.py:23` — `config_value_to_alias` imported; used at `cli.py:142` |
| `src/mote/cli.py` | `src/mote/config.py` | `load_config` | WIRED | `cli.py:8` — `load_config` imported; used at `cli.py:138` |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces a transcription engine (pure processing functions) and CLI integration, not a data-rendering component. No UI components rendering dynamic data from a store or API.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 127 tests pass | `uv run --no-sync pytest tests/ -q` | `127 passed in 2.50s` | PASS |
| transcribe.py module imports cleanly | `uv run --no-sync python -c "from mote.transcribe import transcribe_file, ..."` | `import OK` | PASS |
| `mote record --help` shows correct flags | `uv run --no-sync mote record --help` | Shows `--engine`, `--language`, `--no-transcribe` | PASS |
| 19 test functions in test_transcribe.py | `grep -c "def test_" tests/test_transcribe.py` | `19` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TRX-01 | Plan 01 | User can transcribe using local KBLab KB-Whisper models | SATISFIED | `transcribe_local()` calls `WhisperModel(MODELS[alias], device="cpu", compute_type="int8")` |
| TRX-02 | Plan 01 | User can transcribe using OpenAI Whisper API | SATISFIED | `transcribe_openai()` calls `client.audio.transcriptions.create(model="whisper-1")` |
| TRX-03 | Plan 01, 02 | User can select transcription engine via config or CLI flag | SATISFIED | `--engine` flag on `record_command`; `resolved_engine = engine or cfg.get("transcription", {}).get("engine", "local")` |
| TRX-04 | Plan 01, 02 | User can select language via config or CLI flag | SATISFIED | `--language` flag on `record_command`; `resolved_language = language or cfg.get(...)` |
| TRX-05 | Plan 01 | User sees transcription progress as percentage during processing | SATISFIED | `transcribe_local()` uses `Rich Progress` with `BarColumn`, `TaskProgressColumn`, `TimeRemainingColumn`; `transcribe_openai()` uses `SpinnerColumn` with chunk count |
| TRX-06 | Plan 02 | Transcription runs automatically after recording stops | SATISFIED | `cli.py:134-163` — auto-transcription block runs unconditionally after `record_session` unless `--no-transcribe` |
| CLI-03 | Plan 01 | `mote config` views or edits configuration | SATISFIED | Pre-existing; confirmed by `api_keys` table fix enabling `mote config set api_keys.openai sk-...` |

**Orphaned requirement check:** REQUIREMENTS.md maps the same 7 IDs (TRX-01 through TRX-06, CLI-03) to Phase 4. All 7 are claimed in plan frontmatter. No orphaned requirements.

---

### Anti-Patterns Found

No anti-patterns detected. Scanned `src/mote/transcribe.py`, `src/mote/cli.py`, `src/mote/config.py` for:
- TODO/FIXME/HACK/PLACEHOLDER comments — none found
- Empty implementations (`return null`, `return {}`, `return []`) — none found
- Hardcoded empty state passed to rendering — not applicable (no UI)
- Console.log-only handlers — not applicable (Python)

---

### Human Verification Required

#### 1. Live transcription of real Swedish audio

**Test:** Record a brief Swedish sentence using `mote record`, then stop; observe that transcription runs and produces readable Swedish text.
**Expected:** Transcript contains coherent Swedish words matching the spoken sentence; no garbage output.
**Why human:** Requires a running BlackHole audio device, a real microphone, and subjective assessment of Swedish transcription quality. Cannot be tested without live audio hardware.

#### 2. OpenAI engine with real API key

**Test:** Set `OPENAI_API_KEY` and run `mote record --engine openai` with a short recording.
**Expected:** Transcript returned from OpenAI Whisper API and displayed.
**Why human:** Requires valid OpenAI API credentials and network access; cannot be tested in isolation.

#### 3. Chunking behaviour on a real > 25MB WAV file

**Test:** Generate or use a WAV file exceeding 25MB (> ~820 seconds at 16kHz mono), then call `mote record --engine openai`.
**Expected:** Console output shows `(chunk 1/N)` and `(chunk 2/N)` etc.; final transcript merges all chunks.
**Why human:** Creating a real 25MB+ WAV in a unit test is slow; the unit test uses a mock for `_split_wav`. Needs live verification with real file and API.

---

### Gaps Summary

No gaps. All 14 must-have truths verified, all 5 required artifacts exist and are substantive, all 6 key links confirmed wired, all 7 requirements satisfied, full test suite (127 tests) passes.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
