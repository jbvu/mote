# Phase 6: CLI Polish and Config Reliability - Research

**Researched:** 2026-03-29
**Domain:** Click CLI patterns, Python config validation, JSON output, WAV file lifecycle, retention cleanup
**Confidence:** HIGH

## Summary

Phase 6 is a pure Python refactor-and-extend phase with no new external dependencies. The codebase already has all required libraries. The work decomposes into five orthogonal areas: (1) extract a `_run_transcription()` shared helper from `record_command`, (2) add a `mote transcribe <file>` command reusing that helper, (3) add config validation in `config.py` with automatic pre-flight and a manual `mote config validate` subcommand, (4) extend `write_transcript()` in `output.py` with a JSON format branch, and (5) add WAV retention cleanup (auto at `mote record` startup + `mote cleanup` command).

All five areas use patterns already present in the codebase — Click decorators, `click.confirm()` for interactive prompts, `ClickException` for user errors, `MOTE_HOME` isolation for tests. No new libraries are needed. The primary risk is in the refactor of `record_command()`: existing tests assert positional argument order to `write_transcript` (see `test_record_name_flag`) so the extracted helper must preserve the exact call signature.

**Primary recommendation:** Implement in five sequential waves matching the five areas above. Start with `_run_transcription()` extraction (wave 1) because all subsequent waves depend on it. Config validation (wave 3) must not break v1 configs — absent keys must silently default, only present-but-invalid values produce errors.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Retry & Recovery**
- D-01: When transcription fails, prompt the user interactively: "Retry transcription? [Y/n]" — yes retranscribes the kept WAV immediately. No separate retry command.
- D-02: Orphaned WAV files on `mote record` startup: keep the existing warning but enhance it to point to the `mote transcribe <file>` command. No interactive offer to transcribe orphans at record startup.

**Config Validation**
- D-03: Validate four things: engine name (must be 'local' or 'openai'), model availability (if engine=local, check model is downloaded), output dir writability (exists or can be created), API key presence (if engine=openai, warn if no key configured).
- D-04: Automatic validation runs before `mote record` and `mote transcribe` only — not on `mote list`, `mote config show`, etc.
- D-05: Also add a manual `mote config validate` command for explicit checking.
- D-06: Absent v2 config keys get silent defaults (per roadmap decision). Only present-but-invalid values produce errors.

**JSON Output**
- D-07: JSON structure is flat, mirroring YAML frontmatter fields: `date`, `duration`, `words`, `engine`, `language`, `model`, `transcript`. No segments array.
- D-08: JSON enabled via `--output-format json` flag or by adding "json" to config `output.format` list.

**Transcribe Command**
- D-09: `mote transcribe <file>` accepts a single WAV file only. No multi-file or glob support.
- D-10: Same `--engine`, `--language`, `--name`, `--output-format` flags as `mote record`.
- D-11: If transcript output files already exist for the same timestamp, warn and ask "Overwrite? [Y/n]" before writing.
- D-12: Extract a shared `_run_transcription()` helper used by both `record_command` and `transcribe_command` to avoid duplicating the post-transcription path (per roadmap decision).

**WAV Retention & Cleanup**
- D-13: Config key `cleanup.wav_retention_days` (default: 7) — WAV files older than this are eligible for deletion.
- D-14: Auto-cleanup runs at `mote record` startup, scanning the recordings directory for WAVs older than the retention period and deleting them silently.
- D-15: Also add a `mote cleanup` command for manual/on-demand cleanup of expired WAVs.

### Claude's Discretion

