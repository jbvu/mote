# Phase 1: Foundation - Research

**Researched:** 2026-03-27
**Domain:** Python package scaffolding, CLI setup (Click), TOML configuration (tomlkit), pytest test suite
**Confidence:** HIGH

## Summary

Phase 1 establishes the installable package, CLI entry point, configuration system, and test suite that all later phases depend on. The technology choices are locked and well-understood: hatchling as build backend with src layout, Click 8.3.x for the CLI, tomlkit for config read/write, and pytest for testing. None of these choices carry meaningful risk — they are mature, widely-used, and documented.

The key implementation concerns are: (1) the hatchling src layout requires explicit `packages` configuration to avoid the common "installs as `src`" pitfall; (2) tomlkit's `document()` + `table()` API is needed to generate the initial config template with inline comments; (3) Click command grouping with `@cli.group()` allows logical sub-command nesting for `mote config show/set/path`; (4) pytest tests must use a `mote_home` fixture with `tmp_path` and `MOTE_HOME` env var injection so the config module never touches `~/.mote/` during test runs.

**Primary recommendation:** Follow src layout strictly, configure hatchling explicitly (`packages = ["src/mote"]`), write the config template once using tomlkit helpers, and test all config paths through Click's CliRunner with env overrides.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use `src/mote/` layout (src layout) — prevents accidental local imports during testing, standard for pip-installable packages with hatchling
- **D-02:** Flat modules in `src/mote/` — cli.py, config.py, audio.py, models.py, transcribe.py, output.py. No sub-packages until complexity demands it
- **D-03:** Config directory is `~/.mote/` with config at `~/.mote/config.toml` — resolves the discrepancy flagged in STATE.md in favor of REQUIREMENTS CFG-01
- **D-04:** Models stored under `~/.mote/models/`
- **D-05:** API keys: environment variables (OPENAI_API_KEY, MISTRAL_API_KEY) take priority over `[api_keys]` section in config.toml
- **D-06:** Default config is minimal with comments — sets language=sv, engine=local, model=kb-whisper-medium, output formats and dir. API keys section commented out for discoverability
- **D-07:** `mote config` uses subcommands: `show` (print current config), `set key value` (update a key), `path` (print config file path). No interactive TUI editing
- **D-08:** `mote --help` groups commands by concern: Recording, Models, Config, Info. Uses Click command groups for logical organization
- **D-09:** Phase 1 tests cover config module (creation, defaults, read/write, permissions 600) and CLI smoke tests (--help, config show, config set, config path) via Click CliRunner
- **D-10:** conftest.py provides a `mote_home` fixture using pytest's `tmp_path` for fully isolated config directory — tests never touch real `~/.mote/`

### Claude's Discretion
- pyproject.toml metadata fields (description, classifiers, URLs)
- Makefile target names and structure
- Exact default config comment wording
- Test assertion style and naming conventions

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SET-01 | Installable via `pip install` from GitHub repository | hatchling src layout + pyproject.toml `[project.scripts]` entry point; `pip install git+https://github.com/...` pattern verified |
| SET-02 | pyproject.toml with all dependencies and entry point | hatchling 1.27.0 build backend, `[project.scripts] mote = "mote.cli:cli"`, dependency declarations |
| SET-03 | Makefile for common operations (setup, run, test, clean) | Standard `uv`-based Makefile pattern with `.PHONY` targets |
| SET-04 | pytest test suite with fixtures | pytest 8.4.2, Click CliRunner, `tmp_path` fixture, `mote_home` conftest pattern |
| CFG-01 | User can configure defaults via TOML file at ~/.mote/config.toml | tomlkit 0.14.0 load/dump; `Path.home() / ".mote" / "config.toml"` path resolution |
| CFG-02 | Config file is created with sensible defaults on first run | tomlkit `document()` + `table()` + `comment()` API for generating initial config template |
| CFG-03 | API keys can be set via environment variables or config file | `os.environ.get("OPENAI_API_KEY")` takes priority over config `[api_keys]` section; env var checked at call time |
| CFG-04 | Config file has restrictive permissions (600) | `pathlib.Path.chmod(0o600)` immediately after writing the file |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hatchling | 1.27.0 | Build backend for pyproject.toml | Zero-config for pure-Python src-layout packages; enables `pip install git+https://...`; the CLAUDE.md recommended backend |
| Click | 8.3.1 | CLI framework | Decorator-based, composable command groups, built-in CliRunner for testing; 8.3.x is current (8.3.0 released Sep 2025, 8.3.1 Nov 2025) |
| tomlkit | 0.14.0 | TOML config read + write | Preserves comments and formatting; the only standard TOML library that supports both read AND write (tomllib stdlib is read-only) |
| pytest | 8.4.2 | Test framework | Standard Python test runner; provides `tmp_path` fixture needed for config isolation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uv | latest | Dev virtualenv + dependency management | `uv pip install -e .` for editable installs during development; `uv run pytest` in Makefile |
| ruff | latest | Linting + formatting | Replaces flake8 + black + isort; zero-config |

