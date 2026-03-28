# Phase 4: Transcription Engine - Research

**Researched:** 2026-03-28
**Domain:** faster-whisper local transcription, OpenAI Whisper API, Rich progress display, WAV chunking
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Transcription runs inline in `record_command()` after WAV is written — single `mote record` does capture + transcribe
- **D-02:** Add `--no-transcribe` flag to `mote record` to skip auto-transcription and just save the WAV
- **D-03:** Delete WAV file after successful transcription. If transcription fails, keep the WAV for retry
- **D-04:** `--engine` flag on `mote record` overrides config default. Config key: `transcription.engine`, default value: `local`
- **D-05:** Two engines: `local` (KB-Whisper via faster-whisper) and `openai` (OpenAI Whisper API)
- **D-06:** Config default language is `sv` (Swedish). Config key: `transcription.language`
- **D-07:** `--language` flag on `mote record` overrides config default
- **D-08:** Supported languages: sv, no, da, fi, en. Language parameter is passed directly to the engine
- **D-09:** Local transcription shows time-based Rich progress bar — percentage calculated from (last_segment_end / total_wav_duration). Format: `Transcribing  42%  ████████▓░░░░░░░  02:15/05:22`
- **D-10:** OpenAI transcription shows indeterminate Rich spinner with chunk indicator if splitting: `Transcribing via OpenAI...  ⠋  (chunk 2/4)`
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRX-01 | User can transcribe recorded audio using local KBLab KB-Whisper models | faster-whisper WhisperModel with KBLab HF repo ID; `require_model_downloaded()` guard already exists in models.py |
| TRX-02 | User can transcribe recorded audio using OpenAI Whisper API | `client.audio.transcriptions.create(model="whisper-1", file=..., language=...)` pattern; `openai>=2.29.0` needs adding to pyproject.toml |
| TRX-03 | User can select transcription engine via config or CLI flag | Config key `transcription.engine` already in default config; `--engine` option on `record_command()` |
| TRX-04 | User can select language (sv, no, da, fi, en) via config or CLI flag | Config key `transcription.language` already in default config; `--language` option on `record_command()` |
| TRX-05 | User sees transcription progress as percentage during processing | faster-whisper yields segments with `.end` timestamps; divide by `TranscriptionInfo.duration` for percentage |
| TRX-06 | Transcription runs automatically after recording stops | Call `transcribe_file()` from `record_command()` after `record_session()` returns wav_path |
| CLI-03 | `mote config` views or edits configuration | `config` group already exists with `show/set/path` subcommands; this requirement is already met by existing code |
</phase_requirements>

---

## Summary

Phase 4 implements the transcription module that bridges recorded WAV files to text. The codebase is well-prepared: `transcribe.py` exists as an empty stub, `config.py` already has `transcription.engine` and `transcription.language` in the default config, and `models.py` provides the `require_model_downloaded()` guard. The architecture is function-based throughout — no class abstractions needed.

The core technical challenge is the faster-whisper progress pattern. `WhisperModel.transcribe()` returns a lazy generator — segments are not computed until iterated. Progress can be derived by tracking `segment.end` against `TranscriptionInfo.duration`, but `TranscriptionInfo` is the second item in the return tuple, not a pre-computed value available before iteration starts. The correct pattern is to read WAV duration from the file using `wave.getnframes() / wave.getframerate()` before calling transcribe, then drive progress from segment timestamps as segments yield.

OpenAI chunking requires WAV splitting using the stdlib `wave` module: read frames in `chunk_size_frames` blocks (12 min = 11,520,000 frames at 16kHz), write each to a temp file, send to API, concatenate text results, delete temp files. At 16kHz mono 16-bit, 12 minutes = 21.97MB, safely under the 25MB limit. The `openai>=2.29.0` package is not yet in pyproject.toml and must be added.

CLI-03 (mote config) is already fully implemented — the existing `config show/set/path` commands satisfy the requirement. No new work needed.

