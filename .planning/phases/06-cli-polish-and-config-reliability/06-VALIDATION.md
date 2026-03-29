---
phase: 6
slug: cli-polish-and-config-reliability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `make test` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make test`
- **After every plan wave:** Run `make test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CLI-07 | unit | `make test` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | REL-01 | unit | `make test` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | CLI-08 | unit | `make test` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | INT-02 | unit | `make test` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | CLI-07 | integration | `make test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_validate.py` — stubs for config validation (REL-01)
- [ ] `tests/test_transcribe_cmd.py` — stubs for transcribe command (CLI-07)
- [ ] `tests/test_json_output.py` — stubs for JSON output (INT-02)

*Existing test infrastructure (pytest, conftest.py, MOTE_HOME isolation) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive retry prompt after failure | CLI-08 | Requires terminal input simulation | Run `mote record`, kill transcription mid-way, verify retry prompt appears |
| Orphan WAV detection on startup | CLI-08 | Requires stale WAV file state | Place WAV in recordings dir, run `mote record`, verify warning |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