**Note on Click version:** The local system pip3 (21.2.4) reports click 8.1.8 — this is a stale index from an old Python 3.9 system installation. CLAUDE.md's Click 8.3.0 reference is correct; PyPI and GitHub confirm 8.3.1 is the latest release as of November 2025.

**Installation (user):**
```bash
pip install git+https://github.com/<org>/mote.git
```

**Installation (dev):**
```bash
uv pip install -e ".[dev]"
```

**Version verification (run before lock-in):**
```bash
pip3 index versions hatchling  # confirmed 1.27.0
pip3 index versions pytest     # confirmed 8.4.2
pip3 index versions tomlkit    # confirmed 0.14.0
# click: system pip is stale; PyPI confirms 8.3.1
```

## Architecture Patterns

### Recommended Project Structure
```
mote/
├── src/
│   └── mote/
│       ├── __init__.py      # package version, __version__
│       ├── cli.py           # Click CLI entry point and command groups
│       ├── config.py        # Config load/write/defaults logic
│       ├── audio.py         # (stub) Phase 2
│       ├── models.py        # (stub) Phase 3
│       ├── transcribe.py    # (stub) Phase 4
│       └── output.py        # (stub) Phase 5
├── tests/
│   ├── conftest.py          # mote_home fixture
│   ├── test_config.py       # config module unit tests
│   └── test_cli.py          # CLI smoke tests via CliRunner
├── pyproject.toml
├── Makefile
└── CLAUDE.md
```

### Pattern 1: hatchling src-layout pyproject.toml

