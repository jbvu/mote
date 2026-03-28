# Phase 4: Transcription Engine - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Local KB-Whisper and OpenAI Whisper API transcription of recorded WAV files. This phase delivers: a transcription module with engine dispatch, automatic transcription after recording stops, progress display, language selection, OpenAI chunking for long recordings, and CLI flags for engine/language override. Output is raw transcript text — formatting and file management belong to Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Auto-Transcribe Flow
- **D-01:** Transcription runs inline in `record_command()` after WAV is written — single `mote record` does capture + transcribe
- **D-02:** Add `--no-transcribe` flag to `mote record` to skip auto-transcription and just save the WAV
- **D-03:** Delete WAV file after successful transcription. If transcription fails, keep the WAV for retry

### Engine Selection
- **D-04:** `--engine` flag on `mote record` overrides config default. Config key: `transcription.engine`, default value: `local`
- **D-05:** Two engines: `local` (KB-Whisper via faster-whisper) and `openai` (OpenAI Whisper API)

### Language Handling
- **D-06:** Config default language is `sv` (Swedish). Config key: `transcription.language`
- **D-07:** `--language` flag on `mote record` overrides config default
- **D-08:** Supported languages: sv, no, da, fi, en. Language parameter is passed directly to the engine

### Progress Display
- **D-09:** Local transcription shows time-based Rich progress bar — percentage calculated from (last_segment_end / total_wav_duration). Format: `Transcribing  42%  ████████▓░░░░░░░  02:15/05:22`
- **D-10:** OpenAI transcription shows indeterminate Rich spinner with chunk indicator if splitting: `Transcribing via OpenAI...  (chunk 2/4)`

### OpenAI Chunking
- **D-11:** Auto-split WAV into ~12 min chunks when file exceeds 25MB limit. Split silently — user sees chunk counter but doesn't need to manage splitting
- **D-12:** Split at fixed time intervals (not silence-based). Whisper handles mid-sentence boundaries well with its own context windowing
- **D-13:** Concatenate chunk transcription results into one transcript. Clean up temp chunk files after

### Claude's Discretion
- Engine abstraction pattern (simple functions vs Protocol classes) — codebase leans functional
- Internal API of transcribe module (function signatures, return types)
- WAV duration parsing approach
- Error handling for missing API keys, network failures, model not downloaded
- Exact Rich widget choices for progress display
- How transcript text is returned to the caller (string, dataclass, dict)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Full technology stack: faster-whisper 1.2.1, openai 2.29.0, device="cpu" + compute_type="int8", KBLab model loading pattern, 25MB OpenAI file limit, what NOT to use (openai-whisper pip package, threading)
- `.planning/PROJECT.md` — Core value (Swedish transcription), constraints, key decisions
- `.planning/REQUIREMENTS.md` — TRX-01 through TRX-06 (transcription), CLI-03 (config command)

### Prior Phase Context
- `.planning/phases/02-audio-capture/02-CONTEXT.md` — WAV file location (~/.mote/recordings/), format (16kHz mono 16-bit), recording display patterns (Rich Live)
- `.planning/phases/03-model-management/03-01-SUMMARY.md` — models.py API: MODELS dict, require_model_downloaded(), download_model()

### Existing Code
- `src/mote/models.py` — `require_model_downloaded()` guard, `MODELS` dict with HF repo IDs, `config_value_to_alias()`
- `src/mote/config.py` — `load_config()` with env var override for API keys (OPENAI_API_KEY)
- `src/mote/audio.py` — `record_session()` returns wav_path, 16kHz/mono/16-bit constants
- `src/mote/cli.py` — `record_command()` integration point, existing `config` group with show/set/path

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models.py:require_model_downloaded()` — Gate function that blocks transcription when no model is downloaded, shows instructions. Use before local transcription
- `models.py:MODELS` — Maps alias to HF repo ID (e.g., "medium" -> "KBLab/kb-whisper-medium"). Use to load the correct model
- `models.py:config_value_to_alias()` — Resolves config values like "kb-whisper-medium" to alias "medium"
- `config.py:load_config()` — Returns config dict with `transcription.engine`, `transcription.model`, `transcription.language` keys. Env vars override API keys
- `audio.py:SAMPLE_RATE = 16000` — Constant for WAV format, reusable for duration calculation
- `cli.py:_human_size()` — Byte formatting helper, reusable for file size display

### Established Patterns
- Function-based modules (no classes in models.py, audio.py, config.py)
- Click decorator CLI with `@cli.command()` and `@cli.group()`
- Rich for terminal display (Live, Table, Console already imported in cli.py)
- `MOTE_HOME` env var for test isolation
- `ClickException` for user-facing errors

### Integration Points
- `cli.py:record_command()` — After `wav_path = record_session(...)`, add transcription call
- `transcribe.py` — Empty stub, ready for engine functions
- `config.py` — Already handles `transcription.model` reads; needs `transcription.engine` and `transcription.language` in defaults

</code_context>

<specifics>
## Specific Ideas

- Progress bar mockup: `Transcribing  42%  ████████▓░░░░░░░  02:15/05:22`
- OpenAI chunk display: `Transcribing via OpenAI...  ⠋  (chunk 2/4)`
- After transcription completes, print summary: "Transcription complete (5:22, 1,247 words)"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-transcription-engine*
*Context gathered: 2026-03-28*
