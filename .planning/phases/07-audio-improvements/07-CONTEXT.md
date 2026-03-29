# Phase 7: Audio Improvements - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Auto-switch system audio output to BlackHole before recording and restore after stop. Detect sustained silence during recording and warn the user inline. Handle crash recovery when audio was not restored. Add `mote audio restore` standalone command.

</domain>

<decisions>
## Implementation Decisions

### Audio Switching via SwitchAudioSource
- **D-01:** Detect SwitchAudioSource via `which SwitchAudioSource` at `mote record` startup. If missing, print advisory every time and continue (graceful degradation — user routes audio manually).
- **D-02:** When SwitchAudioSource is available, always auto-switch output to BlackHole on `mote record` — no confirmation, no config opt-in. This is the core value of the feature.
- **D-03:** Print one-line status on switch: `Switched audio output to BlackHole 2ch (was: MacBook Pro Speakers)`. On stop: `Restored audio output to MacBook Pro Speakers`.
- **D-04:** Before switching, write `~/.mote/audio_restore.json` with the previous output device name. Delete the file after successful restore. This is the crash recovery anchor.

### Silence Detection
- **D-05:** Silence threshold: Claude picks the appropriate dB value based on testing patterns and the existing `rms_db()` function (floors at -60dB).
- **D-06:** Duration: warn after 30 seconds of sustained silence (all chunks below threshold).
- **D-07:** Repetition: warn once per silent stretch. If audio resumes then goes silent again, warn again. No spamming during continuous silence.
- **D-08:** Threshold and duration are hardcoded constants — not configurable in config.toml. Keep it simple.

### Crash Recovery
- **D-09:** On `mote record` startup, check for `~/.mote/audio_restore.json`. If found, auto-restore the original output device silently, print `Restored audio output to [device] (from previous crash)`, delete the file, then continue with normal recording flow.
- **D-10:** Add `mote audio restore` standalone command — reads `audio_restore.json` and restores the device. Useful when user just wants their speakers back without starting a new recording.

### Warning Presentation
- **D-11:** Silence warning appears inline in the Rich live display: `Recording  00:01:45  ▁▁▁▁▁  -58dB  ⚠ Silence detected — check audio routing`. Returns to normal display when audio resumes.
- **D-12:** Warning text is amber/yellow styled in the Rich display. The hint "check audio routing" is included (short, not verbose).

### Claude's Discretion
- Exact silence dB threshold value (D-05)
- Implementation of `audio` CLI command group structure
- Error handling for SwitchAudioSource failures (device not found, permission errors)
- Whether `mote audio restore` also appears as `mote restore` alias

</decisions>

<specifics>
## Specific Ideas

- The silence warning should feel like an inline status change, not an intrusive alert — the recording display line gains a warning suffix that disappears when audio returns
- Advisory for missing SwitchAudioSource should mention `brew install switchaudio-osx` as the install path
- The restore JSON file pattern mirrors the existing PID file pattern in `audio.py` — same directory, same lifecycle (write before action, delete after cleanup)

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above and the following project files:

### Audio implementation
- `src/mote/audio.py` — Current audio capture implementation: `rms_db()`, `make_level_bar()`, `make_display()`, `record_session()`, PID file lifecycle pattern
- `src/mote/cli.py` lines 106-199 — `record_command()` with BlackHole detection, pre-flight validation, orphan detection flow

### Project constraints
- `.planning/ROADMAP.md` Phase 7 section — Success criteria, requirement mappings (AUD-05, AUD-06)
- `.planning/REQUIREMENTS.md` — AUD-05 (auto-switch), AUD-06 (silence warning) requirement definitions
- `.planning/STATE.md` — Pending todo: "Verify SwitchAudioSource works on macOS 14/15 before implementing Phase 7"

### Prior phase decisions
- `.planning/phases/02-audio-capture/02-CONTEXT.md` — BlackHole detection patterns (D-07, D-08, D-09), Rich live display decisions (D-01)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `audio.rms_db()` — Already computes dB from float32 audio chunks. Direct reuse for silence threshold checking.
- `audio.make_display()` — Rich Text builder for live recording display. Extend to include silence warning suffix.
- `audio.make_level_bar()` — Maps dB to ASCII bar. Already handles the -60dB to 0dB range.
- PID file pattern (`pid_path.write_text()` / `pid_path.unlink()`) — Same lifecycle pattern for `audio_restore.json`.

### Established Patterns
- Device detection via `sd.query_devices()` in `find_blackhole_device()` — SwitchAudioSource integration adds to this flow, doesn't replace it.
- Pre-flight checks in `record_command()` — Crash recovery check fits naturally before BlackHole detection (line ~160).
- `threading.Event` + queue pattern in `record_session()` — Silence tracking runs in the same main-thread drain loop.

### Integration Points
- `record_session()` — Add silence tracking state (timer, warned flag) to the main drain loop.
- `record_command()` — Add SwitchAudioSource detection, crash recovery check, and audio switch/restore calls.
- `cli.py` — Add `audio` command group with `restore` subcommand.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-audio-improvements*
*Context gathered: 2026-03-29*
