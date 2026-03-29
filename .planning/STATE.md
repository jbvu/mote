---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: planning
stopped_at: Phase 6 context gathered
last_updated: "2026-03-29T11:22:06.732Z"
last_activity: 2026-03-28
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 10
  completed_plans: 10
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-29)

**Core value:** Accurate Swedish-language meeting transcription that actually works
**Current focus:** Phase 06 — cli-polish-and-config-reliability

## Current Position

Phase: 06
Plan: Not started
Status: Roadmap created — ready to plan Phase 6
Last activity: 2026-03-28

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-foundation P01 | 5 | 2 tasks | 12 files |
| Phase 01-foundation P02 | 2 | 2 tasks | 4 files |
| Phase 01-foundation P03 | 1 | 1 tasks | 1 files |
| Phase 02-audio-capture P01 | 2 | 1 tasks | 2 files |
| Phase 03-model-management P01 | 4 | 2 tasks | 4 files |
| Phase 04-transcription-engine P01 | 309 | 2 tasks | 5 files |
| Phase 04-transcription-engine P02 | 420 | 2 tasks | 2 files |
| Phase 05 P01 | 126 | 1 tasks | 2 files |
| Phase 05 P02 | 10 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stack confirmed: Python 3.11+, faster-whisper 1.2.1, sounddevice, Click, Flask, tomlkit
- Apple Silicon: use device="cpu", compute_type="int8" — CTranslate2 MPS is experimental
- Config path: ~/.mote/config.toml (REQUIREMENTS uses ~/.mote/, PROJECT.md context mentions ~/.config/mote/ — clarify at Phase 1 planning)
- [Phase 01-foundation]: src layout with packages=[src/mote] prevents hatchling auto-discovery installing as 'src' not 'mote'
- [Phase 01-foundation]: uv run --no-sync in Makefile: onnxruntime has no wheels for Intel Mac macOS 15; --no-sync skips env sync
- [Phase 01-foundation]: Python 3.13 venv: uv defaulted to 3.14 which onnxruntime doesn't support
- [Phase 01-foundation]: Env var override is in-memory only: OPENAI_API_KEY/MISTRAL_API_KEY never written back to config.toml
- [Phase 01-foundation]: set_config_value raises KeyError for unknown sections/keys to prevent silent config corruption
- [Phase 01-foundation]: Hatchling editable install requires reinstall after adding new source modules
- [Phase 01-foundation]: Use pytest pythonpath config (not PYTHONPATH env var or .pth file) to handle src layout on iCloud Drive paths with spaces — .pth processor silently skips paths containing spaces
- [Phase 02-audio-capture]: make_display uses HH:MM:SS format (not MM:SS) so recordings > 1 hour display correctly
- [Phase 02-audio-capture]: Ctrl+C hint printed once before Live context — simpler than Group/newline in Live
- [Phase 02-audio-capture]: Patch target for mocked CLI functions is mote.cli.* not mote.audio.* — Click imports functions into cli module namespace
- [Phase 02-audio-capture]: find_blackhole_device includes numeric 'index' key via enumerate() — required for sd.InputStream(device=int)
- [Phase 03-model-management]: Use try_to_load_from_cache (not WhisperModel) for download check — avoids loading GB into RAM
- [Phase 03-model-management]: ALLOW_PATTERNS mirrors faster-whisper's internal list exactly — mismatched patterns cause silent re-download at transcription time
- [Phase 03-model-management]: config_value_to_alias() bridges kb-whisper-{size} config format to CLI alias — both naming conventions coexist
- [Phase 04-transcription-engine]: Lazy imports for WhisperModel and OpenAI inside transcribe functions to avoid slow startup and missing-dep errors
- [Phase 04-transcription-engine]: api_keys added as real TOML table in default config (not comments) to enable mote config set api_keys.openai
- [Phase 04-transcription-engine]: get_wav_duration called before transcribe_file so duration is available even after WAV deletion
- [Phase 04-transcription-engine]: Empty string api_key treated as None — normalizes config default empty string to absent key
- [Phase 05-01]: YAML frontmatter in .md files with date/duration/words/engine/language/model; plain .txt files contain transcript text only
- [Phase 05-01]: list_transcripts returns [] silently for missing/malformed files; sorted newest-first by mtime
- [Phase 05]: write_transcript called before wav_path.unlink() — WAV preservation on failure requires this ordering
- [Phase 05]: mote list defaults to 20 most recent transcripts; --all shows unbounded list
- [v2.0 roadmap]: Phase 6 must ship _run_transcription() helper before destinations are wired — both record and transcribe share the post-transcription delivery path
- [v2.0 roadmap]: Config validation: absent v2 keys get silent defaults; error only on present-but-invalid values — must not break v1 configs
- [v2.0 roadmap]: Destination errors are warnings not failures — local files always written first; Drive/NotebookLM failure never appears as transcription failure
- [v2.0 roadmap]: Audio recovery file: write ~/.mote/audio_restore.json before switching to BlackHole; try/finally alone is insufficient for SIGKILL scenarios
- [v2.0 roadmap]: Google OAuth: always pass access_type='offline' and prompt='consent' to run_local_server(); use port=0 only (OOB flow deprecated Oct 2022)
- [v2.0 roadmap]: NotebookLM is best-effort optional — wrap all calls in try/except; surface as warnings; Drive-first is the stable path; check notebooklm-py GitHub issues before starting Phase 9

### Pending Todos

- Check notebooklm-py GitHub issues and recent commits before planning Phase 9 — if broken/unmaintained, skip Phase 9 and document Drive-as-intermediary as the recommended workflow
- Verify SwitchAudioSource works on macOS 14/15 before implementing Phase 7

### Blockers/Concerns

- None currently

## Session Continuity

Last session: 2026-03-29T11:22:06.724Z
Stopped at: Phase 6 context gathered
Resume file: .planning/phases/06-cli-polish-and-config-reliability/06-CONTEXT.md
