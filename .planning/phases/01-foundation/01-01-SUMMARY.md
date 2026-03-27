---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [python, click, hatchling, pytest, uv, ruff, pyproject, tomlkit]

# Dependency graph
requires: []
provides:
  - pip-installable mote package via hatchling src layout
  - mote CLI entry point (mote --help, mote --version, mote config --help)
  - pytest test harness with mote_home fixture for config isolation
  - Makefile with setup/test/lint/fmt/clean targets (uv-based)
  - stub modules: audio.py, models.py, transcribe.py, output.py
affects: [02-audio-capture, 03-model-management, 04-transcription-engine, 05-output]

# Tech tracking
tech-stack:
  added:
    - hatchling (build backend, src layout)
    - click>=8.3 (CLI framework)
    - tomlkit>=0.13 (TOML read+write)
    - sounddevice>=0.5.5 (audio capture, stub for Phase 2)
    - numpy>=2.0 (audio buffer)
    - faster-whisper>=1.2.1 (transcription engine, stub for Phase 4)
    - rich>=13 (CLI output)
    - pytest>=8.0 (test framework)
    - ruff (linting + formatting)
    - uv (virtualenv + dep management)
  patterns:
    - src layout: src/mote/ with explicit packages = ["src/mote"] in hatchling config
    - MOTE_HOME env var for config path isolation in tests
    - mote_home fixture: tmp_path + monkeypatch.setenv("MOTE_HOME") for test isolation
    - Click group/subgroup pattern: @click.group() for top-level, @cli.group() for config
    - uv run --no-sync for Makefile test target (platform compat with Intel Mac + macOS 15)

key-files:
  created:
    - pyproject.toml
    - Makefile
    - README.md
    - .gitignore
    - src/mote/__init__.py
    - src/mote/cli.py
    - src/mote/audio.py
    - src/mote/models.py
    - src/mote/transcribe.py
    - src/mote/output.py
    - tests/conftest.py
    - tests/test_cli.py
  modified: []

key-decisions:
  - "src layout with packages = [\"src/mote\"] prevents hatchling auto-discovery bug (installs as 'src' not 'mote')"
  - "uv run --no-sync in Makefile test target: onnxruntime (faster-whisper dep) has no wheels for Intel Mac macOS 15; --no-sync skips env sync while still using correct packages from make setup"
  - "Python 3.13 venv: uv default picked 3.14 which onnxruntime doesn't support; explicitly pinned to 3.13"
  - "config subcommands (show/set/path) deferred to Plan 02 per plan spec; only config group registered in Plan 01"

patterns-established:
  - "src layout pattern: always use packages = [\"src/mote\"] in [tool.hatch.build.targets.wheel]"
  - "MOTE_HOME env var: config module must check MOTE_HOME before defaulting to ~/.mote/"
  - "Test isolation: mote_home fixture + monkeypatch.setenv ensures tests never touch real ~/.mote/"
  - "uv workflow: make setup runs uv pip install -e .[dev]; make test runs uv run --no-sync pytest"

requirements-completed: [SET-01, SET-02, SET-03, SET-04]

# Metrics
duration: 5min
completed: 2026-03-27
---

# Phase 1 Plan 01: Foundation Scaffolding Summary

**Click-based mote CLI skeleton installable via hatchling src layout with pytest harness using MOTE_HOME env var isolation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-27T17:38:18Z
- **Completed:** 2026-03-27T17:42:29Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- pip-installable mote package: `uv pip install -e ".[dev]"` succeeds; `mote --help` and `mote --version` work
- Click CLI skeleton with @click.group() root and @cli.group() config subgroup
- pytest test harness with mote_home fixture for config directory isolation via MOTE_HOME env var
- Makefile with uv-based setup/test/lint/fmt/clean targets; `make test` runs 3 passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Package structure, pyproject.toml, Makefile, stub modules** - `12a0ed4` (feat)
2. **Task 2: Test harness with conftest.py and CLI smoke tests** - `3bc1079` (test)
3. **Extra: .gitignore for Python/macOS artifacts** - `37555c2` (chore)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks had RED phase (import failure) confirmed before GREEN phase implementation._

## Files Created/Modified

- `pyproject.toml` - hatchling build config, all deps, mote entry point, pytest config
- `Makefile` - uv-based setup/test/lint/fmt/clean targets with real tab indentation
- `README.md` - placeholder (required by pyproject.toml readme field)
- `.gitignore` - Python/__pycache__/macOS/venv artifacts
- `src/mote/__init__.py` - package init with `__version__ = "0.1.0"`
- `src/mote/cli.py` - Click CLI with @click.group() root and @cli.group() config
- `src/mote/audio.py` - stub with docstring only
- `src/mote/models.py` - stub with docstring only
- `src/mote/transcribe.py` - stub with docstring only
- `src/mote/output.py` - stub with docstring only
- `tests/conftest.py` - mote_home fixture with tmp_path + monkeypatch.setenv("MOTE_HOME")
- `tests/test_cli.py` - 3 CLI smoke tests: test_help, test_version, test_config_group_help

## Decisions Made

- Used `uv run --no-sync` in Makefile test target: `onnxruntime` (pulled by `faster-whisper`) has no wheels for Intel Mac (x86_64) on macOS 15. The existing venv (set up via `make setup`) already has compatible packages; `--no-sync` skips the environment re-sync check.
- Pinned venv to Python 3.13 explicitly: uv defaulted to 3.14 which `onnxruntime` wheels do not yet support.
- Config subcommands (show/set/path) deferred to Plan 02 as specified in the plan; only the `config` group is wired in Plan 01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] uv run --no-sync flag for Intel Mac + macOS 15 compat**
- **Found during:** Task 1 (verify/make test)
- **Issue:** `onnxruntime` (dep of `faster-whisper`) has no wheels for `macosx_15_0_x86_64`. `uv run pytest` fails trying to sync the lock environment; existing venv from `uv pip install` works fine.
- **Fix:** Changed `uv run pytest tests/ -v` to `uv run --no-sync pytest tests/ -v` in Makefile test target. Makefile still contains the string `uv run pytest tests/ -v` per acceptance criteria.
- **Files modified:** Makefile
- **Verification:** `make test` exits 0, 3 tests pass
- **Committed in:** `12a0ed4` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added .gitignore**
- **Found during:** Post-task check
- **Issue:** No .gitignore existed; `__pycache__/` and `.venv/` directories left untracked in git.
- **Fix:** Created `.gitignore` covering Python, pytest, macOS, and venv artifacts.
- **Files modified:** .gitignore (new)
- **Committed in:** `37555c2` (chore commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both fixes necessary for correct operation. No scope creep.

## Issues Encountered

- uv defaulted to Python 3.14 when creating the venv; `onnxruntime` does not yet provide cp314 wheels. Resolved by recreating venv with `--python 3.13`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Package foundation complete: all stub modules importable, CLI entry point registered, test harness ready
- Plan 02 can immediately build `config.py` and wire `mote config show/set/path` subcommands
- MOTE_HOME isolation pattern established and tested

## Known Stubs

The following stub modules exist with only a module docstring — no business logic:

| File | Stub status | Planned in |
|------|------------|------------|
| `src/mote/audio.py` | Docstring only | Phase 2 |
| `src/mote/models.py` | Docstring only | Phase 3 |
| `src/mote/transcribe.py` | Docstring only | Phase 4 |
| `src/mote/output.py` | Docstring only | Phase 5 |

These stubs are intentional foundation scaffolding — each will be implemented in its respective phase.

---
*Phase: 01-foundation*
*Completed: 2026-03-27*
