# Phase 5: Output and Transcript Management - Research

**Researched:** 2026-03-28
**Domain:** File I/O, filename conventions, CLI table display (Python stdlib + Rich)
**Confidence:** HIGH

## Summary

This phase is low-risk, stdlib-heavy work. The core tasks are: (1) a new `output.py` module that writes `.md` and `.txt` files, (2) wiring `write_transcript()` into the existing `record_command()` flow, and (3) a `mote list` CLI command that reads metadata back from the Markdown headers and renders a Rich table.

All decisions were locked in the CONTEXT.md discussion. No external dependencies are needed beyond what is already installed. Python's `pathlib`, `re`, and `datetime` modules handle everything for filename generation, directory creation, and metadata parsing. Rich `Table` is already imported in `cli.py`.

The only subtlety is the integration point in `record_command()`: `write_transcript()` must be called **after** `get_wav_duration()` / `transcribe_file()` but **before** `wav_path.unlink()`. This ordering is already documented in the CONTEXT.md and matches the existing code structure at lines 150–157 of `cli.py`.

**Primary recommendation:** Implement `output.py` as a standalone module with two functions (`write_transcript`, `list_transcripts`), wire into `cli.py` with minimal changes, and cover all paths with tests using `MOTE_HOME` for isolation.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Output Format**
- D-01: Markdown file includes a YAML-style header block with date, duration, word count, engine, language, and model — then full transcript text below a separator
- D-02: Plain text file contains transcript text only — no metadata header
- D-03: No per-segment timestamps in output — full continuous text
- D-04: Both formats written simultaneously when config `output.format` includes both (default: `["markdown", "txt"]`)

**Filename Convention**
- D-05: Filename format: `YYYY-MM-DD_HHMM_{name}.{ext}`. Examples: `2026-03-28_1430_standup.md`, `2026-03-28_1430.md`
- D-06: Add `--name` flag to `mote record` for the optional filename component. If omitted, no name segment — just date and time
- D-07: Sanitize user-provided name: lowercase, replace spaces with hyphens, strip non-alphanumeric except hyphens

**Output Directory**
- D-08: Output directory from config `output.dir` (default: `~/Documents/mote`). Create directory if it doesn't exist
- D-09: Both .md and .txt files go to the same output directory

**Transcript Listing**
- D-10: `mote list` shows a Rich table with columns: Filename, Date, Duration, Words, Engine
- D-11: Default shows last 20 transcripts sorted newest-first. `--all` flag shows everything
- D-12: Parse metadata from Markdown files' header block. Skip entries where Markdown file is missing or malformed

**Write Integration**
- D-13: New `output.py` module with `write_transcript()` function
- D-14: `record_command` calls `write_transcript()` after successful transcription, before WAV deletion
- D-15: `write_transcript()` returns list of written file paths for the summary line
- D-16: Summary line updated to show output paths: `Transcription complete (5:22, 1,247 words) → standup.md, standup.txt`

### Claude's Discretion

- Internal structure of output.py (function signatures, helpers)
- Exact Markdown header format (YAML frontmatter vs plain text header)
- Rich table styling for `mote list`
- Error handling for write failures (disk full, permissions)
- Whether to add `--output-dir` CLI override flag (nice-to-have, not required)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUT-01 | Transcripts are saved as Markdown files with timestamps | `write_transcript()` writes `.md` file with YAML-style header (D-01, D-03); `datetime.now()` provides the timestamp |
| OUT-02 | Transcripts are saved as plain text files | `write_transcript()` also writes `.txt` file with transcript text only (D-02, D-04) |
| OUT-03 | Output files use timestamped filenames with optional user-provided name | Filename built as `YYYY-MM-DD_HHMM[_{name}].{ext}` (D-05, D-06, D-07); `--name` flag added to `record_command` |
| OUT-04 | Temporary WAV files are cleaned up after successful transcription | WAV already deleted in `cli.py` line 154 on success; phase must ensure `write_transcript()` completes before unlink and WAV is kept on write failure |
| CLI-05 | `mote list` shows recent transcripts | New `@cli.command("list")` using Rich Table, reads `.md` headers from output dir (D-10, D-11, D-12) |
</phase_requirements>

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib (stdlib) | 3.11+ | Directory creation, path construction, file glob | Zero-dep, handles `~` expansion via `.expanduser()` |
| datetime (stdlib) | 3.11+ | Timestamp generation for filenames and headers | `datetime.now().strftime()` for `YYYY-MM-DD_HHMM` format |
| re (stdlib) | 3.11+ | Name sanitization (strip non-alphanumeric, collapse hyphens) | One-liner substitution |
| rich.table.Table | 13.x (installed) | `mote list` output — already imported in cli.py | Consistent with existing models list command |
| rich.console.Console | 13.x (installed) | Print Rich table — already imported in cli.py | Same pattern as `models_list()` |