- Whether JSON is opt-in only or added to default config for new installs (leaning opt-in to avoid file clutter)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-07 | User can transcribe an existing WAV file via `mote transcribe <file>` with same engine/language flags as `mote record` | New `@cli.command("transcribe")` using `_run_transcription()` helper; Click argument + options pattern already established |
| CLI-08 | On transcription failure, user is prompted to retry with kept WAV; orphaned WAVs detected on next `mote record` and offered for transcription | `click.confirm()` retry loop after exception; existing orphan warning enhanced with `mote transcribe` pointer |
| REL-01 | Config is validated on startup — invalid engine names, missing models, malformed paths caught early; absent v2 keys in v1 configs get silent defaults | `validate_config()` in `config.py` using `.get()` with defaults; `is_model_downloaded()` already available in `models.py` |
| INT-02 | User can get JSON output format alongside Markdown and plain text | Extend `write_transcript()` with a "json" branch; `json.dumps()` stdlib; flat structure mirrors existing `_HEADER_TEMPLATE` fields |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | 8.3.0 | CLI commands and options | Already used throughout; `click.confirm()`, `ClickException`, `@cli.command()` all established |
| Python stdlib `json` | 3.11+ | JSON serialisation | No extra dep; `json.dumps(indent=2)` for human-readable output |
| Python stdlib `datetime` | 3.11+ | Timestamp for JSON `date` field | Already used in `output.py` |
| Python stdlib `pathlib` | 3.11+ | File age check for cleanup (`.stat().st_mtime`) | Already used everywhere |

### No New Dependencies
This phase adds zero new packages to `pyproject.toml`. All required tools are already installed:
- `click` — commands, prompts, exceptions
- `tomlkit` — config read/write with comment preservation
- `json` — stdlib, no import needed
- `mote.models.is_model_downloaded` — model presence check
- `mote.models.config_value_to_alias` — model alias conversion

**Installation:** No additional packages needed.

---

## Architecture Patterns

### Recommended Project Structure (changes only)

```
src/mote/
├── cli.py          # +transcribe_command, +cleanup_command, +config validate subcommand,
│                   #  _run_transcription() helper extracted from record_command
├── config.py       # +validate_config(), +[cleanup] section in _write_default_config()
├── output.py       # +JSON branch in write_transcript()
```

### Pattern 1: Shared `_run_transcription()` Helper

**What:** Extract lines 142-181 of `cli.py` (the post-recording transcription path) into a private helper that accepts `wav_path` and resolved config values. Both `record_command` and `transcribe_command` call this helper.

**When to use:** Whenever both record and transcribe need to run the same post-WAV pipeline.

**Important:** The existing test `test_record_name_flag` asserts `call_args[0][7] == "standup"` against the positional arguments to `write_transcript`. After extracting the helper, `write_transcript` must be called with the same positional order, or the test must be updated alongside the refactor. Coordinate both in the same task.

**Example:**
```python
def _run_transcription(
    wav_path: Path,
    engine: str,
    language: str,
    model_alias: str,
    api_key: str | None,
    output_dir: Path,
    formats: list[str],
    name: str | None,
) -> None:
    """Shared post-recording transcription pipeline."""
    duration = get_wav_duration(wav_path)
    transcript = transcribe_file(wav_path, engine, language, model_alias, api_key)
    written = write_transcript(
        transcript, output_dir, formats, duration, engine, language, model_alias, name
    )
    wav_path.unlink(missing_ok=True)
    word_count = len(transcript.split())
    mins, secs = divmod(int(duration), 60)
    names_str = ", ".join(p.name for p in written)
    click.echo(f"Transcription complete ({mins}:{secs:02d}, {word_count:,} words) \u2192 {names_str}")
```

### Pattern 2: Retry Loop After Transcription Failure (D-01)

**What:** Wrap the `_run_transcription()` call in a loop. On exception, keep WAV, show the error, and use `click.confirm()` to offer retry. If user declines, re-raise as `ClickException` with WAV path.

**Example:**
```python
while True:
    try:
        _run_transcription(wav_path, ...)
        break
    except click.ClickException:
        raise
    except Exception as e:
        click.echo(f"Transcription failed: {e}\nWAV kept at: {wav_path}")
        if not click.confirm("Retry transcription?", default=True):
            raise click.ClickException(f"Transcription failed. WAV kept at: {wav_path}")
```

**Note:** `click.ClickException` should be re-raised immediately without wrapping (it already displays cleanly). Only generic `Exception` triggers the retry prompt.

