# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 01-foundation
**Areas discussed:** Package structure, Config path & defaults, CLI command design, Test strategy

---

## Package Structure

### Layout

| Option | Description | Selected |
|--------|-------------|----------|
| src/mote/ layout | Prevents accidental imports, standard for pip-installable packages | ✓ |
| Flat mote/ layout | Simpler, but can cause import confusion during development | |

**User's choice:** src/mote/ layout (Recommended)
**Notes:** None

### Module Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Flat modules | All modules in src/mote/ — cli.py, config.py, etc. Refactor later if needed | ✓ |
| Sub-packages now | Group by concern from the start: engines/, core/ | |

**User's choice:** Flat modules (Recommended)
**Notes:** None

---

## Config Path & Defaults

### Config Directory

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.mote/ | Matches REQUIREMENTS CFG-01. Config at ~/.mote/config.toml, models under ~/.mote/models/ | ✓ |
| ~/.config/mote/ | Follows XDG spec but doesn't match REQUIREMENTS | |

**User's choice:** ~/.mote/ (Recommended)
**Notes:** Resolves discrepancy flagged in STATE.md

### API Key Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Env vars take priority | Check env vars first, fall back to [api_keys] in config.toml | ✓ |
| Config file only | All keys in config.toml only | |
| Env vars only | No keys in config file at all | |

**User's choice:** Env vars take priority (Recommended)
**Notes:** None

### Default Config

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal with comments | Essential defaults set, optional settings commented out for discoverability | ✓ |
| Complete with all options | Every config key present | |
| Bare minimum | Only engine and language | |

**User's choice:** Minimal with comments (Recommended)
**Notes:** None

---

## CLI Command Design

### mote config Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| show/set subcommands | `mote config show`, `mote config set key value`, `mote config path` | ✓ |
| Print path only | Just prints config file path, user edits manually | |
| Interactive TUI | Rich-based interactive editor | |

**User's choice:** show/set subcommands (Recommended)
**Notes:** None

### Help Output

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by concern | Commands grouped: Recording, Models, Config, Info | ✓ |
| Flat list | Alphabetical, default Click behavior | |

**User's choice:** Grouped by concern (Recommended)
**Notes:** None

---

## Test Strategy

### Phase 1 Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Config + CLI smoke tests | Config creation/defaults/permissions, CLI via CliRunner | ✓ |
| Config only | Just config module tests | |
| Full coverage targets | Set thresholds like 90% | |

**User's choice:** Config + CLI smoke tests (Recommended)
**Notes:** None

### Test Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| tmp_path fixture | conftest.py mote_home fixture using tmp_path | ✓ |
| Monkeypatch HOME | Override HOME env var per test | |

**User's choice:** tmp_path fixture (Recommended)
**Notes:** None

---

## Claude's Discretion

- pyproject.toml metadata fields
- Makefile target names and structure
- Default config comment wording
- Test assertion style and naming conventions

## Deferred Ideas

None — discussion stayed within phase scope
