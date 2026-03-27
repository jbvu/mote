# Phase 2: Audio Capture - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

BlackHole recording with live status feedback. This phase delivers: system audio capture from virtual meetings via BlackHole, a `mote record` CLI command with live Rich display (level meter + elapsed time), graceful Ctrl+C stop that writes a WAV file, a `mote status` command, and BlackHole device detection with clear error messaging.

</domain>

<decisions>
## Implementation Decisions

### Recording Display
- **D-01:** Use Rich library live display with a single updating line showing animated level bar, elapsed time, and dB reading
- **D-02:** Show device name once at recording start, then only level + elapsed time during recording
- **D-03:** Display "Ctrl+C to stop" hint below the live line

### WAV File Handling
- **D-04:** Store temporary WAV files in `~/.mote/recordings/` (consistent with config path pattern)
- **D-05:** On abnormal exit (crash/kill), leave orphaned WAV files in place. On next `mote record`, detect orphans and warn the user — let them decide to keep or delete
- **D-06:** WAV format: 16kHz mono 16-bit (per PROJECT.md constraints, ~1.9MB/min)

### BlackHole Detection
- **D-07:** Auto-detect BlackHole by searching `sounddevice.query_devices()` for devices containing "BlackHole" in the name
- **D-08:** Prefer "BlackHole 2ch" when multiple BlackHole devices are found (2ch is the recommended install). Fall back to other BlackHole variants only if 2ch is absent
- **D-09:** If no BlackHole device is found, refuse to start recording with a clear error message including install instructions (`brew install blackhole-2ch`)

### Status Tracking
- **D-10:** Use a PID file at `~/.mote/mote.pid` to track active recording
- **D-11:** `mote status` checks if the PID file exists and whether the process is alive — reports "Recording in progress" or "Idle"
- **D-12:** `mote record` refuses to start if another recording is active (PID alive). If PID is stale (process dead), warn, clean up the PID file, and allow start

### Claude's Discretion
- sounddevice stream configuration details (buffer size, callback structure)
- Rich layout specifics (Panel, Live, progress bar widget choices)
- WAV file naming convention within ~/.mote/recordings/
- Exact error message wording for BlackHole not found
- Signal handler implementation for Ctrl+C (SIGINT)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Setup
- `CLAUDE.md` — Full technology stack: sounddevice 0.5.5, Rich 13.x, WAV format specs, device/compute_type patterns, what NOT to use (PyAudio, threading)
- `.planning/PROJECT.md` — Constraints (BlackHole 2ch, macOS only, 16kHz mono 16-bit), key decisions
- `.planning/REQUIREMENTS.md` — AUD-01 through AUD-04 (audio capture), CLI-01 (record command), CLI-04 (status command), CLI-06 (Ctrl+C graceful stop)
- `.planning/ROADMAP.md` — Phase 2 success criteria and scope boundary

### Prior Phase Context
- `.planning/phases/01-foundation/01-CONTEXT.md` — Package structure (src/mote/ layout), config patterns, CLI design decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mote/config.py` — `get_config_dir()` returns `~/.mote/` path (use for recordings/ and PID file paths), `load_config()` for reading settings
- `src/mote/cli.py` — Click group `cli` ready for new `record` and `status` commands
- `src/mote/audio.py` — Empty stub, ready for recording logic

### Established Patterns
- Click decorator-based CLI commands with `@cli.command()` or `@cli.group()`
- `MOTE_HOME` env var for test isolation of all `~/.mote/` paths
- tomlkit for config read/write with comment preservation
- `ClickException` for user-facing errors

### Integration Points
- `cli.py` needs `record` command and `status` command added to the `cli` group
- `audio.py` will be imported by `cli.py` for recording functions
- Config dir (`get_config_dir()`) is the parent for `recordings/` and `mote.pid`

</code_context>

<specifics>
## Specific Ideas

- Rich live display mockup: `Recording  00:42:15  ████████████▓░░░░░░░  -12dB` with "Ctrl+C to stop" below
- Device info shown once at start: "Recording from BlackHole 2ch (16kHz mono)"
- Orphan detection message: "Found recording from [timestamp] in ~/.mote/recordings/. Keep or delete?"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-audio-capture*
*Context gathered: 2026-03-27*