### Pattern 3: `mote transcribe <file>` Command (D-09, D-10)

**What:** New top-level Click command accepting a PATH argument (not a string — use `click.Path(exists=True, path_type=Path)`) and same flags as `record_command`.

**Overwrite detection (D-11):** Before calling `write_transcript`, predict the output filename using `_build_filename(ts, name, ext)` for each format. If any predicted path exists, prompt with `click.confirm("Overwrite?", default=False)`. Extract the timestamp from the WAV file's mtime so the output filename matches the recording time, not the transcription time.

**Example:**
```python
@cli.command("transcribe")
@click.argument("wav_file", type=click.Path(exists=True, path_type=Path))
@click.option("--engine", type=click.Choice(["local", "openai"]), default=None)
@click.option("--language", type=click.Choice(["sv", "no", "da", "fi", "en"]), default=None)
@click.option("--name", default=None)
@click.option("--output-format", "extra_formats", multiple=True,
              type=click.Choice(["json"]), help="Additional output formats.")
def transcribe_command(wav_file, engine, language, name, extra_formats):
    """Transcribe an existing WAV file."""
    ...
```

### Pattern 4: `validate_config()` in `config.py` (D-03, D-06)

**What:** A function that takes a loaded config dict and returns a list of error/warning strings. Caller decides whether to abort (startup) or print (manual validate command).

**Silent defaults pattern:** Use `.get()` with defaults throughout — never assume a v2 key exists in a v1 config:

```python
def validate_config(cfg: dict) -> tuple[list[str], list[str]]:
    """Validate config. Returns (errors, warnings).

    errors: present-but-invalid values that will prevent operation.
    warnings: advisory issues (missing API key, etc).
    """
    errors = []
    warnings = []

    # Engine check
    engine = cfg.get("transcription", {}).get("engine", "local")
    if engine not in ("local", "openai"):
        errors.append(f"Invalid engine '{engine}'. Must be 'local' or 'openai'.")

    # Model check (only if engine=local)
    if engine == "local":
        model_config = cfg.get("transcription", {}).get("model", "kb-whisper-medium")
        alias = config_value_to_alias(model_config)
        if alias is None:
            errors.append(f"Unknown model '{model_config}'.")
        elif not is_model_downloaded(alias):
            errors.append(
                f"Model '{alias}' is not downloaded. Run: mote models download {alias}"
            )

    # Output dir check
    output_dir = Path(cfg.get("output", {}).get("dir", "~/Documents/mote")).expanduser()
    if output_dir.exists() and not output_dir.is_dir():
        errors.append(f"Output dir '{output_dir}' exists but is not a directory.")
    elif not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errors.append(f"Cannot create output dir '{output_dir}': {e}")

    # API key warning (not an error)
    if engine == "openai":
        api_key = cfg.get("api_keys", {}).get("openai") or ""
        if not api_key:
            warnings.append("engine=openai but no api_keys.openai set.")

    return errors, warnings
```

**Startup use (D-04):** Call at top of `record_command` and `transcribe_command`, before BlackHole detection or any other work. If `errors`, raise `ClickException` immediately.

### Pattern 5: JSON Output Branch in `write_transcript()` (D-07, D-08)

**What:** Add a `if "json" in formats:` branch in `write_transcript()`. The JSON structure is a flat dict matching frontmatter keys, serialised with `json.dumps(indent=2)`.

**Example:**
```python
if "json" in formats:
    import json
    payload = {
        "date": ts.isoformat(),
        "duration": round(duration_seconds),
        "words": len(transcript.split()),
        "engine": engine,
        "language": language,
        "model": model_alias,
        "transcript": transcript,
    }
    json_path = output_dir / _build_filename(ts, name, "json")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append(json_path)
```

**Note:** `ensure_ascii=False` is required for Swedish characters (å, ä, ö) to be stored as UTF-8 rather than `\uXXXX` escape sequences.

