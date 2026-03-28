# Phase 5: Output and Transcript Management - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Formatted output files (Markdown and plain text) from transcription results, timestamped filenames with optional user-provided names, and a `mote list` command to browse past transcripts. This phase wires file-writing into the existing record→transcribe flow and adds the final CLI command. Google Drive integration is v2 scope — this phase writes local files only.

</domain>

<decisions>
## Implementation Decisions

### Output Format
- **D-01:** Markdown file includes a YAML-style header block with date, duration, word count, engine, language, and model — then full transcript text below a separator
- **D-02:** Plain text file contains transcript text only — no metadata header. Machine-parseable, copy-paste friendly
- **D-03:** No per-segment timestamps in output — full continuous text. Segment-level timestamps add complexity without clear value for the NotebookLM consumption workflow
- **D-04:** Both formats written simultaneously when config `output.format` includes both (default: `["markdown", "txt"]`)

### Filename Convention
- **D-05:** Filename format: `YYYY-MM-DD_HHMM_{name}.{ext}` where name is optional. Examples: `2026-03-28_1430_standup.md`, `2026-03-28_1430.md`
- **D-06:** Add `--name` flag to `mote record` for the optional filename component. If omitted, no name segment — just date and time
- **D-07:** Sanitize user-provided name: lowercase, replace spaces with hyphens, strip non-alphanumeric except hyphens

### Output Directory
- **D-08:** Output directory from config `output.dir` (default: `~/Documents/mote`). Create directory if it doesn't exist
- **D-09:** Both .md and .txt files go to the same output directory

### Transcript Listing
- **D-10:** `mote list` shows a Rich table with columns: Filename, Date, Duration, Words, Engine
- **D-11:** Default shows last 20 transcripts sorted newest-first. `--all` flag shows everything
- **D-12:** Parse metadata from Markdown files' header block. Skip entries where Markdown file is missing or malformed

### Write Integration
- **D-13:** New `output.py` module with `write_transcript()` function — keeps file-writing logic out of cli.py
- **D-14:** `record_command` calls `write_transcript()` after successful transcription, before WAV deletion
- **D-15:** `write_transcript()` returns list of written file paths for the summary line
- **D-16:** Summary line updated to show output paths: `Transcription complete (5:22, 1,247 words) → standup.md, standup.txt`

### Claude's Discretion
- Internal structure of output.py (function signatures, helpers)
- Exact Markdown header format (YAML frontmatter vs plain text header)
- Rich table styling for `mote list`
- Error handling for write failures (disk full, permissions)
- Whether to add `--output-dir` CLI override flag (nice-to-have, not required)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Technology stack, conventions, constraints
- `.planning/PROJECT.md` — Core value, output config defaults (`output.format`, `output.dir`)
- `.planning/REQUIREMENTS.md` — OUT-01 through OUT-04, CLI-05

### Prior Phase Context
- `.planning/phases/04-transcription-engine/04-CONTEXT.md` — Transcription flow decisions, progress display, WAV cleanup
- `.planning/phases/04-transcription-engine/04-01-SUMMARY.md` — transcribe.py API: transcribe_file(), get_wav_duration()
- `.planning/phases/04-transcription-engine/04-02-SUMMARY.md` — CLI integration: record_command with --engine, --language, --no-transcribe

### Existing Code
- `src/mote/cli.py` — `record_command()` integration point (transcript text available at line 152, WAV deleted at line 154)
- `src/mote/transcribe.py` — `transcribe_file()` returns transcript string, `get_wav_duration()` returns float seconds
- `src/mote/config.py` — `load_config()` returns dict with `output.format` and `output.dir` keys

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py:load_config()` — Already has `output.format` and `output.dir` in default config
- `transcribe.py:get_wav_duration()` — Duration available for metadata header
- `cli.py:_human_size()` — Byte formatting, reusable pattern for file size display
- Rich Console and Table already imported in cli.py — reuse for `mote list`

### Established Patterns
- Function-based modules (no classes) — output.py should follow same pattern
- Click decorator CLI with `@cli.command()` for new `list` command
- `ClickException` for user-facing errors
- `MOTE_HOME` env var for test isolation of output directory

### Integration Points
- `cli.py:record_command()` line 152-157 — after `transcript = transcribe_file(...)`, before `wav_path.unlink()`, call `write_transcript()`
- New `@cli.command("list")` — top-level command (not under a group)
- `output.dir` config value — needs `Path.expanduser()` since default contains `~`

</code_context>

<specifics>
## Specific Ideas

- Markdown output example from ROADMAP: `2026-03-27_standup.md`
- Summary line after transcription should show written filenames
- Output consumed by Google Drive sync (future) and NotebookLM — keep Markdown clean and standard

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-output-and-transcript-management*
*Context gathered: 2026-03-28*
