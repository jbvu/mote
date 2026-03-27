# Phase 1: Foundation - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Project scaffolding and configuration system. This phase delivers: a pip-installable Python package with CLI entry point, TOML-based configuration with sensible defaults, and a pytest test suite. All later phases build on this foundation.

</domain>

<decisions>
## Implementation Decisions

### Package Structure
- **D-01:** Use `src/mote/` layout (src layout) — prevents accidental local imports during testing, standard for pip-installable packages with hatchling
- **D-02:** Flat modules in `src/mote/` — cli.py, config.py, audio.py, models.py, transcribe.py, output.py. No sub-packages until complexity demands it

### Config Path & Defaults
- **D-03:** Config directory is `~/.mote/` with config at `~/.mote/config.toml` — resolves the discrepancy flagged in STATE.md in favor of REQUIREMENTS CFG-01
- **D-04:** Models stored under `~/.mote/models/`
- **D-05:** API keys: environment variables (OPENAI_API_KEY, MISTRAL_API_KEY) take priority over `[api_keys]` section in config.toml
- **D-06:** Default config is minimal with comments — sets language=sv, engine=local, model=kb-whisper-medium, output formats and dir. API keys section commented out for discoverability

### CLI Command Design
- **D-07:** `mote config` uses subcommands: `show` (print current config), `set key value` (update a key), `path` (print config file path). No interactive TUI editing
- **D-08:** `mote --help` groups commands by concern: Recording, Models, Config, Info. Uses Click command groups for logical organization

### Test Strategy
- **D-09:** Phase 1 tests cover config module (creation, defaults, read/write, permissions 600) and CLI smoke tests (--help, config show, config set, config path) via Click CliRunner
- **D-10:** conftest.py provides a `mote_home` fixture using pytest's `tmp_path` for fully isolated config directory — tests never touch real `~/.mote/`

### Claude's Discretion
- pyproject.toml metadata fields (description, classifiers, URLs)
- Makefile target names and structure
- Exact default config comment wording
- Test assertion style and naming conventions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Full technology stack, version constraints, patterns, and what NOT to use
- `.planning/PROJECT.md` — Vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — SET-01 through SET-04 (project setup), CFG-01 through CFG-04 (configuration)
- `.planning/ROADMAP.md` — Phase 1 success criteria and scope boundary

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — this phase establishes the patterns all later phases follow

### Integration Points
- pyproject.toml `[project.scripts]` entry point: `mote = "mote.cli:cli"`
- Config module will be imported by every subsequent phase (audio, models, transcription, output)

</code_context>

<specifics>
## Specific Ideas

- Default config template shown in discussion: `[general]` with language, `[transcription]` with engine and model, `[output]` with format and dir, commented `[api_keys]`
- Output directory default: `~/Documents/mote`
- CLI help preview: "Möte — Swedish meeting transcription" as tagline

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-27*