### Pattern 6: WAV Retention Cleanup (D-13, D-14, D-15)

**What:** A function `cleanup_old_wavs(recordings_dir, retention_days)` that deletes WAV files older than `retention_days` days. Auto-called silently at `mote record` startup before the orphan check. Also exposed via `mote cleanup` command.

**Age check:**
```python
import time

def cleanup_old_wavs(recordings_dir: Path, retention_days: int) -> list[Path]:
    """Delete WAV files older than retention_days. Returns list of deleted paths."""
    if not recordings_dir.exists():
        return []
    cutoff = time.time() - (retention_days * 86400)
    deleted = []
    for wav in recordings_dir.glob("*.wav"):
        if wav.stat().st_mtime < cutoff:
            wav.unlink(missing_ok=True)
            deleted.append(wav)
    return deleted
```

**Default config addition** in `_write_default_config()`:
```python
cleanup_table = tomlkit.table()
cleanup_table.add(tomlkit.comment("Days to keep WAV files before auto-deletion (0 = keep forever)"))
cleanup_table.add("wav_retention_days", 7)
doc.add("cleanup", cleanup_table)
```

**Silent vs. verbose:** Auto-cleanup (from `record_command`) runs silently — no output unless `--verbose` is added (out of scope). The `mote cleanup` command prints how many files were deleted (or "No expired WAVs found.").

### Anti-Patterns to Avoid

- **Don't import `json` at module level in `output.py`:** Keep it as a local import inside the `if "json" in formats:` block, consistent with the lazy-import pattern used in `transcribe.py` (per Phase 4 decision). Actually `json` is stdlib so module-level is fine — unlike `faster_whisper`/`openai` which are optional. Either works; module-level is simpler for stdlib.
- **Don't make `validate_config()` call `load_config()`:** It should accept an already-loaded dict. This makes it testable without file I/O and avoids double-loading.
- **Don't use `click.Path(exists=True)` for the output dir:** Output dir may not exist yet and should be created. Use `Path.mkdir(parents=True, exist_ok=True)` inside `validate_config` to test writability.
- **Don't delete WAVs without confirming they are not the current recording:** `cleanup_old_wavs` checks only `recordings_dir/*.wav` — the in-flight recording goes there too, but it will have a recent mtime and won't fall below the cutoff.
- **Don't implement `mote config validate` as a standalone command:** Per D-05 it must be a subcommand of the `config` group (`@config.command("validate")`), consistent with `mote config show` and `mote config set`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interactive yes/no prompt | Custom `input()` loop | `click.confirm()` | Already used in `models_download`; handles TTY detection, default values, abort-on-no |
| File existence check before write | Custom stat + loop | `Path.exists()` + `click.confirm()` | Trivial with pathlib; no extra complexity |
| JSON serialisation | Manual string formatting | `json.dumps(indent=2, ensure_ascii=False)` | Handles all edge cases including Swedish chars, nested values |
| File age in seconds | `datetime.now() - datetime.fromtimestamp(mtime)` | `time.time() - path.stat().st_mtime` | Simpler, no timezone conversion needed for relative age |
| Click argument type validation | Manual `isinstance` check | `click.Path(exists=True, path_type=Path)` | Click validates and reports error before command body runs |

---

## Common Pitfalls

### Pitfall 1: Existing Test Breaks After `_run_transcription()` Extraction

**What goes wrong:** `test_record_name_flag` asserts `call_args[0][7] == "standup"` — the 8th positional argument to `write_transcript`. If `_run_transcription()` changes the call signature to keyword arguments, this positional assertion breaks.

**Why it happens:** The test was written asserting positional order to `write_transcript`. Any refactor that wraps the call changes what `mock_write.call_args[0]` contains.

**How to avoid:** Keep the `write_transcript` call signature identical in the extracted helper. Update the test to use `call_kwargs` by keyword name instead of positional index — more resilient going forward.

**Warning signs:** `AssertionError: assert None == 'standup'` in `test_record_name_flag`.

### Pitfall 2: Retry Loop Catches `click.ClickException`

