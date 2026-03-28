---
phase: 4
slug: transcription-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=["tests"], pythonpath=["src"]) |
| **Quick run command** | `uv run --no-sync pytest tests/test_transcribe.py -q` |
| **Full suite command** | `uv run --no-sync pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-sync pytest tests/test_transcribe.py -q`
- **After every plan wave:** Run `uv run --no-sync pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | TRX-01 | unit | `pytest tests/test_transcribe.py::test_transcribe_local_calls_model -x` | No — W0 | pending |
| 04-01-02 | 01 | 1 | TRX-01 | unit | `pytest tests/test_transcribe.py::test_transcribe_local_no_model -x` | No — W0 | pending |
| 04-01-03 | 01 | 1 | TRX-02 | unit | `pytest tests/test_transcribe.py::test_transcribe_openai_calls_api -x` | No — W0 | pending |
| 04-01-04 | 01 | 1 | TRX-02 | unit | `pytest tests/test_transcribe.py::test_transcribe_openai_chunking -x` | No — W0 | pending |
| 04-01-05 | 01 | 1 | TRX-02 | unit | `pytest tests/test_transcribe.py::test_transcribe_openai_no_key -x` | No — W0 | pending |
| 04-01-06 | 01 | 1 | TRX-03 | unit | `pytest tests/test_transcribe.py::test_engine_from_config -x` | No — W0 | pending |
| 04-01-07 | 01 | 1 | TRX-04 | unit | `pytest tests/test_transcribe.py::test_language_from_config -x` | No — W0 | pending |
| 04-01-08 | 01 | 1 | TRX-05 | unit | `pytest tests/test_transcribe.py::test_local_progress_updates -x` | No — W0 | pending |
| 04-02-01 | 02 | 2 | TRX-03 | unit | `pytest tests/test_cli.py::test_record_engine_flag -x` | No — W0 | pending |
| 04-02-02 | 02 | 2 | TRX-04 | unit | `pytest tests/test_cli.py::test_record_language_flag -x` | No — W0 | pending |
| 04-02-03 | 02 | 2 | TRX-06 | unit | `pytest tests/test_cli.py::test_record_auto_transcribes -x` | No — W0 | pending |
| 04-02-04 | 02 | 2 | TRX-06 | unit | `pytest tests/test_cli.py::test_record_deletes_wav_on_success -x` | No — W0 | pending |
| 04-02-05 | 02 | 2 | TRX-06 | unit | `pytest tests/test_cli.py::test_record_keeps_wav_on_failure -x` | No — W0 | pending |
| 04-02-06 | 02 | 2 | TRX-06 | unit | `pytest tests/test_cli.py::test_record_no_transcribe_flag -x` | No — W0 | pending |
| 04-00-01 | — | — | CLI-03 | unit | `pytest tests/test_cli.py::test_config_show -x` | Yes | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_transcribe.py` — stubs for TRX-01 through TRX-05
- [ ] New test cases in `tests/test_cli.py` — TRX-06 and CLI flag override tests

*Existing infrastructure covers CLI-03.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rich progress bar visual rendering | TRX-05 | Visual appearance cannot be asserted in CI | Run `mote record` on a test WAV and verify progress bar renders correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