**Installation:** No new packages required. All libraries are stdlib or already in pyproject.toml.

### No New Dependencies

This phase requires zero new pip packages. The only new file is `src/mote/output.py`.

## Architecture Patterns

### Recommended Project Structure

```
src/mote/
├── output.py        # NEW — write_transcript(), list_transcripts(), helpers
├── cli.py           # MODIFIED — add --name to record_command, add list command, wire write_transcript()
├── config.py        # NO CHANGE — output.dir and output.format already in default config
└── transcribe.py    # NO CHANGE — transcribe_file() and get_wav_duration() already done
```

### Pattern 1: write_transcript() Signature

**What:** Accepts all data needed to write both files; returns list of Path objects written.

**When to use:** Called from `record_command()` after `transcribe_file()` returns, before `wav_path.unlink()`.

```python
# src/mote/output.py
from datetime import datetime
from pathlib import Path
import re

def write_transcript(
    transcript: str,
    output_dir: Path,
    formats: list[str],          # ["markdown", "txt"] from config
    duration_seconds: float,
    engine: str,
    language: str,
    model_alias: str,
    name: str | None = None,     # from --name flag, already sanitized
    timestamp: datetime | None = None,  # injectable for tests
) -> list[Path]:
    """Write transcript to .md and/or .txt files. Returns list of written paths."""
    ...
```

### Pattern 2: Filename Generation

**What:** Build `YYYY-MM-DD_HHMM[_{name}].{ext}` from a datetime and optional name.

**When to use:** Called inside `write_transcript()`.

```python
def _build_filename(ts: datetime, name: str | None, ext: str) -> str:
    base = ts.strftime("%Y-%m-%d_%H%M")
    if name:
        base = f"{base}_{name}"
    return f"{base}.{ext}"
```

### Pattern 3: Name Sanitization

**What:** Lowercase, spaces to hyphens, strip everything non-alphanumeric except hyphens, collapse repeated hyphens.

**When to use:** Applied to `--name` value before passing to `write_transcript()`. Applied in CLI, not in output.py, so output.py always receives a clean name.

```python
def _sanitize_name(raw: str) -> str:
    s = raw.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s
```

### Pattern 4: Markdown Header Format

**What:** YAML-style front matter block followed by separator and transcript text.

**When to use:** Written to the `.md` file only.

```
---
date: 2026-03-28T14:30:00
duration: 322
words: 1247
engine: local
language: sv
model: medium
---

[transcript text here]
```

Notes:
- `duration` is stored as integer seconds (from `get_wav_duration()` which returns float — use `round()`).
- ISO 8601 timestamp (`isoformat()`) enables unambiguous parsing when reading back.
- Plain YAML block is easy to parse with a simple regex — no PyYAML dependency needed.

### Pattern 5: Metadata Parsing for mote list

**What:** Read `.md` files from output dir, parse the front matter block, return structured rows.

**When to use:** Called by `list_command()` in cli.py.

```python
import re

_HEADER_RE = re.compile(
    r"^---\n"
    r"date: (?P<date>[^\n]+)\n"
    r"duration: (?P<duration>\d+)\n"
    r"words: (?P<words>\d+)\n"
    r"engine: (?P<engine>[^\n]+)\n"
    r"language: (?P<language>[^\n]+)\n"
    r"model: (?P<model>[^\n]+)\n"
    r"---",
    re.MULTILINE,
)

def list_transcripts(output_dir: Path) -> list[dict]:
    """Return parsed metadata from all .md files, newest-first."""
    ...
```

Return each record as a dict: `{"filename": str, "date": str, "duration": int, "words": int, "engine": str}`.

Skip any `.md` file where the regex does not match (malformed or unrelated file).

### Pattern 6: list_command in cli.py

**What:** `@cli.command("list")` with `--all` flag, renders Rich table.