**What goes wrong:** `click.ClickException` is a subclass of `Exception`. A bare `except Exception` catch in the retry loop will catch Click's own user-facing errors (e.g., missing API key) and re-prompt instead of exiting cleanly.

**Why it happens:** The exception hierarchy. `ClickException` inherits from `Exception`.

**How to avoid:** Always re-raise `click.ClickException` first in the except chain before the generic catch:
```python
except click.ClickException:
    raise
except Exception as e:
    # offer retry
```

### Pitfall 3: JSON Output `--output-format` Flag Name Collision

**What goes wrong:** The existing `mote record` has no `--output-format` flag. Adding it to both `record_command` and `transcribe_command` is correct. But if it's named identically to Click's built-in `--format` on some platforms, there may be shadowing.

**Why it happens:** Click uses `--format` internally in some contexts.

**How to avoid:** Name the option `--output-format` (not `--format`) and map it to a Python parameter with a non-reserved name: `@click.option("--output-format", "extra_formats", multiple=True, ...)`. `multiple=True` allows multiple `--output-format json` flags.

### Pitfall 4: `validate_config()` Breaks v1 Configs (D-06)

**What goes wrong:** A v1 config has no `[cleanup]` section. If `validate_config` accesses `cfg["cleanup"]["wav_retention_days"]` directly, it raises `KeyError` on every v1 user.

**Why it happens:** tomlkit returns a document that does not auto-create missing keys.

**How to avoid:** Always use `.get()` with defaults in `validate_config`:
```python
retention = cfg.get("cleanup", {}).get("wav_retention_days", 7)
```

### Pitfall 5: WAV Overwrite Detection Uses Wrong Timestamp

**What goes wrong:** `mote transcribe <file>` uses `datetime.now()` for the output filename, so running the command twice produces different filenames and never triggers the overwrite prompt (D-11).

**Why it happens:** `write_transcript` defaults `timestamp` to `datetime.now()`.

**How to avoid:** Extract the WAV file's mtime as the timestamp:
```python
ts = datetime.fromtimestamp(wav_file.stat().st_mtime)
```
Pass this explicitly to `write_transcript(timestamp=ts)` so both the overwrite check and the written file use the same deterministic timestamp.

### Pitfall 6: `mote config validate` Output Dir Check Creates Dir on Dry Run

**What goes wrong:** The manual `mote config validate` command should report whether the output dir is writable — but if the validation function creates the directory as part of checking writability, running `validate` has a side effect.

**Why it happens:** The writability check for non-existent dirs needs to try `mkdir` to confirm.

**How to avoid:** The auto-startup validation creating the dir is acceptable (it would be created anyway). The manual `mote config validate` can also create it — this is benign since recording would create it anyway. Alternatively, test with `os.access(parent_dir, os.W_OK)` on the parent. Simplest: allow the mkdir side effect; document it.

---

## Code Examples

Verified patterns from existing codebase:

### Click confirm (existing pattern in `models_download`)
```python
# Source: src/mote/cli.py lines 297-301
click.confirm(
    f"kb-whisper-{name} is approximately {approx}. Continue?",
    default=True,
    abort=True,
)
```

### Click Path argument (for `transcribe_command`)
```python
# Click 8.x docs — click.Path with path_type=Path returns a pathlib.Path directly
@click.argument("wav_file", type=click.Path(exists=True, path_type=Path))
```

### Orphan warning (existing, to enhance with D-02)
```python
# Source: src/mote/cli.py lines 110-117
orphans = find_orphan_recordings(recordings_dir)
if orphans:
    click.echo(f"Warning: Found {len(orphans)} orphaned recording(s) in {recordings_dir}:")
    for o in orphans:
        size_mb = o.stat().st_size / (1024 * 1024)
        click.echo(f"  {o.name} ({size_mb:.1f} MB)")
    click.echo("These may be from a previous crashed session.")
    # Phase 6 enhancement: add this line below
    click.echo("Transcribe them with: mote transcribe <file>")
    click.echo()
```