**Primary recommendation:** Implement `transcribe.py` with two functions (`transcribe_local` and `transcribe_openai`) plus a dispatcher (`transcribe_file`). Wire into `record_command()` after `record_session()` returns. Add `--engine`, `--language`, and `--no-transcribe` options to `record_command()`. Add `openai>=2.29.0` to pyproject.toml.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| faster-whisper | 1.2.1 | Local KB-Whisper transcription | Already in pyproject.toml; CTranslate2 backend; loads KBLab models by HF repo ID directly |
| openai | >=2.29.0 | OpenAI Whisper API fallback | Official SDK; `client.audio.transcriptions.create()` pattern; must be ADDED to pyproject.toml |
| wave (stdlib) | 3.11+ stdlib | WAV duration reading + chunking | No deps; `getnframes()/getframerate()` gives exact duration; `writeframes()` for chunk creation |
| rich | 14.3.3 (installed) | Progress bar + spinner | Already used in audio.py (Live) and models.py (tqdm.rich); Progress widget for deterministic bar |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tempfile (stdlib) | stdlib | Temp chunk files for OpenAI splitting | `tempfile.mkstemp()` for chunk WAV files; always cleaned up in finally block |
| pathlib (stdlib) | stdlib | File path handling | Already the project standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib wave for duration | soundfile or librosa | stdlib is zero-dep and sufficient for duration + splitting; soundfile/librosa add deps with no benefit |
| Progress widget for local bar | Live + custom Text | Progress widget gives accurate time columns; simpler than manual Live+Text for percentage display |
| Fixed-interval chunking | silence-based chunking | D-12 locks fixed intervals; Whisper handles mid-sentence well; silence detection adds complexity |

**Installation (what to add to pyproject.toml):**
```bash
uv add openai>=2.29.0
```

**Current pyproject.toml dependencies are:** click>=8.3, tomlkit>=0.13, sounddevice>=0.5.5, numpy>=2.0, faster-whisper>=1.2.1, onnxruntime<1.24, rich>=13.
`openai` is missing and must be added before the OpenAI engine can be used.

---

## Architecture Patterns

### Recommended Project Structure

The transcription module stays in `src/mote/transcribe.py`. No new files needed beyond tests.

```
src/mote/
├── transcribe.py    # Engine functions + dispatcher (currently empty stub)
├── cli.py           # record_command() integration point
├── config.py        # Already has transcription.engine/language defaults
└── models.py        # require_model_downloaded() guard already implemented
```

### Pattern 1: Segment-based Progress for Local Transcription

**What:** faster-whisper returns a lazy generator + TranscriptionInfo. The total duration must be known before iteration to compute percentages. Read WAV duration from file first, then drive Rich Progress from `segment.end`.

**When to use:** Always for `transcribe_local()`.

```python
# Source: verified against faster-whisper 1.2.1 installed in .venv
import wave
from pathlib import Path
from faster_whisper import WhisperModel
from rich.progress import Progress, BarColumn, TaskProgressColumn, TimeRemainingColumn, TextColumn

def transcribe_local(wav_path: Path, model_alias: str, language: str) -> str:
    from mote.models import MODELS, require_model_downloaded
    require_model_downloaded(model_alias)

    # Read WAV duration before transcription (wave stdlib, no deps)
    with wave.open(str(wav_path)) as wf:
        total_duration = wf.getnframes() / wf.getframerate()

    model = WhisperModel(MODELS[model_alias], device="cpu", compute_type="int8")
    segments_gen, info = model.transcribe(wav_path, language=language)

    texts = []
    with Progress(
        TextColumn("Transcribing"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("", total=total_duration)
        for segment in segments_gen:
            texts.append(segment.text)
            progress.update(task, completed=segment.end)

    return " ".join(texts).strip()
```

**Key facts verified from installed faster-whisper 1.2.1:**
- `model.transcribe()` returns `(Iterable[Segment], TranscriptionInfo)`
- `Segment` fields: `id, seek, start, end, text, tokens, avg_logprob, compression_ratio, no_speech_prob, words, temperature`
- `TranscriptionInfo` fields: `language, language_probability, duration, duration_after_vad, all_language_probs, transcription_options, vad_options`
- `info.duration` exists but arrives alongside the generator, not before. Use stdlib `wave` to get total duration for progress bar denominator.
- `device="cpu"` and `compute_type="int8"` are the required settings per CLAUDE.md (CTranslate2 MPS is experimental on Apple Silicon)

### Pattern 2: OpenAI Chunked Transcription

**What:** Split WAV into <=12-min chunks using stdlib `wave`, upload each to `client.audio.transcriptions.create()`, concatenate results.

