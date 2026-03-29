---
phase: 06-cli-polish-and-config-reliability
verified: 2026-03-29T12:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run `mote transcribe <real_wav>` with an actual recorded WAV file"
    expected: "Transcript files written to ~/Documents/mote with completion summary printed"
    why_human: "Requires BlackHole + real WAV; transcribe_file is mocked in all tests"
  - test: "Set engine=invalid in config.toml, run `mote record`, verify it exits before the BlackHole prompt"
    expected: "Error message visible before any device detection output"
    why_human: "Integration-level ordering concern that tests verify functionally but a human can confirm the UX clearly"
---

# Phase 6: CLI Polish and Config Reliability Verification Report

**Phase Goal:** Users can transcribe existing WAV files, recover from failures without losing recordings, and trust that startup catches misconfiguration before wasting meeting time
**Verified:** 2026-03-29
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `mote transcribe <file>` accepts a WAV and produces transcript output with engine/language/name flags | VERIFIED | `transcribe_command` at cli.py:272-337 accepts `click.Path(exists=True)`, passes --engine/--language/--name/--output-format through to `_run_transcription()`; tests `test_transcribe_command`, `test_transcribe_flags`, `test_transcribe_output_format_json` all pass |
| 2 | When transcription fails, WAV is kept and user is prompted to retry | VERIFIED | `while True:` retry loop at cli.py:199-212 (record) and 323-337 (transcribe) — on `Exception` prints "WAV kept at", calls `click.confirm("Retry transcription?")`. Tests `test_transcribe_retry_yes`, `test_transcribe_retry_no`, `test_record_retry_yes` all pass |
| 3 | On `mote record` startup, orphaned WAVs are detected and user pointed to `mote transcribe` | VERIFIED | cli.py:150-158 calls `find_orphan_recordings()`, emits warning with names, then `click.echo("Transcribe them with: mote transcribe <file>")`. Test `test_record_orphan_warning` asserts `"mote transcribe" in result.output` and passes |
| 4 | Starting `mote record` with invalid engine/missing model/malformed path prints error and exits before recording | VERIFIED | cli.py:134-142 calls `validate_config(cfg)` before `find_blackhole_device()`; on errors raises `ClickException`. Tests `test_record_validates_engine` and `test_record_validates_model` verify `mock_bh.assert_not_called()` and `mock_rec.assert_not_called()`, both pass |
| 5 | `mote transcribe <file> --output-format json` produces a JSON transcript file | VERIFIED | output.py:111-126 `if "json" in formats:` branch produces flat 7-key JSON with `ensure_ascii=False`; cli.py:279-280 `--output-format json` option on transcribe_command. Test `test_transcribe_output_format_json` verifies `"json" in call_args[2]` and passes; `test_write_json_swedish_chars` verifies UTF-8 literal characters |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mote/config.py` | `validate_config()` and `cleanup_old_wavs()` | VERIFIED | Both functions present at lines 64-121; `validate_config()` performs 4 checks per D-03; `cleanup_old_wavs()` uses mtime comparison; `[cleanup]` section added to `_write_default_config()` at lines 156-159 |
| `src/mote/output.py` | JSON branch in `write_transcript()` | VERIFIED | Lines 111-126 contain complete `if "json" in formats:` branch; `json.dumps(..., ensure_ascii=False)` at line 123 |
| `src/mote/cli.py` | `_run_transcription()`, `transcribe_command`, `config_validate`, `cleanup_command` | VERIFIED | `_run_transcription()` at lines 345-378; `transcribe_command` at lines 272-337; `config_validate` at lines 70-89; `cleanup_command` at lines 250-269 |
| `tests/test_config.py` | `validate_config` and `cleanup_old_wavs` tests | VERIFIED | 10 new tests present: `test_validate_config_valid`, `test_validate_config_invalid_engine`, `test_validate_config_missing_model`, `test_validate_config_openai_no_key_warning`, `test_validate_config_v1_compat`, `test_validate_config_bad_output_dir`, `test_cleanup_old_wavs_deletes_expired`, `test_cleanup_old_wavs_keeps_recent`, `test_cleanup_old_wavs_empty_dir`, `test_default_config_has_cleanup_section` |
| `tests/test_output.py` | JSON output tests | VERIFIED | 6 new tests: `test_write_json`, `test_write_json_fields`, `test_write_json_field_types`, `test_write_json_swedish_chars`, `test_write_json_alongside_md`, `test_write_json_filename` |
| `tests/test_cli.py` | `transcribe_command`, retry, validation, cleanup tests | VERIFIED | 20+ new tests covering all Plan 02 and Plan 03 behaviors; all 52 cli tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py _run_transcription` | `transcribe.py transcribe_file` | direct call at line 363 | WIRED | `transcript = transcribe_file(wav_path, engine, language, model_alias, api_key)` |
| `cli.py _run_transcription` | `output.py write_transcript` | direct call at lines 365-368 | WIRED | `written = write_transcript(transcript, output_dir, formats, duration, engine, language, model_alias, name, timestamp=timestamp)` |
| `cli.py transcribe_command` | `cli.py _run_transcription` | direct call at lines 325-329 | WIRED | `_run_transcription(..., delete_wav=False, timestamp=ts)` |
| `cli.py record_command` | `config.py validate_config` | called before BlackHole detection at lines 135-142 | WIRED | `errors, warnings = validate_config(cfg)` precedes `find_blackhole_device()` at line 161 |
| `cli.py transcribe_command` | `config.py validate_config` | called at top of function at lines 284-290 | WIRED | `errors, warnings = validate_config(cfg)` is first logic after function entry |
| `cli.py record_command` | `config.py cleanup_old_wavs` | called before orphan check at lines 144-147 | WIRED | `cleanup_old_wavs(recordings_dir, retention_days)` precedes `find_orphan_recordings()` at line 150 |
| `config.py validate_config` | `models.py is_model_downloaded` | module-level import at line 9, called at line 85 | WIRED | `from mote.models import is_model_downloaded, config_value_to_alias` — module-level import, called inside engine=="local" branch |