```python
@cli.command("list")
@click.option("--all", "show_all", is_flag=True, default=False,
              help="Show all transcripts, not just the last 20.")
def list_command(show_all):
    """Show recent transcripts."""
    cfg = load_config()
    output_dir = Path(cfg.get("output", {}).get("dir", "~/Documents/mote")).expanduser()

    from mote.output import list_transcripts
    records = list_transcripts(output_dir)
    if not show_all:
        records = records[:20]

    if not records:
        click.echo("No transcripts found.")
        return

    console = Console()
    table = Table(title="Recent Transcripts", show_header=True, header_style="bold")
    table.add_column("Filename", style="cyan")
    table.add_column("Date", no_wrap=True)
    table.add_column("Duration", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Engine")
    for r in records:
        mins, secs = divmod(r["duration"], 60)
        table.add_row(
            r["filename"],
            r["date"],
            f"{mins}:{secs:02d}",
            f"{r['words']:,}",
            r["engine"],
        )
    console.print(table)
```

### Pattern 7: record_command Integration Point

**What:** Wire `write_transcript()` into the existing `record_command()` at lines 150–157.

**Critical ordering:** `write_transcript()` MUST be called before `wav_path.unlink()`. If writing fails, raise `ClickException` and keep WAV.

```python
# Current (end of record_command auto-transcription block):
duration = get_wav_duration(wav_path)
transcript = transcribe_file(wav_path, engine, language, model_alias, api_key)
wav_path.unlink(missing_ok=True)  # <-- WAV delete (current line 154)
word_count = len(transcript.split())
...

# Phase 5 updated flow:
duration = get_wav_duration(wav_path)
transcript = transcribe_file(wav_path, engine, language, model_alias, api_key)

# Write output files BEFORE deleting WAV (so WAV is kept on write failure)
from mote.output import write_transcript as _write_transcript
output_cfg = cfg.get("output", {})
output_dir = Path(output_cfg.get("dir", "~/Documents/mote")).expanduser()
formats = output_cfg.get("format", ["markdown", "txt"])
sanitized_name = _sanitize_name(name) if name else None
written = _write_transcript(
    transcript, output_dir, formats, duration, resolved_engine,
    resolved_language, model_alias, sanitized_name,
)
wav_path.unlink(missing_ok=True)
# Build summary
names_str = ", ".join(p.name for p in written)
click.echo(f"Transcription complete ({mins}:{secs:02d}, {word_count:,} words) → {names_str}")
```

### Anti-Patterns to Avoid

- **Deleting WAV before writing output files:** If `write_transcript()` raises (disk full, permissions), WAV would already be gone. Always write files first.
- **Not calling `.expanduser()` on output dir:** Config default is `~/Documents/mote` — Path will not expand `~` automatically.
- **Calling `write_transcript()` inside the existing `try/except` that guards transcription:** Write failures need their own error path. Keep write logic after the transcription try/except resolves successfully.
- **Importing `output` at module top-level:** Follow the project's lazy-import pattern for new modules — import inside function body or at module level only if there are no circular concerns. For `output.py` there are no circular imports, so top-level import in cli.py is fine.
- **Using class-based design:** All existing modules are function-based. `output.py` should be too.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory creation | Custom mkdir logic | `Path.mkdir(parents=True, exist_ok=True)` | One line, handles nested dirs, idempotent |
| Filename timestamp | Manual string formatting | `datetime.now().strftime("%Y-%m-%d_%H%M")` | stdlib, no edge cases |
| YAML front matter parsing | Full YAML parser (pyyaml) | Single `re.compile()` regex | No new dep; front matter is fully controlled format |
| File glob + sort | `os.walk()` | `sorted(output_dir.glob("*.md"), reverse=True)` | Pathlib glob with sort on `stat().st_mtime` gives newest-first |
| Rich table | Custom formatting | `rich.table.Table` already in project | Consistent with `models list` command |

**Key insight:** This phase is pure I/O orchestration. Every component already exists in stdlib or installed libs.

## Common Pitfalls

### Pitfall 1: WAV deleted before output written

**What goes wrong:** If `write_transcript()` is called after `wav_path.unlink()` and writing fails, the audio is gone permanently.

**Why it happens:** Natural ordering instinct is "finish transcription → delete temp → save output."

**How to avoid:** Always write output files first. The integration point in `record_command()` must be: `transcribe_file()` → `write_transcript()` → `wav_path.unlink()`.

**Warning signs:** Code review — look for `unlink` appearing before `write_transcript` call.

### Pitfall 2: output.dir not expanded

**What goes wrong:** `Path("~/Documents/mote")` does not expand to the home directory — `~` is literal. File writes go to a `~/Documents/mote` folder relative to cwd, which won't exist.

**Why it happens:** Forgetting `.expanduser()` on paths read from config.

**How to avoid:** Always call `.expanduser()` when constructing the output dir path from config. The CONTEXT.md explicitly calls this out.