**When to use:** For `transcribe_openai()`. Chunking only happens if file size > 25MB (verified math: 12 min * 60s * 16000 Hz * 2 bytes = 21.97 MB, safely under limit).

```python
# Source: verified against OpenAI docs (MEDIUM confidence — openai not yet installed)
import wave, tempfile, os
from pathlib import Path
from openai import OpenAI

OPENAI_CHUNK_FRAMES = 12 * 60 * 16000  # 12 minutes at 16kHz
OPENAI_LIMIT_BYTES = 25 * 1024 * 1024

def transcribe_openai(wav_path: Path, language: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)

    file_size = wav_path.stat().st_size
    if file_size <= OPENAI_LIMIT_BYTES:
        # Single-shot — no chunking needed
        with Progress(SpinnerColumn(), TextColumn("Transcribing via OpenAI...")) as progress:
            progress.add_task("")
            with open(wav_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-1", file=f, language=language
                )
        return result.text

    # Chunked path
    chunks = _split_wav(wav_path, OPENAI_CHUNK_FRAMES)
    texts = []
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("")
            for i, chunk_path in enumerate(chunks):
                progress.update(task, description=f"Transcribing via OpenAI...  (chunk {i+1}/{len(chunks)})")
                with open(chunk_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model="whisper-1", file=f, language=language
                    )
                texts.append(result.text)
    finally:
        for chunk_path in chunks:
            chunk_path.unlink(missing_ok=True)

    return " ".join(texts).strip()


def _split_wav(wav_path: Path, chunk_frames: int) -> list[Path]:
    """Split WAV into chunks of chunk_frames frames. Returns list of temp file paths."""
    chunk_paths = []
    with wave.open(str(wav_path)) as src:
        params = src.getparams()
        total_frames = src.getnframes()

        offset = 0
        while offset < total_frames:
            n = min(chunk_frames, total_frames - offset)
            src.setpos(offset)
            data = src.readframes(n)

            fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="mote_chunk_")
            os.close(fd)
            with wave.open(tmp, "wb") as dst:
                dst.setparams(params)
                dst.writeframes(data)
            chunk_paths.append(Path(tmp))
            offset += n

    return chunk_paths
```

### Pattern 3: Dispatcher + CLI Integration

**What:** A single `transcribe_file()` dispatcher reads engine/language from config (with CLI overrides), calls the appropriate engine function.

**When to use:** This is the interface that `record_command()` calls.

```python
# Pattern aligned with codebase's function-based style
def transcribe_file(
    wav_path: Path,
    engine: str,           # "local" or "openai"
    language: str,         # "sv", "no", "da", "fi", "en"
    model_alias: str,      # for local engine: "medium", "large", etc.
    openai_api_key: str | None = None,
) -> str:
    """Dispatch to the appropriate engine and return transcript text."""
    if engine == "local":
        return transcribe_local(wav_path, model_alias, language)
    elif engine == "openai":
        if not openai_api_key:
            raise click.ClickException(
                "OpenAI API key not set.\n"
                "Set it with: mote config set api_keys.openai sk-...\n"
                "Or set OPENAI_API_KEY environment variable."
            )
        return transcribe_openai(wav_path, language, openai_api_key)
    else:
        raise click.ClickException(f"Unknown engine '{engine}'. Choose: local, openai")
```

**CLI integration in `record_command()`:**
```python
@cli.command("record")
@click.option("--engine", type=click.Choice(["local", "openai"]), default=None,
              help="Transcription engine (overrides config).")
@click.option("--language", type=click.Choice(["sv", "no", "da", "fi", "en"]), default=None,
              help="Language code (overrides config).")
@click.option("--no-transcribe", is_flag=True, default=False,
              help="Save WAV only, skip transcription.")
def record_command(engine, language, no_transcribe):
    ...
    wav_path = record_session(device_index, recordings_dir, pid_path)

    if no_transcribe:
        click.echo(f"Recording saved: {wav_path}")
        return

    cfg = load_config()
    resolved_engine = engine or cfg.get("transcription", {}).get("engine", "local")
    resolved_language = language or cfg.get("transcription", {}).get("language", "sv")
    model_alias = config_value_to_alias(cfg.get("transcription", {}).get("model", "kb-whisper-medium")) or "medium"
    api_key = cfg.get("api_keys", {}).get("openai")

    try:
        transcript = transcribe_file(wav_path, resolved_engine, resolved_language, model_alias, api_key)
        wav_path.unlink()  # D-03: delete after success
        # Phase 5 will save transcript to file; for now return it
        # Temporary: print word count summary
        word_count = len(transcript.split())
        # Duration for summary
        click.echo(f"Transcription complete ({word_count:,} words)")
    except Exception as e:
        # D-03: keep WAV on failure for retry
        raise click.ClickException(f"Transcription failed: {e}\nWAV kept at: {wav_path}")
```

