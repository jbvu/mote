---
phase: 01-foundation
plan: "03"
subsystem: testing
tags: [pytest, pyproject.toml, pythonpath, src-layout, icloud]

requires:
  - phase: 01-foundation-02
    provides: CLI, config module, and 20 passing tests in src layout

provides:
  - pytest pythonpath = ["src"] config enabling make test to pass without manual PYTHONPATH
  - Closed Phase 1 verification gap: all 20 tests pass via make test in clean shell

affects: []

tech-stack:
  added: []
  patterns:
    - "pytest pythonpath config: add pythonpath = [\"src\"] to [tool.pytest.ini_options] when using src layout on paths with spaces"

key-files:
  created: []
  modified:
    - pyproject.toml

key-decisions:
  - "Use pytest pythonpath config (not PYTHONPATH env var or .pth file) to handle src layout on iCloud Drive paths with spaces — .pth processor silently skips paths containing spaces"

patterns-established:
  - "pytest src layout fix: pythonpath = [\"src\"] in pyproject.toml is the canonical solution for src-layout packages on macOS iCloud paths"

requirements-completed: [SET-03, SET-04]

duration: 1min
completed: 2026-03-27
---

# Phase 01 Plan 03: Pytest Pythonpath Fix Summary

**pytest pythonpath = ["src"] config added to pyproject.toml, closing the make test gap caused by iCloud Drive's space-containing path silently breaking .pth file injection**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-27T17:59:19Z
- **Completed:** 2026-03-27T17:59:44Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `pythonpath = ["src"]` to `[tool.pytest.ini_options]` in pyproject.toml
- `make test` now exits 0 with all 20 tests passing in a clean shell without any manual PYTHONPATH export
- Closed the single outstanding gap from Phase 1 verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pythonpath to pytest config in pyproject.toml** - `53b3f5c` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `pyproject.toml` - Added `pythonpath = ["src"]` under `[tool.pytest.ini_options]`

## Decisions Made

The root cause was that Python's `.pth` file processor silently skips entries that contain spaces in the path. The iCloud Drive path (`~/Library/Mobile Documents/...`) contains a space in "Mobile Documents", so the editable install's `.pth` injection never placed `src/` in `sys.path`. The fix is to configure pytest itself to inject the path via its `pythonpath` setting, which is not subject to the `.pth` limitation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 is fully complete: project scaffold, config module, CLI, and all 20 tests pass via `make test`
- Ready to proceed to Phase 2 (audio capture)

---
*Phase: 01-foundation*
*Completed: 2026-03-27*

## Self-Check: PASSED

- FOUND: pyproject.toml
- FOUND: .planning/phases/01-foundation/01-03-SUMMARY.md
- FOUND: commit 53b3f5c
