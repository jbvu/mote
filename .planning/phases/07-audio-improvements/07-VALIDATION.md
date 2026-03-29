---
phase: 7
slug: audio-improvements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_audio.py tests/test_cli.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_audio.py tests/test_cli.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | AUD-05 | unit | `uv run pytest tests/test_audio.py -k "switch" -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | AUD-05 | unit | `uv run pytest tests/test_cli.py -k "switch" -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | AUD-05 | unit | `uv run pytest tests/test_cli.py -k "restore" -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | AUD-05 | unit | `uv run pytest tests/test_cli.py -k "advisory" -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | AUD-05 | unit | `uv run pytest tests/test_cli.py -k "crash_recovery" -x` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | AUD-05 | unit | `uv run pytest tests/test_cli.py -k "audio_restore" -x` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | AUD-06 | unit | `uv run pytest tests/test_audio.py -k "silence" -x` | ❌ W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | AUD-06 | unit | `uv run pytest tests/test_audio.py -k "silence_warn" -x` | ❌ W0 | ⬜ pending |
| 07-03-03 | 03 | 2 | AUD-06 | unit | `uv run pytest tests/test_audio.py -k "silence_reset" -x` | ❌ W0 | ⬜ pending |
| 07-03-04 | 03 | 2 | AUD-06 | unit | `uv run pytest tests/test_audio.py -k "display_silence" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_audio.py` — add silence detection tests (SILENCE_THRESHOLD_DB, make_display silence_warning, silence counter reset)
- [ ] `tests/test_cli.py` — add SwitchAudioSource tests (mocked subprocess), crash recovery tests, `mote audio restore` tests

*Existing test infrastructure covers framework — only new test functions needed, no new files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Actual audio switch audible | AUD-05 | Requires real audio hardware | Run `mote record`, verify system audio switches to BlackHole, Ctrl+C, verify restored |
| Actual silence detection trigger | AUD-06 | Requires real recording with no audio | Run `mote record` with BlackHole but no meeting, wait 30s, verify warning appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