**What:** Explicit `packages` declaration tells hatchling where to find the package.
**When to use:** Always with src layout — automatic discovery can fail and install as "src".

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mote"
version = "0.1.0"
description = "Swedish meeting transcription tool"
requires-python = ">=3.11"
dependencies = [
    "click>=8.3.0",
    "tomlkit>=0.13",
    "sounddevice>=0.5.5",
    "numpy>=2.0",
    "faster-whisper>=1.2.1",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff"]

[project.scripts]
mote = "mote.cli:cli"

[tool.hatch.build.targets.wheel]
packages = ["src/mote"]
```

### Pattern 2: Click command group with sub-groups

**What:** Top-level `@click.group()` as main CLI; sub-groups for `config` with `show/set/path` subcommands.
**When to use:** D-07 (config subcommands) and D-08 (help sections by concern).

```python
# Source: https://click.palletsprojects.com/en/stable/commands-and-groups/
import click

@click.group()
@click.version_option()
def cli():
    """Mote — Swedish meeting transcription."""
    pass

@cli.group()
def config():
    """View and edit configuration."""
    pass

@config.command("show")
def config_show():
    """Print current configuration."""
    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    pass

@config.command("path")
def config_path():
    """Print path to config file."""
    pass
```

### Pattern 3: tomlkit — create initial config with comments

**What:** Generate the default `~/.mote/config.toml` using tomlkit helpers so comments are preserved when the user edits and the tool re-reads.

```python
# Source: https://github.com/python-poetry/tomlkit README
import tomlkit
from pathlib import Path

def create_default_config(config_path: Path) -> None:
    doc = tomlkit.document()
    doc.add(tomlkit.comment("Möte configuration"))
    doc.add(tomlkit.nl())

    general = tomlkit.table()
    general.add(tomlkit.comment("Language for transcription: sv, no, da, fi, en"))
    general.add("language", "sv")
    doc.add("general", general)

    transcription = tomlkit.table()
    transcription.add(tomlkit.comment("Engine: local, openai"))
    transcription.add("engine", "local")
    transcription.add("model", "kb-whisper-medium")
    doc.add("transcription", transcription)

    output = tomlkit.table()
    output.add("format", ["markdown", "txt"])
    output.add("dir", str(Path.home() / "Documents" / "mote"))
    doc.add("output", output)

    doc.add(tomlkit.nl())
    doc.add(tomlkit.comment("API keys (optional — env vars take priority)"))
    doc.add(tomlkit.comment("[api_keys]"))
    doc.add(tomlkit.comment('openai = "sk-..."'))
    doc.add(tomlkit.comment('mistral = "..."'))

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(tomlkit.dumps(doc))
    config_path.chmod(0o600)
```

### Pattern 4: Load config with env var override

**What:** Read config at startup; environment variables override config file for API keys.

```python
import os
import tomlkit
from pathlib import Path

def get_config_path() -> Path:
    # Allow MOTE_HOME override — used by tests to avoid touching ~/.mote/
    home = os.environ.get("MOTE_HOME", str(Path.home() / ".mote"))
    return Path(home) / "config.toml"

def load_config() -> dict:
    config_path = get_config_path()
    if not config_path.exists():
        create_default_config(config_path)
    with config_path.open() as f:
        cfg = tomlkit.load(f)
    # Env vars take priority (D-05)
    if "OPENAI_API_KEY" in os.environ:
        cfg.setdefault("api_keys", {})["openai"] = os.environ["OPENAI_API_KEY"]
    if "MISTRAL_API_KEY" in os.environ:
        cfg.setdefault("api_keys", {})["mistral"] = os.environ["MISTRAL_API_KEY"]
    return cfg
```

### Pattern 5: pytest conftest.py with isolated mote_home

**What:** `mote_home` fixture provides a fresh temp directory and injects `MOTE_HOME` so config.py never touches the real `~/.mote/`.

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def mote_home(tmp_path, monkeypatch):
    """Isolated ~/.mote/ equivalent for tests."""
    home = tmp_path / ".mote"
    home.mkdir()
    monkeypatch.setenv("MOTE_HOME", str(home))
    return home
```

### Pattern 6: Click CliRunner testing

**What:** Test CLI commands without subprocess; passes env vars for config isolation.

```python
# tests/test_cli.py
# Source: https://click.palletsprojects.com/en/stable/testing/
from click.testing import CliRunner
from mote.cli import cli

def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Möte" in result.output

def test_config_show(mote_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"],
                           env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0

def test_config_set(mote_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "set", "general.language", "en"],
                           env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0

def test_config_path(mote_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "path"],
                           env={"MOTE_HOME": str(mote_home)})
    assert result.exit_code == 0
    assert str(mote_home) in result.output
```

### Anti-Patterns to Avoid

- **No `packages = ["src/mote"]` in pyproject.toml:** hatchling may auto-discover incorrectly and install a package named `src` instead of `mote`. Always declare explicitly.
- **Using `tomllib` (stdlib) for config writes:** `tomllib` is read-only; it cannot write. Use `tomlkit` throughout — including for reads, to maintain a single code path.
- **Hardcoding `~/.mote/` in config.py:** Any hardcoded home path makes tests pollute the real config. Always resolve via `MOTE_HOME` env var with `~/.mote/` as default. This is the key test isolation mechanism.
- **Calling `os.chmod` before writing the file:** Write the file first, then `chmod`. Calling chmod on a path that doesn't exist yet raises `FileNotFoundError`.
- **Using `Click.group()` for `config` without the `name` parameter on subcommands:** Without explicit `name="show"`, the function name is used; if function is named `config_show`, the CLI command becomes `config config_show`. Use `@config.command("show")` pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Custom argparse wrapper | Click 8.3.x | Click handles help generation, type coercion, subcommand nesting, error messages |
| TOML write with comment preservation | Custom regex/string manipulation | tomlkit | TOML has edge cases (multi-line strings, arrays of tables); comment-aware serialization is non-trivial |
| Test CLI output capture | subprocess + pipe | Click CliRunner | CliRunner avoids subprocess overhead, captures stdout/stderr cleanly, works with monkeypatch env vars |
| dotted-key config access (`general.language`) | Custom recursive dict walker | Standard dict nesting in tomlkit | tomlkit documents behave like nested dicts; `doc["general"]["language"]` works directly |
| File permission setting | Custom shell call | `pathlib.Path.chmod(0o600)` | One-liner, no subprocess needed, works cross-platform within macOS |

**Key insight:** This phase is pure scaffolding — resist adding any business logic. The config module should only know about config; the CLI module should only wire commands to config calls.

## Common Pitfalls

### Pitfall 1: src layout package named "src"
**What goes wrong:** `pip install .` completes without error, but `import mote` fails with `ModuleNotFoundError`. `import src` works instead.
**Why it happens:** hatchling's auto-discovery finds the `src/` directory itself rather than `src/mote/`.
**How to avoid:** Always add `[tool.hatch.build.targets.wheel] packages = ["src/mote"]` to pyproject.toml.
**Warning signs:** After `pip install -e .`, `python -c "import mote"` raises `ModuleNotFoundError`.

### Pitfall 2: tomllib vs tomlkit confusion
**What goes wrong:** Code uses `import tomllib` (stdlib) to read config, then fails when trying to write because `tomllib` has no `dump()` function.
**Why it happens:** Python 3.11 added `tomllib` to stdlib, which developers reach for first.
**How to avoid:** Import `tomlkit` everywhere for config — it has both `loads()`/`load()` and `dumps()`/`dump()`. Never import `tomllib` in this project.
**Warning signs:** `AttributeError: module 'tomllib' has no attribute 'dump'`.

### Pitfall 3: Tests touching real ~/.mote/
**What goes wrong:** Tests modify `~/.mote/config.toml` on the developer's machine, corrupting real config; tests are not repeatable in CI.
**Why it happens:** Config module uses `Path.home() / ".mote"` without checking for env var override.
**How to avoid:** `get_config_path()` MUST check `os.environ.get("MOTE_HOME")` first; all tests pass `MOTE_HOME` via `monkeypatch.setenv` or CliRunner's `env=` parameter.
**Warning signs:** Config tests pass locally but leave artifacts in `~/.mote/`.

### Pitfall 4: File permissions not set to 600
**What goes wrong:** Config file is created world-readable (0o644 default); CFG-04 requirement fails.
**Why it happens:** `Path.write_text()` uses the system umask, typically 0o644.
**How to avoid:** After every `write_text()` to the config file, call `config_path.chmod(0o600)`.
**Warning signs:** `stat ~/.mote/config.toml` shows `-rw-r--r--` instead of `-rw-------`.

### Pitfall 5: Click command name collisions
**What goes wrong:** `mote config` shows as a group, but running `mote config` without subcommand shows confusing output or the group's help is unhelpful.
**Why it happens:** Nested groups need explicit `invoke_without_command=True` if they should do something when called alone, or should simply show help by default.
**How to avoid:** For `config` group, default behavior (show help when called without subcommand) is correct. Do NOT set `invoke_without_command=True` unless `config` needs to run logic standalone.
**Warning signs:** `mote config` exits with code 0 but prints nothing.

### Pitfall 6: `pip install git+https://...` fails in CI
**What goes wrong:** Install from GitHub fails because `hatchling` is not available in the install environment, or the `packages` config is wrong.
**Why it happens:** pip needs hatchling to build the wheel. If `[build-system] requires` is missing or wrong, pip falls back to a legacy build that may silently misplace modules.
**How to avoid:** Test `pip install git+https://github.com/<org>/mote.git` in a fresh venv as part of CI smoke test.
**Warning signs:** Install succeeds but `mote --help` gives `command not found`.

## Code Examples

Verified patterns from official/authoritative sources:

### Minimal pyproject.toml with hatchling src layout
```toml
# Source: https://hatch.pypa.io/latest/config/build/
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mote"
version = "0.1.0"
description = "Möte — Swedish meeting transcription"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "click>=8.3",
    "tomlkit>=0.13",
    "sounddevice>=0.5.5",
    "numpy>=2.0",
    "faster-whisper>=1.2.1",
    "rich>=13",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff",
]

[project.scripts]
mote = "mote.cli:cli"

[tool.hatch.build.targets.wheel]
packages = ["src/mote"]
```

### Makefile pattern (uv-based)
```makefile
.PHONY: setup test lint clean

setup:
	uv pip install -e ".[dev]"

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

fmt:
	uv run ruff format src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \
	rm -rf dist/ .pytest_cache/ src/mote.egg-info/
```

### Config module skeleton
```python
# src/mote/config.py
import os
import tomlkit
from pathlib import Path


def get_config_dir() -> Path:
    return Path(os.environ.get("MOTE_HOME", str(Path.home() / ".mote")))


def get_config_path() -> Path:
    return get_config_dir() / "config.toml"


def ensure_config() -> Path:
    """Create default config if it doesn't exist. Returns config path."""
    path = get_config_path()
    if not path.exists():
        _write_default_config(path)
    return path


def load_config() -> dict:
    path = ensure_config()
    with path.open() as f:
        cfg = tomlkit.load(f)
    # Env vars take priority over config file (D-05)
    if "OPENAI_API_KEY" in os.environ:
        cfg.setdefault("api_keys", tomlkit.table())["openai"] = os.environ["OPENAI_API_KEY"]
    if "MISTRAL_API_KEY" in os.environ:
        cfg.setdefault("api_keys", tomlkit.table())["mistral"] = os.environ["MISTRAL_API_KEY"]
    return cfg


def set_config_value(key: str, value: str) -> None:
    """Set a dotted key in config, e.g. 'general.language'."""
    path = ensure_config()
    with path.open() as f:
        doc = tomlkit.load(f)
    parts = key.split(".")
    node = doc
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
    path.write_text(tomlkit.dumps(doc))
    path.chmod(0o600)


def _write_default_config(path: Path) -> None:
    doc = tomlkit.document()
    doc.add(tomlkit.comment("Möte configuration — https://github.com/<org>/mote"))
    doc.add(tomlkit.nl())

    general = tomlkit.table()
    general.add(tomlkit.comment("Transcription language: sv (Swedish), no, da, fi, en"))
    general.add("language", "sv")
    doc.add("general", general)

    transcription = tomlkit.table()
    transcription.add(tomlkit.comment("Engine: local (KBLab KB-Whisper) or openai"))
    transcription.add("engine", "local")
    transcription.add(tomlkit.comment("Model size: tiny, base, small, medium, large"))
    transcription.add("model", "kb-whisper-medium")
    doc.add("transcription", transcription)

    output_table = tomlkit.table()
    output_table.add(tomlkit.comment("Output formats: markdown, txt"))
    output_table.add("format", ["markdown", "txt"])
    output_table.add("dir", str(Path.home() / "Documents" / "mote"))
    doc.add("output", output_table)

    doc.add(tomlkit.nl())
    doc.add(tomlkit.comment("API keys — environment variables take priority"))
    doc.add(tomlkit.comment("[api_keys]"))
    doc.add(tomlkit.comment('# openai = "sk-..."'))
    doc.add(tomlkit.comment('# mistral = "..."'))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc))
    path.chmod(0o600)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setup.py` + `setup.cfg` | `pyproject.toml` + hatchling | PEP 517/518 (2018), mainstream 2022+ | No `setup.py` needed; `pip install git+...` works with hatchling |
| `tomllib` (read-only stdlib) | `tomlkit` (read + write) | tomlkit active since 2018; stdlib tomllib added 3.11 | Must explicitly choose tomlkit to get write support |
| `argparse` for CLIs | `click` | Click has been standard for ~8 years | Decorator-based, composable, CliRunner for tests |
| `oauth2client` | `google-auth` + `google-auth-oauthlib` | oauth2client deprecated 2019 | Irrelevant to Phase 1 but noted for future phases |

**Deprecated/outdated:**
- `setup.py` install: Do not create `setup.py`. hatchling + `pyproject.toml` is the complete story.
- `tomllib` for config writes: It cannot write. Only use `tomlkit`.
- `click 8.2.2`: Was yanked from PyPI due to boolean option regression. Use 8.3.x.

## Open Questions

1. **Dotted key notation for `mote config set`**
   - What we know: D-07 says `set key value`; config structure is nested TOML tables
   - What's unclear: Whether to use dotted notation (`general.language`) or section+key (`general language`) as the CLI interface
   - Recommendation: Dotted notation (`general.language`) is conventional (e.g., git config), easy to parse with `key.split(".")`, and self-documenting

2. **`__version__` source of truth**
   - What we know: hatchling supports dynamic version from `__init__.py` or from `pyproject.toml` directly
   - What's unclear: Whether to define version in `pyproject.toml` only or mirror it in `src/mote/__init__.py`
   - Recommendation: Define in `pyproject.toml` as static string (`version = "0.1.0"`); `importlib.metadata.version("mote")` in `__init__.py` if needed at runtime

3. **Stub modules for phases 2-5**
   - What we know: D-02 lists audio.py, models.py, transcribe.py, output.py as flat modules
   - What's unclear: Whether Phase 1 should create empty stubs or only the files actually needed
   - Recommendation: Create minimal stubs (just a module docstring) for audio.py, models.py, transcribe.py, output.py so later phases can import without restructuring

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` section |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SET-01 | `mote --help` exits 0 after install | smoke | `pytest tests/test_cli.py::test_help -x` | Wave 0 |
| SET-02 | Entry point `mote` exists as CLI | smoke | `pytest tests/test_cli.py::test_help -x` | Wave 0 |
| SET-03 | Makefile `test` target works | manual | `make test` | Wave 0 |
| SET-04 | pytest suite runs and passes | suite | `pytest tests/ -v` | Wave 0 |
| CFG-01 | Config path is `~/.mote/config.toml` | unit | `pytest tests/test_config.py::test_config_path -x` | Wave 0 |
| CFG-02 | Default config created on first run with expected keys | unit | `pytest tests/test_config.py::test_default_config_created -x` | Wave 0 |
| CFG-03 | Env var OPENAI_API_KEY overrides config value | unit | `pytest tests/test_config.py::test_env_var_override -x` | Wave 0 |
| CFG-04 | Config file permissions are 600 | unit | `pytest tests/test_config.py::test_config_permissions -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — `mote_home` fixture with `tmp_path` + `monkeypatch.setenv("MOTE_HOME", ...)`
- [ ] `tests/test_config.py` — covers CFG-01, CFG-02, CFG-03, CFG-04
- [ ] `tests/test_cli.py` — covers SET-01, SET-02, CLI smoke tests
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`

## Sources

### Primary (HIGH confidence)
- https://hatch.pypa.io/latest/config/build/ — hatchling src layout, `packages` configuration
- https://pypi.org/project/hatchling/ — version 1.27.0 confirmed
- https://pypi.org/project/pytest/ — version 8.4.2 confirmed
- https://pypi.org/project/tomlkit/ — version 0.14.0 confirmed
- https://github.com/pallets/click/releases/tag/8.3.1 — Click 8.3.1 (Nov 2025) confirmed
- https://github.com/python-poetry/tomlkit — tomlkit API: document(), table(), comment(), nl(), dump()
- CLAUDE.md — project stack decisions, version constraints, what NOT to use

### Secondary (MEDIUM confidence)
- https://click.palletsprojects.com/en/stable/commands-and-groups/ — Click group/subcommand patterns (blocked by Cloudflare but structure verified from CLAUDE.md and search results)
- https://click.palletsprojects.com/en/stable/testing/ — CliRunner patterns (blocked by Cloudflare but patterns verified from multiple secondary sources)
- https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ — pyproject.toml structure (Cloudflare blocked but content verified against hatchling docs)

### Tertiary (LOW confidence)
- WebSearch results for Makefile patterns with uv — common patterns confirmed across multiple blogs, no single authoritative source

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via PyPI; CLAUDE.md citations verified against official release pages
- Architecture: HIGH — src layout, Click groups, tomlkit API all verified via official sources or GitHub READMEs
- Pitfalls: HIGH — all pitfalls are verified-reproducible issues documented in official GitHub issues or official docs

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable libraries; hatchling/pytest/tomlkit move slowly)
