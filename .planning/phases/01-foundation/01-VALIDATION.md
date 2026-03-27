---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `make test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | SET-01 | unit | `python -m pytest tests/test_package.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | SET-02 | unit | `python -m pytest tests/test_cli.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | CFG-01 | unit | `python -m pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | CFG-02 | unit | `python -m pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | CFG-03 | unit | `python -m pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 1 | CFG-04 | unit | `python -m pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (tmp_path, MOTE_HOME env override)
- [ ] `tests/test_package.py` — stubs for SET-01, SET-02
- [ ] `tests/test_cli.py` — stubs for SET-03, SET-04
- [ ] `tests/test_config.py` — stubs for CFG-01, CFG-02, CFG-03, CFG-04
- [ ] `pytest` — install as dev dependency

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `pip install git+https://...` works | SET-01 | Requires clean venv + network | Create fresh venv, pip install from GitHub, run `mote --help` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
