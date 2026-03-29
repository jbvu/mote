# Phase 9: NotebookLM Integration - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Experimental upload of transcripts to Google NotebookLM via the unofficial `notebooklm-py` library. Best-effort integration with clear expectations: sessions expire weekly, failures are warnings not errors, and the feature may be replaced by documentation if the library is dead/unmaintained. Local files and Drive upload are always unaffected.

</domain>

<decisions>
## Implementation Decisions

### Viability Gate
- **D-01:** Research phase MUST check notebooklm-py GitHub status (last commit, open issues, API stability) before planning proceeds. If the library is dead or broken, Phase 9 pivots to documenting "use Drive + manually add to NotebookLM" as the recommended workflow instead of writing code.

### Authentication
- **D-02:** Use cookie extraction from Chrome's cookie store (notebooklm-py's default approach). User must be logged into Google in Chrome. `mote auth notebooklm` extracts and stores the session cookies.
- **D-03:** Store session credentials at `~/.mote/notebooklm_session.json` with permissions 600, consistent with google_token.json pattern from Phase 8.

### Destination Config
- **D-04:** Add `"notebooklm"` as a valid destination in the existing `[destinations]` config. Same pattern as Drive: add to `active` list to enable, or use `--destination notebooklm` per-run override.
- **D-05:** Add `[destinations.notebooklm]` subsection in config for NotebookLM-specific settings (notebook name).

### Upload Behavior
- **D-06:** Upload markdown file only (.md) to NotebookLM. Plain text and JSON add no value for NotebookLM's source ingestion.
- **D-07:** Use a single "Mote Transcripts" notebook. Each transcription adds the markdown as a new source. Mirrors the Drive folder approach. Auto-create notebook if it doesn't exist; cache notebook ID locally.

### Failure & Expiry UX
- **D-08:** Same pattern as Drive (D-09 from Phase 8): attempt upload silently, on auth failure show "NotebookLM session expired. Run: mote auth notebooklm". No proactive session checks.
- **D-09:** NotebookLM failures never propagate — local files and Drive upload are unaffected. Warning format matches Drive: one-line with retry hint.

### Auth Command UX
- **D-10:** `mote auth notebooklm` added as subcommand under existing `auth` group (alongside `google`). Shows status when already authenticated, offers re-auth.

### Claude's Discretion
- Exact cookie extraction mechanism (direct Chrome cookie DB read vs notebooklm-py's built-in method)
- Session credential storage format (mirror notebooklm-py's internal format or normalize)
- Whether `mote upload` command should also support NotebookLM as a target (or only auto-upload)
- Notebook naming convention and whether it's configurable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Technology stack, conventions, constraints; notes notebooklm-py as experimental
- `.planning/PROJECT.md` — Core value, roadmap decisions including "NotebookLM is best-effort optional"
- `.planning/REQUIREMENTS.md` — INT-05 (NotebookLM upload via notebooklm-py)

### Prior Phase Context
- `.planning/phases/08-google-drive-integration/08-CONTEXT.md` — Drive destination pattern (D-04 through D-12), auth group design, warning format for failures
- `.planning/phases/06-cli-polish-and-config-reliability/06-CONTEXT.md` — _run_transcription() helper, config validation patterns

### Existing Code (from Phase 8)
- `src/mote/drive.py` — Google Drive module pattern to mirror: function-based, lazy imports, token persistence with chmod 600
- `src/mote/cli.py` — `auth` command group (add `notebooklm` subcommand), `_run_transcription()` (add NotebookLM upload after Drive), `--destination` flag (add "notebooklm" choice)
- `src/mote/config.py` — `_write_default_config()` (add [destinations.notebooklm] section), `set_config_value()` (already supports 3-part keys)

### External
- `notebooklm-py` GitHub repository — MUST be checked by researcher for viability (D-01)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `drive.py` — Complete pattern to mirror: module constants, lazy imports, token persistence, folder ID caching, upload function
- `cli.py:auth` group — Already exists with `google` subcommand; add `notebooklm` alongside it
- `cli.py:_run_transcription()` — Already has Drive upload block; add NotebookLM block after it with same try/except warning pattern
- `config.py:_write_default_config()` — Already has `[destinations]` and `[destinations.drive]`; extend with `[destinations.notebooklm]`
- `config.py:set_config_value()` — Already handles 3-part dotted keys

### Established Patterns
- Destination errors are warnings (Phase 8 D-09): try/except around upload, click.echo warning, never raise
- Lazy imports for heavy dependencies (notebooklm-py imports inside function bodies)
- Function-based modules with no classes
- Token/session files at `~/.mote/` with chmod 0o600
- Mock-heavy testing for external service calls
- `--destination` flag with `click.Choice` validator

### Integration Points
- `cli.py:_run_transcription()` — Add NotebookLM upload block after Drive block
- `cli.py:auth` group — Add `notebooklm` subcommand
- `cli.py:record_command` and `transcribe_command` — `--destination` Choice list needs "notebooklm" added
- `config.py:_write_default_config()` — Add `[destinations.notebooklm]` section
- New module: `src/mote/notebooklm.py` — NotebookLM API wrapper functions

</code_context>

<specifics>
## Specific Ideas

- Mirror Drive's architecture exactly: notebooklm.py module with auth/upload functions, lazy imports, same error handling pattern
- Cookie extraction keeps auth friction low — user just needs Chrome logged into Google
- "Mote Transcripts" notebook mirrors "Mote Transcripts" Drive folder — consistent naming
- If notebooklm-py is dead, the phase deliverable becomes documentation (not code): a section in README explaining "transcripts go to Drive, then manually add to NotebookLM"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-notebooklm-integration*
*Context gathered: 2026-03-29*
