# Phase 6: CLI Polish and Config Reliability - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can transcribe existing WAV files via `mote transcribe <file>`, recover from transcription failures with an interactive retry prompt, trust that startup validation catches misconfiguration before wasting a meeting, and get JSON output format alongside Markdown and plain text. This phase also adds WAV retention-based cleanup and a `mote config validate` command.

</domain>

<decisions>
## Implementation Decisions

### Retry & Recovery
- **D-01:** When transcription fails, prompt the user interactively: "Retry transcription? [Y/n]" — yes retranscribes the kept WAV immediately. No separate retry command.
- **D-02:** Orphaned WAV files on `mote record` startup: keep the existing warning but enhance it to point to the `mote transcribe <file>` command. No interactive offer to transcribe orphans at record startup.

### Config Validation
- **D-03:** Validate four things: engine name (must be 'local' or 'openai'), model availability (if engine=local, check model is downloaded), output dir writability (exists or can be created), API key presence (if engine=openai, warn if no key configured).
- **D-04:** Automatic validation runs before `mote record` and `mote transcribe` only — not on `mote list`, `mote config show`, etc.
- **D-05:** Also add a manual `mote config validate` command for explicit checking.
- **D-06:** Absent v2 config keys get silent defaults (per roadmap decision). Only present-but-invalid values produce errors.

### JSON Output
- **D-07:** JSON structure is flat, mirroring YAML frontmatter fields: `date`, `duration`, `words`, `engine`, `language`, `model`, `transcript`. No segments array.
- **D-08:** JSON enabled via `--output-format json` flag or by adding "json" to config `output.format` list.

### Claude's Discretion
- Whether JSON is opt-in only or added to default config for new installs (leaning opt-in to avoid file clutter)

### Transcribe Command
- **D-09:** `mote transcribe <file>` accepts a single WAV file only. No multi-file or glob support.
- **D-10:** Same `--engine`, `--language`, `--name`, `--output-format` flags as `mote record`.
- **D-11:** If transcript output files already exist for the same timestamp, warn and ask "Overwrite? [Y/n]" before writing.
- **D-12:** Extract a shared `_run_transcription()` helper used by both `record_command` and `transcribe_command` to avoid duplicating the post-transcription path (per roadmap decision).

### WAV Retention & Cleanup
- **D-13:** Config key `cleanup.wav_retention_days` (default: 7) — WAV files older than this are eligible for deletion.
- **D-14:** Auto-cleanup runs at `mote record` startup, scanning the recordings directory for WAVs older than the retention period and deleting them silently.
- **D-15:** Also add a `mote cleanup` command for manual/on-demand cleanup of expired WAVs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Technology stack, conventions, constraints
- `.planning/PROJECT.md` — Core value, config defaults, key decisions
- `.planning/REQUIREMENTS.md` — REL-01, INT-02, CLI-07, CLI-08

### Prior Phase Context
- `.planning/phases/04-transcription-engine/04-CONTEXT.md` — Transcription flow decisions, lazy imports pattern
- `.planning/phases/05-output-and-transcript-management/05-CONTEXT.md` — Output format decisions, write_transcript() API, filename conventions

### Existing Code
- `src/mote/cli.py` — `record_command()` (integration point for validation, retry, orphan warning enhancement, shared helper extraction)
- `src/mote/config.py` — `load_config()` (validation target), `_write_default_config()` (new config keys to add)
- `src/mote/output.py` — `write_transcript()` (extend for JSON format)
- `src/mote/transcribe.py` — `transcribe_file()`, `get_wav_duration()` (used by shared helper)
- `src/mote/models.py` — `is_model_downloaded()`, `config_value_to_alias()` (used by validation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `output.py:write_transcript()` — Already handles markdown + txt; extend with "json" format branch
- `output.py:_build_filename()` — Reuse for JSON filename generation (same pattern, `.json` extension)
- `output.py:_HEADER_TEMPLATE` fields — JSON keys should mirror these exactly for consistency
- `cli.py` lines 110-117 — Orphan warning code, enhance with `mote transcribe` pointer
- `cli.py` lines 142-181 — Post-transcription logic to extract into `_run_transcription()` helper
- `models.py:is_model_downloaded()` — Direct reuse for config validation's model check
- `models.py:config_value_to_alias()` — Needed for model validation to convert config value to alias

### Established Patterns
- Function-based modules (no classes) — validation should be a `validate_config()` function in config.py
- Click decorator CLI with `@cli.command()` for new commands
- `ClickException` for user-facing errors
- `click.confirm()` for interactive prompts (already used in models_download)
- `MOTE_HOME` env var for test isolation

### Integration Points
- `cli.py:record_command()` — Add validation call before BlackHole detection, add auto-cleanup call before orphan check
- `cli.py` — New `@cli.command("transcribe")` top-level command
- `cli.py` — New `@cli.command("cleanup")` top-level command
- `config.py` — New `validate_config()` function, new `cleanup` section in default config
- `config.py:_write_default_config()` — Add `[cleanup]` section with `wav_retention_days = 7`

</code_context>

<specifics>
## Specific Ideas

- WAV retention prevents disk space issues from accumulated recordings — user specifically raised this concern
- `mote config validate` serves as a pre-flight check users can run before important meetings
- Retry prompt after failure is interactive (click.confirm), not a separate command — keeps the workflow linear
- Orphan handling is non-blocking: warn + point to `mote transcribe`, don't slow down `mote record` startup

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-cli-polish-and-config-reliability*
*Context gathered: 2026-03-29*
