---
phase: 8
slug: google-drive-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_drive.py tests/test_cli.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_drive.py tests/test_cli.py -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | INT-03 | unit | `pytest tests/test_config.py::test_default_config_has_destinations -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | INT-03 | unit | `pytest tests/test_config.py::test_destinations_active_default -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | INT-03 | unit (CLI mock) | `pytest tests/test_cli.py::test_destination_flag_override -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | INT-04 | unit (mock flow) | `pytest tests/test_drive.py::test_auth_flow_saves_token -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | INT-04 | unit (mock creds) | `pytest tests/test_drive.py::test_auth_status_shows_when_valid -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | INT-04 | unit (mock service) | `pytest tests/test_drive.py::test_upload_all_formats -x` | ❌ W0 | ⬜ pending |
| 08-02-04 | 02 | 2 | INT-04 | unit (mock fail) | `pytest tests/test_cli.py::test_drive_upload_failure_is_warning -x` | ❌ W0 | ⬜ pending |
| 08-02-05 | 02 | 2 | INT-04 | unit (mock service) | `pytest tests/test_cli.py::test_upload_command -x` | ❌ W0 | ⬜ pending |
| 08-02-06 | 02 | 1 | INT-04 | unit | `pytest tests/test_drive.py::test_token_file_permissions -x` | ❌ W0 | ⬜ pending |
| 08-02-07 | 02 | 2 | INT-04 | unit (mock service) | `pytest tests/test_drive.py::test_folder_id_cached -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_drive.py` — stubs for all INT-04 drive module tests (auth flow, token permissions, upload, folder caching)
- [ ] Additional tests in `tests/test_cli.py` — stubs for INT-03 destination flag, INT-04 CLI integration (upload failure warning, upload command)
- [ ] Additional tests in `tests/test_config.py` — stubs for INT-03 destinations config section

*Existing `conftest.py` with `mote_home` fixture is sufficient — no new shared fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `mote auth google` opens browser consent page | INT-04 | Requires real browser + Google account | Run `mote auth google`, verify browser opens to consent screen |
| Token persists across CLI invocations | INT-04 | Requires real OAuth flow completion | Complete auth, run `mote auth google` again, verify status shown without re-auth |
| File actually appears in Google Drive | INT-04 | Requires real Drive account | Complete auth, run `mote upload <file>`, verify file in Drive folder |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