### Adding a `config` subcommand (existing pattern)
```python
# Source: src/mote/cli.py lines 44-48
@config.command("show")
def config_show():
    """Print current configuration."""
    ...

# New: same pattern for validate
@config.command("validate")
def config_validate():
    """Run pre-flight config checks."""
    ...
```

### `_build_filename` for overwrite detection
```python
# Source: src/mote/output.py lines 46-56
# Reuse to predict output filenames before writing:
from mote.output import _build_filename
ts = datetime.fromtimestamp(wav_file.stat().st_mtime)
predicted_md = output_dir / _build_filename(ts, sanitized_name, "md")
if predicted_md.exists():
    if not click.confirm(f"Overwrite {predicted_md.name}?", default=False):
        raise click.Abort()
```

---

## Environment Availability

Step 2.6: SKIPPED — Phase 6 is purely Python code and config changes. No new external tools, services, CLIs, runtimes, or databases are required beyond the existing project venv.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/pytest tests/test_cli.py tests/test_config.py tests/test_output.py -q` |
| Full suite command | `.venv/bin/pytest -q` |

### Baseline Health
Current suite: 151 passed, 1 pre-existing failure (`test_download_model_passes_tqdm_class` — unrelated to Phase 6, asserts internal tqdm class identity). This failure is not caused by Phase 6 and does not need to be fixed here.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-07 | `mote transcribe <file>` runs and produces transcript files | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_transcribe_command -x` | ❌ Wave 0 |
| CLI-07 | `--engine`, `--language`, `--name` flags work on transcribe | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_transcribe_flags -x` | ❌ Wave 0 |
| CLI-08 | Retry prompt shown after transcription failure; yes retranscribes | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_transcribe_retry -x` | ❌ Wave 0 |
| CLI-08 | Orphan warning includes `mote transcribe` pointer | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_record_orphan_warning` | ✅ (update needed) |
| REL-01 | Invalid engine name exits before recording | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_record_validates_engine -x` | ❌ Wave 0 |
| REL-01 | Missing model exits before recording | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_record_validates_model -x` | ❌ Wave 0 |
| REL-01 | v1 config (no `[cleanup]` section) does not error | unit | `.venv/bin/pytest tests/test_config.py::test_validate_config_v1_compat -x` | ❌ Wave 0 |
| REL-01 | `mote config validate` command prints results | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_config_validate_command -x` | ❌ Wave 0 |
| INT-02 | `write_transcript` with "json" format writes valid JSON file | unit | `.venv/bin/pytest tests/test_output.py::test_write_json -x` | ❌ Wave 0 |
| INT-02 | JSON contains all 7 fields with correct types | unit | `.venv/bin/pytest tests/test_output.py::test_write_json_fields -x` | ❌ Wave 0 |
| INT-02 | Swedish chars in transcript stored as UTF-8 not escaped | unit | `.venv/bin/pytest tests/test_output.py::test_write_json_swedish_chars -x` | ❌ Wave 0 |
| D-13/14/15 | `cleanup_old_wavs` deletes files older than retention | unit | `.venv/bin/pytest tests/test_cli.py::test_cleanup_old_wavs -x` | ❌ Wave 0 |
| D-15 | `mote cleanup` command runs and reports deleted count | unit/CLI | `.venv/bin/pytest tests/test_cli.py::test_cleanup_command -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_cli.py tests/test_config.py tests/test_output.py -q`
- **Per wave merge:** `.venv/bin/pytest -q`
- **Phase gate:** Full suite green (excluding the pre-existing `test_download_model_passes_tqdm_class` failure) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli.py` — add test functions for: `test_transcribe_command`, `test_transcribe_flags`, `test_transcribe_retry`, `test_record_validates_engine`, `test_record_validates_model`, `test_config_validate_command`, `test_cleanup_old_wavs`, `test_cleanup_command`
- [ ] `tests/test_config.py` — add: `test_validate_config_v1_compat`, `test_validate_config_invalid_engine`, `test_validate_config_missing_model`, `test_validate_config_openai_no_key_warning`
- [ ] `tests/test_output.py` — add: `test_write_json`, `test_write_json_fields`, `test_write_json_swedish_chars`
- [ ] Update `tests/test_cli.py::test_record_orphan_warning` to assert `"mote transcribe"` appears in output

*(Existing test infrastructure covers all other phase requirements without new files.)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `transcription` path only in `record_command` | Extracted `_run_transcription()` shared helper | Phase 6 | Both `record` and `transcribe` use identical post-WAV pipeline |
| Orphan warning only | Warning + `mote transcribe` pointer | Phase 6 | Users know how to recover without hunting for the command |
| Output formats: markdown, txt only | + json | Phase 6 | NotebookLM and other tools can consume structured JSON |

---

## Open Questions

1. **JSON opt-in vs. added to default config**
   - What we know: D-08 enables it via flag or config; Claude's discretion whether it's in new install defaults
   - What's unclear: If "json" is NOT in default config, users must actively opt in via flag or `mote config set output.format`
   - Recommendation: Keep JSON opt-in (not in default config). The user mentioned "avoid file clutter." Add a comment to default config: `# Add "json" to include JSON output`. This matches the established pattern of the config file serving as self-documenting documentation.