**Warning signs:** `FileNotFoundError` with a path starting with `~`.

### Pitfall 3: Malformed header breaks mote list

**What goes wrong:** If the regex pattern doesn't exactly match the header written by `write_transcript()`, every file is silently skipped and `mote list` shows no results.

**Why it happens:** Slight divergence between the write format and the read regex (e.g., extra whitespace, field order change).

**How to avoid:** Use the same constant header template for write and the same regex for read. Test round-trip: write a file, parse it back, assert field values match.

**Warning signs:** `mote list` shows "No transcripts found." when `.md` files exist in the output dir.

### Pitfall 4: name sanitization applied in wrong place

**What goes wrong:** If sanitization happens inside `write_transcript()`, the function's callers in tests may not see the sanitized name in the returned path, or the sanitized name diverges from what the user expects.

**How to avoid:** Sanitize in CLI layer (`record_command`) before passing to `write_transcript()`. `write_transcript()` receives an already-clean name (or None).

### Pitfall 5: --name flag naming collision with Python built-in `list`

**What goes wrong:** Click command named `list` conflicts with Python's built-in `list` type if the function is also named `list`.

**How to avoid:** Name the function `list_command` (consistent with `status_command`, `record_command` pattern). Register it as `@cli.command("list")`.

## Code Examples

### Write transcript (full example)

```python
# src/mote/output.py
from datetime import datetime
from pathlib import Path
import re

_HEADER_TEMPLATE = """\
---
date: {date}
duration: {duration}
words: {words}
engine: {engine}
language: {language}
model: {model}
---

{transcript}
"""

def write_transcript(
    transcript: str,
    output_dir: Path,
    formats: list[str],
    duration_seconds: float,
    engine: str,
    language: str,
    model_alias: str,
    name: str | None = None,
    timestamp: datetime | None = None,
) -> list[Path]:
    ts = timestamp or datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = ts.strftime("%Y-%m-%d_%H%M")
    if name:
        base = f"{base}_{name}"
    word_count = len(transcript.split())
    written = []
    if "markdown" in formats:
        md_path = output_dir / f"{base}.md"
        md_content = _HEADER_TEMPLATE.format(
            date=ts.isoformat(),
            duration=round(duration_seconds),
            words=word_count,
            engine=engine,
            language=language,
            model=model_alias,
            transcript=transcript,
        )
        md_path.write_text(md_content, encoding="utf-8")
        written.append(md_path)
    if "txt" in formats:
        txt_path = output_dir / f"{base}.txt"
        txt_path.write_text(transcript, encoding="utf-8")
        written.append(txt_path)
    return written
```

### Parse headers for mote list

```python
_HEADER_RE = re.compile(
    r"^---\n"
    r"date: (?P<date>[^\n]+)\n"
    r"duration: (?P<duration>\d+)\n"
    r"words: (?P<words>\d+)\n"
    r"engine: (?P<engine>[^\n]+)\n"
    r"language: (?P<language>[^\n]+)\n"
    r"model: (?P<model>[^\n]+)\n"
    r"---",
)

def list_transcripts(output_dir: Path) -> list[dict]:
    if not output_dir.exists():
        return []
    files = sorted(output_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    records = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
            m = _HEADER_RE.match(text)
            if not m:
                continue
            records.append({
                "filename": f.name,
                "date": m.group("date"),
                "duration": int(m.group("duration")),
                "words": int(m.group("words")),
                "engine": m.group("engine"),
            })
        except OSError:
            continue
    return records
```

### Name sanitization helper

```python
def _sanitize_name(raw: str) -> str:
    s = raw.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")
```

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code/config changes with no external dependencies.

