# Phase 8: Google Drive Integration - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Transcripts are automatically uploaded to Google Drive after each recording, completing the capture-to-Drive workflow. Includes OAuth2 authentication, configurable destinations, and a manual upload command for retries. Local files are always written first; Drive upload is additive and failure-tolerant.

</domain>

<decisions>
## Implementation Decisions

### OAuth2 Credentials
- **D-01:** Ship a Google Cloud "installed app" (Desktop type) client_id embedded in the source code. Standard practice for open-source CLI tools (gcloud, gh). Users run `mote auth google` with zero credential setup.
- **D-02:** Store OAuth refresh token at `~/.mote/google_token.json` with permissions 600, consistent with existing config layout.
- **D-03:** Use `access_type='offline'` and `prompt='consent'` with `run_local_server(port=0)` per roadmap decision. OOB flow deprecated.

### Destination Config
- **D-04:** Config schema uses simple list: `[destinations] active = ["local"]`. Adding `"drive"` enables auto-upload. `--destination` flag overrides per-run.
- **D-05:** Local files are always written regardless of destination flag. Drive upload is additive, not a replacement. Matches roadmap decision: "local files always written first."
- **D-06:** `[destinations.drive]` subsection holds Drive-specific config (folder_name).

### Upload Behavior
- **D-07:** Upload ALL configured output formats (md, txt, json — whatever the user has in `output.format`) to Drive, not just markdown.
- **D-08:** Use named folder with auto-create: `[destinations.drive] folder_name = "Mote Transcripts"`. On first upload, search Drive for folder by name; if not found, create it. Cache folder_id locally to avoid repeated API searches.
- **D-09:** Destination errors are warnings, not failures — one-line warning with retry hint: "Drive upload failed: {reason}. Transcripts saved locally. Run 'mote upload' to retry."

### Auth Command UX
- **D-10:** `mote auth google` when already authenticated shows status (email, token validity, folder) and offers re-auth via `click.confirm("Re-authenticate? [y/N]")`. Non-destructive by default.
- **D-11:** First-time `mote auth google` opens browser consent page, stores refresh token, confirms success with email display.

### Upload Command
- **D-12:** Add `mote upload [file]` command for manual/retry uploads to Drive. Uploads a local transcript file on demand. Completes the Drive workflow for failed auto-uploads.

### Claude's Discretion
- Drive API scope selection (drive.file vs broader scope)
- Folder ID caching mechanism (in token file, separate cache file, or config)
- File naming convention on Drive (mirror local filenames or add metadata)
- Whether `mote upload` without arguments uploads the most recent transcript or requires explicit file path

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Technology stack (google-api-python-client 2.193.0, google-auth-oauthlib 1.x, google-auth 2.38.0), conventions, constraints
- `.planning/PROJECT.md` — Core value, Google OAuth decisions, evolution rules
- `.planning/REQUIREMENTS.md` — INT-03 (configurable destinations), INT-04 (Google Drive upload)

### Prior Phase Context
- `.planning/phases/06-cli-polish-and-config-reliability/06-CONTEXT.md` — _run_transcription() helper design (D-12), config validation patterns, output format decisions
- `.planning/phases/05-output-and-transcript-management/05-CONTEXT.md` — write_transcript() API, filename conventions, output format structure

### Existing Code
- `src/mote/cli.py` — `_run_transcription()` (integration point for Drive upload), `record_command()`, `transcribe_command()`, existing command group patterns (`config`, `models`, `audio`)
- `src/mote/config.py` — `load_config()`, `_write_default_config()` (add [destinations] section), `get_config_dir()`
- `src/mote/output.py` — `write_transcript()` (returns list of written file paths — these are the files to upload)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli.py:_run_transcription()` — Returns `list[Path]` of written files; this is the hook point for Drive upload after local write
- `config.py:get_config_dir()` — Returns `~/.mote/` Path; reuse for token storage path
- `config.py:_write_default_config()` — Extend with `[destinations]` section for new installs
- `config.py:set_config_value()` — Can set destination config values
- `cli.py` command group patterns — `@cli.group()` with subcommands (config, models, audio) — reuse for `auth` group

### Established Patterns
- Function-based modules (no classes) — Drive module should be functions
- Lazy imports for heavy dependencies (Phase 4 pattern) — apply to google-api-python-client imports
- `click.ClickException` for user-facing errors
- `click.confirm()` for interactive prompts
- Mock-heavy testing with `unittest.mock.patch` for external service calls
- `MOTE_HOME` env var for test isolation of config/token paths

### Integration Points
- `cli.py:_run_transcription()` — Add Drive upload call after `write_transcript()` returns
- `cli.py` — New `@cli.group() def auth()` command group with `google` subcommand
- `cli.py` — New `@cli.command("upload")` top-level command
- `config.py:_write_default_config()` — Add `[destinations]` and `[destinations.drive]` sections
- `config.py:validate_config()` — Optionally validate Drive config (token exists if drive in active destinations)
- New module: `src/mote/drive.py` — Google Drive API wrapper functions

</code_context>

<specifics>
## Specific Ideas

- Upload should happen silently on success — only the filename confirmation line, no extra "uploaded to Drive" noise unless verbose mode
- The folder auto-create pattern (search by name, create if missing, cache ID) keeps setup friction near zero
- Token at `~/.mote/google_token.json` means `mote config show` could display auth status alongside config
- `mote upload` command enables a clean retry workflow without re-transcribing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-google-drive-integration*
*Context gathered: 2026-03-29*