### Anti-Patterns to Avoid

- **Calling `model.transcribe()` and reading `info.duration` for progress denominator:** `info` arrives with the generator tuple, but segments are lazy. The duration IS available in `info` before iteration — however, using stdlib `wave` is simpler and doesn't require the generator to be set up first. Either approach works; `wave` is preferred for clarity.
- **Loading WhisperModel at module import time:** WhisperModel loading is slow (GB from disk). Load inside the function call, not at import.
- **Using `log_progress=True` in `WhisperModel.transcribe()`:** This prints tqdm to stderr instead of Rich-integrated output. Always use `log_progress=False` (the default) and drive Rich Progress from segment callbacks.
- **Using threading for transcription:** CLAUDE.md explicitly forbids threading for transcription — Python GIL contention. The record-then-transcribe sequential pattern is the design.
- **Using `openai-whisper` pip package:** CLAUDE.md explicitly forbids this. Always use `faster-whisper` for local and `openai` SDK for API.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WAV duration calculation | Custom byte-counting math | `wave.getnframes() / wave.getframerate()` | stdlib, exact, handles all WAV header variants |
| WAV file splitting | Custom byte slicing with header patching | stdlib `wave.readframes()` + `wave.writeframes()` | Handles WAV header, params, frame counting correctly |
| Progress display | Custom print/carriage-return loops | `rich.progress.Progress` with `BarColumn` + `TaskProgressColumn` | Already a dependency; handles terminal width, animation |
| API key retrieval | Custom env var parsing | `load_config()` already handles OPENAI_API_KEY env override | Pattern already established in config.py |
| Model path resolution | Custom HF cache lookup | `MODELS[alias]` dict already maps alias -> HF repo ID | Already in models.py |
| Model download guard | Re-implementing cache check | `require_model_downloaded(alias)` already in models.py | Already implemented; raises ClickException with instructions |

**Key insight:** Most of the infrastructure for this phase already exists. The work is connecting existing pieces through `transcribe.py`.

---

## Common Pitfalls

### Pitfall 1: WhisperModel Loaded with Wrong Device/compute_type

**What goes wrong:** Using `device="mps"` or `compute_type="float16"` causes crashes on Apple Silicon because CTranslate2's MPS backend is experimental.

**Why it happens:** Documentation shows GPU options; developers assume Apple Silicon = MPS = fast.

**How to avoid:** Always `device="cpu"` and `compute_type="int8"` per CLAUDE.md. int8 quantization on CPU is reliably fast on M-series chips.

**Warning signs:** `CTranslate2Error` or silent model load failure.

### Pitfall 2: faster-whisper Segment Generator Exhausted by Iteration

**What goes wrong:** Iterating `segments_gen` twice (e.g., once for progress, once for text) silently produces nothing on second pass — generators are single-pass.

**Why it happens:** The return type looks like an iterable but is a generator. Second iteration yields nothing.

**How to avoid:** Collect text inside a single iteration loop. Never separate the iteration from the text collection.

### Pitfall 3: OpenAI API Key Not Set Gives Cryptic Error

**What goes wrong:** `openai.AuthenticationError` is raised with a long traceback rather than a clear user message.

**Why it happens:** The OpenAI client raises on first API call, not at client construction.

**How to avoid:** Check for `api_key` being set before constructing the OpenAI client; raise `click.ClickException` with instructions if missing. The `load_config()` function already applies OPENAI_API_KEY env override — just check that the resulting value is non-empty.

### Pitfall 4: WAV Not Deleted on Transcription Exception

**What goes wrong:** D-03 says delete WAV after success, keep on failure. But uncaught exceptions in `record_command()` skip the delete. Orphaned WAV files accumulate.

**Why it happens:** Delete happens after transcription in linear code; exception skips it.