### Data-Flow Trace (Level 4)

This phase produces CLI commands and library functions, not UI components. Data flows are through function call chains, not async state. Key flows verified:

| Flow | Source | Path | Status |
|------|--------|------|--------|
| WAV mtime → transcript filename | `wav_file.stat().st_mtime` at cli.py:309 | `datetime.fromtimestamp()` → `ts` → passed as `timestamp=ts` to `_run_transcription` → to `write_transcript` | FLOWING |
| validate_config errors → pre-flight exit | `validate_config(cfg)` returns `(errors, warnings)` | `if errors:` raises `ClickException` before `find_blackhole_device()` | FLOWING |
| cleanup_old_wavs → recordings dir | `cfg.get("cleanup", {}).get("wav_retention_days", 7)` → `cleanup_old_wavs(recordings_dir, retention_days)` | Reads real mtime on glob results, deletes if expired | FLOWING |
| JSON payload → file | 7-key dict constructed in `write_transcript()` | `json.dumps(..., ensure_ascii=False)` → `json_path.write_text(encoding="utf-8")` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 99 phase-6 tests pass | `.venv/bin/pytest tests/test_config.py tests/test_output.py tests/test_cli.py -q` | 99 passed in 1.46s | PASS |
| Full suite (excluding pre-existing failure) | `.venv/bin/pytest -q` | 189 passed, 1 pre-existing failure (test_download_model_passes_tqdm_class — unrelated to phase 6) | PASS |
| `validate_config` import available | `from mote.config import validate_config, cleanup_old_wavs` | Verified by test_config.py imports at lines 17-18 | PASS |
| `transcribe` subcommand registered | `cli.py` has `@cli.command("transcribe")` at line 272 | Present in source | PASS |
| `config validate` subcommand registered | `cli.py` has `@config.command("validate")` at line 70 | Present in source | PASS |
| `cleanup` top-level command registered | `cli.py` has `@cli.command("cleanup")` at line 250 | Present in source | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| REL-01 | 06-01, 06-03 | Config validated on startup — invalid engine names, missing models, malformed paths caught early; absent v2 keys in v1 configs get silent defaults | SATISFIED | `validate_config()` in config.py:64-106 performs all 4 checks; wired into `record_command` before BlackHole detection (cli.py:135-142) and at top of `transcribe_command` (cli.py:284-290); v1-compat tested by `test_validate_config_v1_compat` |
| INT-02 | 06-01, 06-02 | User can get JSON output format alongside Markdown and plain text | SATISFIED | `if "json" in formats:` branch in output.py:111-126; `--output-format json` flag on both `record_command` (cli.py:114-115) and `transcribe_command` (cli.py:279-280); 6 JSON tests pass |
| CLI-07 | 06-02 | User can transcribe an existing WAV file via `mote transcribe <file>` with same engine/language flags as `mote record` | SATISFIED | `transcribe_command` at cli.py:272-337 with `click.Path(exists=True)`, identical `--engine`/`--language`/`--name`/`--output-format` options; `_run_transcription()` shared between both commands |
| CLI-08 | 06-02, 06-03 | On transcription failure, user prompted to retry with kept WAV; orphaned WAVs detected on next `mote record` and offered for transcription | SATISFIED | Retry loop at cli.py:199-212 (record) and 323-337 (transcribe); orphan detection at cli.py:150-158 with `"mote transcribe <file>"` pointer; auto-cleanup at cli.py:144-147 runs silently before orphan check |

All 4 phase requirements satisfied. No orphaned requirements found — REQUIREMENTS.md traceability table maps all 4 IDs to Phase 6 with status Complete.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

Scan performed on: `src/mote/config.py`, `src/mote/output.py`, `src/mote/cli.py`, `tests/test_config.py`, `tests/test_output.py`, `tests/test_cli.py`

No TODOs, FIXMEs, placeholder returns, empty implementations, or hardcoded empty data found in production paths. The one pre-existing test failure (`test_download_model_passes_tqdm_class` in `tests/test_models.py`) is unrelated to phase 6 — it tests internal tqdm class wrapping in `models.py` which was not modified in this phase.

### Human Verification Required

#### 1. End-to-end transcribe from real WAV

**Test:** Run `mote transcribe /path/to/real_meeting.wav` against an actual WAV file with a downloaded KB-Whisper model
**Expected:** Transcript files written to `~/Documents/mote/`, completion message with word count and duration printed
**Why human:** All tests mock `transcribe_file` and `write_transcript`; integration through real audio processing cannot be verified programmatically

#### 2. Pre-flight validation UX ordering

**Test:** Set `engine = "invalid"` in `~/.mote/config.toml`, run `mote record`, observe terminal output
**Expected:** Error message about invalid engine appears immediately, with no BlackHole device detection message at all
**Why human:** Tests verify `mock_bh.assert_not_called()` but the user-visible UX ordering (error text before any device output) is a human judgement call

### Gaps Summary

No gaps. All 5 success criteria from the ROADMAP are implemented and tested. All 4 requirement IDs (REL-01, INT-02, CLI-07, CLI-08) are satisfied with implementation evidence and passing tests. All key wiring links are confirmed present in source code. The full phase 6 test suite (99 tests across test_config.py, test_output.py, test_cli.py) passes in 1.46s.

---

_Verified: 2026-03-29_
_Verifier: Claude (gsd-verifier)_
