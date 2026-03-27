---
phase: 01-foundation
plan: 02
subsystem: infra
tags: [python, tomlkit, click, config, toml, permissions, env-override]

# Dependency graph
requires:
  - phase: 01-01
    provides: pip-installable mote package, click CLI skeleton with config group, mote_home pytest fixture
provides:
  - TOML config module (get_config_dir, get_config_path, ensure_config, load_config, set_config_value)
  - Auto-creation of ~/.mote/config.toml with sensible defaults on first access
  - Config file permissions 600 enforced on create and write
  - Env var override for OPENAI_API_KEY/MISTRAL_API_KEY at load time without persisting to disk
  - Working CLI: mote config show/set/path
  - 13 config unit tests + 4 CLI integration tests = 20 total passing tests
affects: [02-audio-capture, 03-model-management, 04-transcription-engine, 05-output, web-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - tomlkit read+write preserving comments; never use tomllib (read-only)
    - Env var override at load time: inject into in-memory dict, do NOT write back to file
    - chmod 600 applied in both _write_default_config and set_config_value
    - dot-notation key addressing: 'section.field' split to [section][field] for tomlkit access
    - Hatchling editable install requires uv pip install -e . after adding new source modules

key-files:
  created:
    - src/mote/config.py
    - tests/test_config.py
  modified:
    - src/mote/cli.py
    - tests/test_cli.py

key-decisions:
  - "Env var override is in-memory only: OPENAI_API_KEY/MISTRAL_API_KEY injected into loaded dict but never written back to config.toml (security: credentials never persisted by accident)"
  - "api_keys section absent from default config.toml: commented out to avoid empty section in file; env vars inject it at runtime only"
  - "set_config_value only accepts existing sections/keys: prevents typos silently creating orphan config values"
  - "Hatchling editable install with --no-deps required after adding new source files: package must be reinstalled for new modules to be importable in the venv"

patterns-established:
  - "Config module pattern: get_config_dir() checks MOTE_HOME first, falls back to ~/.mote/"
  - "Permissions pattern: path.chmod(0o600) called after every file write (create + update)"
  - "Env override pattern: inject into tomlkit doc in-memory, never serialize back"
  - "CLI error pattern: catch KeyError/ValueError in command, re-raise as click.ClickException for clean user output"

requirements-completed: [CFG-01, CFG-02, CFG-03, CFG-04]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 1 Plan 02: Configuration System Summary

**TOML config module with 600-permission auto-creation, in-memory env var override for API keys, and mote config show/set/path CLI commands**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T17:44:56Z
- **Completed:** 2026-03-27T17:46:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- config.py implements full TOML config lifecycle: auto-create defaults, load with env override, set value preserving comments
- Config file has 0o600 permissions enforced on every write (create and update)
- OPENAI_API_KEY and MISTRAL_API_KEY override api_keys at load time — never written back to disk
- `mote config show/set/path` all functional with proper error handling
- 20 tests total: 13 config unit tests + 4 CLI integration tests + 3 original CLI smoke tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Config module with defaults, load, set, env override (TDD)** - `f7e5082` (feat)
2. **Task 2: Wire config subcommands into CLI + CLI tests** - `fe5df35` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 was TDD — RED phase confirmed (ModuleNotFoundError), GREEN phase achieved 13/13 passing._

## Files Created/Modified

- `src/mote/config.py` - Full config module: get_config_dir/path/ensure_config/load_config/set_config_value/_write_default_config
- `tests/test_config.py` - 13 unit tests covering CFG-01 through CFG-04
- `src/mote/cli.py` - Added config show/set/path subcommands with import from config module
- `tests/test_cli.py` - Added 4 CLI integration tests for config commands

## Decisions Made

- Env var override is in-memory only: OPENAI_API_KEY/MISTRAL_API_KEY injected into loaded dict but never written to config.toml — credentials cannot be accidentally persisted
- api_keys section absent from default config.toml: kept as commented-out hints only; env vars inject the section at runtime
- set_config_value raises KeyError for unknown sections/keys: prevents silent typo-based config corruption
- Hatchling editable install requires `uv pip install -e . --no-deps` after adding new source modules (not a true editable install in the Python sense)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reinstalled package after adding new source modules**
- **Found during:** Task 1 GREEN phase verification
- **Issue:** After creating src/mote/config.py, tests still failed with ModuleNotFoundError — hatchling's editable install does not auto-pick up new modules without reinstall
- **Fix:** Ran `uv pip install -e ".[dev]" --no-deps` to refresh the installed package. Same fix needed after Task 2 modified cli.py.
- **Files modified:** None (install side-effect only)
- **Verification:** `uv run --no-sync pytest tests/test_config.py -v` went from error to 13 passed
- **Committed in:** Not in task commit (install operation, not a file change)

---

**Total deviations:** 1 auto-fixed (blocking install)
**Impact on plan:** Necessary for test execution. No scope creep.

## Issues Encountered

- Hatchling editable install requires explicit reinstall when new source files are added to the package. This is an Intel Mac / hatchling behavior — on systems with true editable installs, this would not be needed. Documented as a pattern for future tasks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Config foundation complete: all later phases can `from mote.config import load_config` to get typed config
- MOTE_HOME isolation pattern proven: all tests use tmp_path isolation, never touch real ~/.mote/
- Plan 03 (audio capture) can access audio device config from transcription section
- API key loading pattern established for Plans 04/05 (OpenAI/Mistral engines)

## Known Stubs

None — this plan delivered complete functionality with no stubs.

---
*Phase: 01-foundation*
*Completed: 2026-03-27*