**How to avoid:** Use try/except in `record_command()`: on success, unlink WAV; on failure, log the WAV path clearly so user can retry. The exception should NEVER unlink the WAV.

### Pitfall 5: Temp Chunk Files Not Cleaned on OpenAI Network Error

**What goes wrong:** If an API call fails mid-chunking, temp WAV files remain in /tmp.

**Why it happens:** Normal code path deletes them, but exception exits early.

**How to avoid:** Use `try/finally` in `transcribe_openai()` — delete all chunk_paths regardless of success/failure.

### Pitfall 6: config.py `set_config_value` Rejects `api_keys.openai`

**What goes wrong:** `set_config_value("api_keys.openai", "sk-...")` raises `KeyError: Unknown config section: api_keys` because the default config has `api_keys` commented out, not as a live section.

**Why it happens:** The default config template has api_keys as comments (see `_write_default_config()` — it adds `tomlkit.comment("# openai = ...")` not a real section). `set_config_value()` raises on unknown sections.

**How to avoid:** Either (a) make `api_keys` a real (empty) table in `_write_default_config()`, or (b) handle the `api_keys` section specially in `set_config_value()`. This must be resolved for CLI-03 to work for API key configuration.

**Note:** This is a pre-existing issue in config.py that this phase must fix if users need to set API keys via `mote config set`.

### Pitfall 7: Language Code Passed Directly to OpenAI API

**What goes wrong:** OpenAI Whisper API requires ISO-639-1 codes. The project uses the same set (sv, no, da, fi, en) — these ARE valid ISO-639-1 codes, so no translation needed. But if the code set ever expands to non-standard codes, the API will reject them.

**Why it happens:** Assumption that project language codes == ISO-639-1 codes is currently correct but could drift.

**How to avoid:** Document explicitly that the 5 supported codes (sv, no, da, fi, en) are ISO-639-1 compliant. No mapping needed.

---

## Code Examples

### Reading WAV Duration (stdlib, verified)

```python
# Source: stdlib wave module — verified working in Python 3.13
import wave
from pathlib import Path

def get_wav_duration(wav_path: Path) -> float:
    """Return WAV duration in seconds."""
    with wave.open(str(wav_path)) as wf:
        return wf.getnframes() / wf.getframerate()
```

### Loading WhisperModel Correctly (verified against faster-whisper 1.2.1)

```python
# Source: CLAUDE.md + faster-whisper installed version
from faster_whisper import WhisperModel

model = WhisperModel(
    "KBLab/kb-whisper-medium",  # or MODELS[alias] from models.py
    device="cpu",
    compute_type="int8",
)
segments, info = model.transcribe(
    str(wav_path),
    language="sv",      # ISO-639-1 code
    log_progress=False, # Never use log_progress=True — bypasses Rich
)
```

### Rich Progress for Deterministic Percentage (verified imports)

```python
# Source: rich 14.3.3 installed in .venv — imports verified
from rich.progress import (
    Progress, BarColumn, TaskProgressColumn,
    TimeRemainingColumn, TextColumn, SpinnerColumn,
)

# Deterministic bar (local engine)
with Progress(
    TextColumn("Transcribing"),
    BarColumn(),
    TaskProgressColumn(),
    TimeRemainingColumn(),
) as progress:
    task = progress.add_task("", total=total_duration)
    for segment in segments:
        texts.append(segment.text)
        progress.update(task, completed=segment.end)

# Spinner (OpenAI engine)
with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
    task = progress.add_task("Transcribing via OpenAI...")
    # ... API calls, update description for chunk indicator
```

### Transcript Summary Print (after Phase 5 defers file-writing)

