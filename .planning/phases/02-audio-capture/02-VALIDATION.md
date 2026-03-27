---
phase: 2
slug: audio-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_audio.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_audio.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | AUD-01 | unit | `uv run pytest tests/test_audio.py::test_find_blackhole_found -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | AUD-01 | unit | `uv run pytest tests/test_audio.py::test_find_blackhole_not_found -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | AUD-02 | unit | `uv run pytest tests/test_audio.py::test_record_writes_wav -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | AUD-03 | unit | `uv run pytest tests/test_audio.py::test_rms_db -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | AUD-04 | unit | `uv run pytest tests/test_audio.py::test_make_display_elapsed -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | CLI-01 | smoke | `uv run pytest tests/test_cli.py::test_record_help -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | CLI-04 | unit | `uv run pytest tests/test_cli.py::test_status_idle -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | CLI-04 | unit | `uv run pytest tests/test_cli.py::test_status_recording -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | CLI-06 | integration | manual (requires BlackHole hardware) | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_audio.py` — stubs for AUD-01, AUD-02, AUD-03, AUD-04
- [ ] `tests/test_cli.py` — extend with record/status tests for CLI-01, CLI-04

*Existing infrastructure covers pytest framework — no new framework config needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ctrl+C stop writes WAV and exits cleanly | CLI-06 | Requires BlackHole hardware device and real audio stream | 1. Start `mote record` 2. Wait 5s 3. Press Ctrl+C 4. Verify WAV file exists and is playable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
