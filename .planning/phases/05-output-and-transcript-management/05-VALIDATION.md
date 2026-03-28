---
phase: 05
slug: output-and-transcript-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --no-sync pytest tests/test_output.py -q` |
| **Full suite command** | `uv run --no-sync pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-sync pytest tests/test_output.py -q`
- **After every plan wave:** Run `uv run --no-sync pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | OUT-01, OUT-02, OUT-03 | unit | `uv run --no-sync pytest tests/test_output.py -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | CLI-05 | unit | `uv run --no-sync pytest tests/test_cli.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_output.py` — stubs for OUT-01, OUT-02, OUT-03, OUT-04
- [ ] Existing `tests/conftest.py` — `mote_home` fixture already available

*Existing infrastructure covers test framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Output directory creation with `~/Documents/mote` expansion | OUT-01 | Path.expanduser on real home dir | Run `mote record --no-transcribe`, verify dir created |

*Most behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