```python
# Phase 4 returns text string; Phase 5 writes to disk
# Summary line pattern from CONTEXT.md specifics:
word_count = len(transcript.split())
click.echo(f"Transcription complete ({word_count:,} words)")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| openai-whisper pip package (CPU-only) | faster-whisper (CTranslate2, int8) | 2022-2023 | 4x faster, same WER, required for KBLab models |
| Manual HF model download | WhisperModel loads by HF repo ID directly | faster-whisper 1.x | No conversion step needed |
| `gpt-4o-transcribe` as primary | `whisper-1` for Swedish (D-05 locked) | 2025 | gpt-4o-transcribe exists but whisper-1 is the locked choice |

**Deprecated/outdated:**
- `openai-whisper` pip package: CPU-only, no CTranslate2, cannot load KBLab ctranslate2 models. NEVER use.
- `oauth2client`: Deprecated since 2019 (not relevant to this phase, but in CLAUDE.md).

---

## Open Questions

1. **api_keys section in config is commented-out template**
   - What we know: `_write_default_config()` writes api_keys as comments, not a real TOML table. `set_config_value()` raises `KeyError` for unknown sections.
   - What's unclear: Should this phase fix `_write_default_config()` to include a real `[api_keys]` section, or should `set_config_value()` be made more permissive for `api_keys`?
   - Recommendation: Add `[api_keys]` as an empty real table in `_write_default_config()` with the openai and mistral keys defaulting to empty string `""`. This is the minimal change that makes `mote config set api_keys.openai sk-...` work.

2. **CLI-03 is already implemented**
   - What we know: `config show/set/path` subcommands exist and pass tests. REQUIREMENTS.md marks CLI-03 as Pending.
   - What's unclear: Is CLI-03's "pending" status a tracking artifact, or does it require new subcommands?
   - Recommendation: CLI-03 is satisfied by existing code. The planner should mark it as met in verification but not create new tasks for it. The only CLI-03 gap is the api_keys config issue above.

3. **Phase 5 boundary: transcript return value**
   - What we know: Phase 5 handles output file writing. Phase 4 must return transcript text to the caller.
   - What's unclear: Should `transcribe_file()` return a plain string, or a dataclass with metadata (language detected, duration, word count)?
   - Recommendation: Return a plain string for Phase 4. A dataclass can be introduced in Phase 5 if the output module needs metadata. This keeps Phase 4 minimal and functional.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| faster-whisper | TRX-01 (local engine) | Yes | 1.2.1 | — |
| openai Python SDK | TRX-02 (OpenAI engine) | No | not installed | Add to pyproject.toml as optional or required dep |
| rich | Progress display | Yes | 14.3.3 | — |
| wave (stdlib) | WAV duration + splitting | Yes | stdlib 3.13 | — |
| Python 3.13 | Runtime | Yes | 3.13 (venv) | — |
| KBLab model downloaded | TRX-01 execution | Not checked | — | `require_model_downloaded()` guards this — raises with instructions |

**Missing dependencies with no fallback:**
- `openai>=2.29.0`: Must be added to `pyproject.toml` and installed before the OpenAI engine can be tested. Add with `uv add openai>=2.29.0`.

**Missing dependencies with fallback:**
- KBLab model not downloaded: `require_model_downloaded()` raises `ClickException` with clear instructions. Graceful degradation built in.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=["tests"], pythonpath=["src"]) |
| Quick run command | `uv run --no-sync pytest tests/test_transcribe.py -q` |
| Full suite command | `uv run --no-sync pytest tests/ -q` |

**Baseline:** 102 tests pass before Phase 4 work begins.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRX-01 | Local engine calls WhisperModel with correct args | unit | `pytest tests/test_transcribe.py::test_transcribe_local_calls_model -x` | No — Wave 0 |
| TRX-01 | `require_model_downloaded()` guard blocks transcription if no model | unit | `pytest tests/test_transcribe.py::test_transcribe_local_no_model -x` | No — Wave 0 |
| TRX-02 | OpenAI engine calls `client.audio.transcriptions.create` | unit | `pytest tests/test_transcribe.py::test_transcribe_openai_calls_api -x` | No — Wave 0 |
| TRX-02 | OpenAI chunking splits large WAV into multiple API calls | unit | `pytest tests/test_transcribe.py::test_transcribe_openai_chunking -x` | No — Wave 0 |
| TRX-02 | Missing API key raises ClickException | unit | `pytest tests/test_transcribe.py::test_transcribe_openai_no_key -x` | No — Wave 0 |
| TRX-03 | Engine selection from config default | unit | `pytest tests/test_transcribe.py::test_engine_from_config -x` | No — Wave 0 |
| TRX-03 | `--engine` CLI flag overrides config | unit | `pytest tests/test_cli.py::test_record_engine_flag -x` | No — Wave 0 |
| TRX-04 | Language selection from config default | unit | `pytest tests/test_transcribe.py::test_language_from_config -x` | No — Wave 0 |
| TRX-04 | `--language` CLI flag overrides config | unit | `pytest tests/test_cli.py::test_record_language_flag -x` | No — Wave 0 |
| TRX-05 | Progress updates during local transcription | unit | `pytest tests/test_transcribe.py::test_local_progress_updates -x` | No — Wave 0 |
| TRX-06 | Auto-transcription called after record_session | unit | `pytest tests/test_cli.py::test_record_auto_transcribes -x` | No — Wave 0 |
| TRX-06 | WAV deleted after successful transcription (D-03) | unit | `pytest tests/test_cli.py::test_record_deletes_wav_on_success -x` | No — Wave 0 |
| TRX-06 | WAV kept after failed transcription (D-03) | unit | `pytest tests/test_cli.py::test_record_keeps_wav_on_failure -x` | No — Wave 0 |
| TRX-06 | `--no-transcribe` skips transcription and keeps WAV | unit | `pytest tests/test_cli.py::test_record_no_transcribe_flag -x` | No — Wave 0 |
| CLI-03 | `mote config set/show/path` already work | unit | `pytest tests/test_cli.py::test_config_show -x` | Yes |

### Sampling Rate

- **Per task commit:** `uv run --no-sync pytest tests/test_transcribe.py -q`
- **Per wave merge:** `uv run --no-sync pytest tests/ -q`
- **Phase gate:** Full suite green (102 + new tests) before `/gsd:verify-work`

### Wave 0 Gaps

- `tests/test_transcribe.py` — new file covering all TRX requirements
- New test cases in `tests/test_cli.py` — `test_record_engine_flag`, `test_record_language_flag`, `test_record_auto_transcribes`, `test_record_deletes_wav_on_success`, `test_record_keeps_wav_on_failure`, `test_record_no_transcribe_flag`

---

## Project Constraints (from CLAUDE.md)

The following directives apply to this phase:

| Directive | Impact on Phase 4 |
|-----------|-------------------|
| `device="cpu"` and `compute_type="int8"` for WhisperModel | Hard requirement; never use "mps" or "float16" |
| No threading for audio + transcription | Sequential pattern only: record → transcribe |
| Do not use `openai-whisper` pip package | Use `faster-whisper` for local; `openai` SDK for API |
| `MOTE_HOME` env var for test isolation | All tests must use `mote_home` fixture from conftest.py |
| `ClickException` for user-facing errors | API key missing, model not downloaded, unknown engine |
| Function-based modules (no classes) | `transcribe.py` uses plain functions, not Protocol/ABC |
| Config file permissions 600 | Not modified in this phase (config.py handles it) |
| `load_config()` already applies env var overrides for API keys | Do not re-implement env var reading; call `load_config()` |

---

## Sources

### Primary (HIGH confidence)
- faster-whisper 1.2.1 installed in `.venv` — `WhisperModel.transcribe()` signature and return types verified by direct introspection
- Python stdlib `wave` module — `getnframes()`, `getframerate()`, `readframes()`, `writeframes()` pattern verified by running in `.venv`
- `src/mote/models.py` — `require_model_downloaded()`, `MODELS` dict, `config_value_to_alias()` confirmed by direct read
- `src/mote/config.py` — `load_config()` with env var override, default config structure confirmed by direct read
- `src/mote/cli.py` — `record_command()` integration point confirmed by direct read
- rich 14.3.3 installed — `Progress`, `BarColumn`, `TaskProgressColumn`, `SpinnerColumn`, `TextColumn` imports verified

### Secondary (MEDIUM confidence)
- OpenAI `client.audio.transcriptions.create(model="whisper-1", file=..., language=...)` pattern — from OpenAI docs (platform.openai.com) via WebSearch; `openai` not installed in venv so not directly verified
- WAV file size math: 16kHz * 1ch * 2 bytes = 32000 bytes/sec = 1.83MB/min; 12 min = 21.97MB < 25MB — verified by calculation

### Tertiary (LOW confidence)
- None — all critical claims verified by primary sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — faster-whisper, wave, rich all verified in installed venv; openai MEDIUM (not installed but well-documented)
- Architecture: HIGH — verified against actual installed API signatures, existing codebase patterns
- Pitfalls: HIGH — most derived from reading actual source code (config.py api_keys issue directly observed)

**Research date:** 2026-03-28
**Valid until:** 2026-04-27 (stable libraries; faster-whisper and openai change infrequently at patch level)