All required libraries (pathlib, datetime, re, rich) are stdlib or already installed via pyproject.toml.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run --no-sync pytest tests/test_output.py tests/test_cli.py -q` |
| Full suite command | `uv run --no-sync pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| OUT-01 | `.md` file written with YAML-style header and transcript | unit | `pytest tests/test_output.py::test_write_markdown -x` | Wave 0 |
| OUT-01 | Markdown header contains date, duration, words, engine, language, model | unit | `pytest tests/test_output.py::test_markdown_header_fields -x` | Wave 0 |
| OUT-02 | `.txt` file written with transcript text only (no header) | unit | `pytest tests/test_output.py::test_write_txt -x` | Wave 0 |
| OUT-03 | Filename with timestamp only when no `--name` | unit | `pytest tests/test_output.py::test_filename_no_name -x` | Wave 0 |
| OUT-03 | Filename includes sanitized name when `--name` provided | unit | `pytest tests/test_output.py::test_filename_with_name -x` | Wave 0 |
| OUT-03 | Name sanitization: lowercase, spaces to hyphens, strip specials | unit | `pytest tests/test_output.py::test_sanitize_name -x` | Wave 0 |
| OUT-04 | WAV deleted after successful transcription and write | integration | `pytest tests/test_cli.py::test_record_deletes_wav_after_write -x` | Wave 0 |
| OUT-04 | WAV kept on disk when write_transcript raises | integration | `pytest tests/test_cli.py::test_record_keeps_wav_on_write_failure -x` | Wave 0 |
| CLI-05 | `mote list` shows Rich table with correct columns | integration | `pytest tests/test_cli.py::test_list_command -x` | Wave 0 |
| CLI-05 | `mote list` limits to 20 by default, `--all` shows more | unit | `pytest tests/test_output.py::test_list_transcripts_limit` | Wave 0 |
| CLI-05 | `mote list` skips malformed .md files silently | unit | `pytest tests/test_output.py::test_list_skips_malformed -x` | Wave 0 |
| CLI-05 | `mote list` shows "No transcripts found." when dir is empty | integration | `pytest tests/test_cli.py::test_list_empty -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run --no-sync pytest tests/test_output.py tests/test_cli.py -q`
- **Per wave merge:** `uv run --no-sync pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_output.py` — covers OUT-01, OUT-02, OUT-03, OUT-04 (unit), CLI-05 (unit)
  - `tests/test_cli.py` already exists; new tests for OUT-04 (WAV lifecycle with write) and CLI-05 (list command) added as Wave 0 additions

*(All other infrastructure — conftest.py, MOTE_HOME fixture, pytest config — already exists and covers this phase without modification.)*

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 5 |
|-----------|-------------------|
| Function-based modules (no classes) | `output.py` uses functions only |
| `MOTE_HOME` env var for test isolation | All tests set `MOTE_HOME` via `mote_home` fixture; output dir derived from there |
| `ClickException` for user-facing errors | Write failures raised as `ClickException` |
| Rich for CLI output formatting | `mote list` uses `rich.table.Table` |
| No new dependencies unless necessary | Zero new packages; stdlib + installed Rich only |
| Security: config file permissions 600 | No config changes needed; `output.py` writes transcript files with default umask (no special permissions needed for transcript files) |
| Hatchling editable install requires reinstall after adding new source modules | After creating `src/mote/output.py`, run `uv pip install -e .` before testing |

## Open Questions

1. **What happens if `write_transcript()` fails mid-write (e.g., disk full after .md but before .txt)?**
   - What we know: Python's `Path.write_text()` is atomic at the OS level only for small files on some filesystems.
   - What's unclear: Should partial output be cleaned up?
   - Recommendation: Accept partial output. Do not attempt cleanup on partial write. Document in error message. The transcript text is not lost (it's in memory and in the error output). LOW priority edge case.

2. **Should `list_command` scan recursively or only the top-level output dir?**
   - What we know: CONTEXT.md doesn't address subdirectories.
   - What's unclear: Future Google Drive phase may organize files by date subdirectory.
   - Recommendation: Top-level only (`output_dir.glob("*.md")`). Easy to change later.

## Sources

### Primary (HIGH confidence)

- `src/mote/cli.py` — Integration point at lines 149–163; existing Rich Table pattern at models_list()
- `src/mote/config.py` — `output.format` and `output.dir` already in default config (lines 81–85)
- `src/mote/transcribe.py` — `get_wav_duration()` returns `float`, `transcribe_file()` returns `str`
- `.planning/phases/05-output-and-transcript-management/05-CONTEXT.md` — All decisions locked
- Python 3.11 stdlib: `pathlib`, `datetime`, `re` — well-known, no verification needed
- `tests/conftest.py` — `mote_home` fixture confirmed; `MOTE_HOME` env var pattern established

### Secondary (MEDIUM confidence)

- Rich table API — confirmed via existing models_list() implementation in cli.py (lines 198–222)

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — zero new dependencies; all tools already in use
- Architecture: HIGH — directly derived from locked CONTEXT.md decisions and existing code patterns
- Integration point: HIGH — exact lines in cli.py identified (150–157), ordering requirement clear
- Pitfalls: HIGH — derived from CONTEXT.md warnings and existing code review

**Research date:** 2026-03-28
**Valid until:** Stable (pure Python stdlib + locked decisions; no external APIs)