2. **`_run_transcription()` function location**
   - What we know: It's a private helper used only by `cli.py`
   - What's unclear: Should it be in `cli.py` (private to the module) or extracted to a new `pipeline.py`?
   - Recommendation: Keep in `cli.py` as a module-level private function (`_run_transcription`). It depends on Click (for `click.echo`) which is a CLI concern, not a library concern. No need for a new module.

---

## Project Constraints (from CLAUDE.md)

The following directives from `CLAUDE.md` apply to this phase and must be honoured by the planner:

- **Python 3.11+** — use `tomllib` stdlib only if read-only; use `tomlkit` for config writes (already the pattern)
- **tomlkit** — config read AND write; never use `tomllib` for write operations
- **Click 8.3.0** — `ClickException`, `click.confirm()`, `@cli.command()` decorators
- **No YAML for config** — TOML via tomlkit only
- **No `threading`** — sequential record-then-transcribe; no concurrent paths
- **Function-based modules, no classes** — `validate_config()` as a function in `config.py`, not a class
- **`MOTE_HOME` env var** — all test isolation uses this; never touch real `~/.mote` in tests
- **Security**: config file permissions 600 — `_write_default_config` already does this; `validate_config` must not change permissions
- **Web UI binds to 127.0.0.1 only** — not relevant to Phase 6
- **Distribution via pip install from GitHub** — no new dependencies introduced in Phase 6 (confirmed)
- **GSD Workflow Enforcement** — code changes via `/gsd:execute-phase`, not direct edits

---

## Sources

### Primary (HIGH confidence)
- `src/mote/cli.py` — existing `record_command`, orphan warning, `click.confirm` usage
- `src/mote/config.py` — `load_config()`, `_write_default_config()`, `set_config_value()` patterns
- `src/mote/output.py` — `write_transcript()`, `_build_filename()`, `_HEADER_TEMPLATE` fields
- `src/mote/models.py` — `is_model_downloaded()`, `config_value_to_alias()`
- `tests/test_cli.py` — existing test coverage, positional assertion in `test_record_name_flag`
- `tests/test_output.py` — write_transcript test coverage
- `.planning/phases/06-cli-polish-and-config-reliability/06-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- Click 8.x docs — `click.Path(exists=True, path_type=Path)`, `multiple=True` options, `click.confirm()` behaviour

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use; zero new dependencies
- Architecture: HIGH — all patterns directly derived from existing codebase code
- Pitfalls: HIGH — identified from reading existing tests (positional arg assertion) and exception hierarchy analysis
- Test map: HIGH — based on direct reading of existing test suite

**Research date:** 2026-03-29
**Valid until:** 2026-06-29 (stable stack; no external service dependencies)
