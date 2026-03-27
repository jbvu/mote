# Phase 2: Audio Capture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 02-audio-capture
**Areas discussed:** Recording display, WAV file handling, BlackHole detection, Status tracking

---

## Recording Display

### Audio level indicator style

| Option | Description | Selected |
|--------|-------------|----------|
| Rich live display | Single updating line with animated level bar + elapsed time using Rich library. Clean, stays in one place. | ✓ |
| Minimal text | Simple updating line with ASCII characters, no Rich dependency needed | |
| You decide | Claude picks the approach that fits the codebase best | |

**User's choice:** Rich live display
**Notes:** None

### Display content beyond level + time

| Option | Description | Selected |
|--------|-------------|----------|
| Level + time only | Keep it clean — just the audio meter and elapsed time. Device info shown once at start. | ✓ |
| Add file size | Show growing WAV file size alongside level and time | |
| Add device name | Persistently show which BlackHole device is being captured | |

**User's choice:** Level + time only
**Notes:** Device name shown once at recording start, not persistently

---

## WAV File Handling

### Temporary WAV file location

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.mote/recordings/ | Dedicated dir inside Mote config home. Easy to find, survives crashes. | ✓ |
| System temp dir | OS temp directory via tempfile.mkdtemp() | |
| Output dir | Write directly to ~/Documents/mote/ | |

**User's choice:** ~/.mote/recordings/
**Notes:** Consistent with config path pattern from Phase 1

### Crash/kill behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Leave it, warn on next start | Detect orphaned WAV on next `mote record` and warn user. Let them decide. | ✓ |
| Auto-clean on next start | Silently delete orphaned WAV files | |
| You decide | Claude picks the safest approach | |

**User's choice:** Leave it, warn on next start
**Notes:** None

---

## BlackHole Detection

### Device discovery method

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-detect by name | Search sounddevice.query_devices() for 'BlackHole' in device name | ✓ |
| Config-based device name | User sets exact device name in config.toml | |
| Auto-detect + config override | Auto-detect with config.toml override option | |

**User's choice:** Auto-detect by name
**Notes:** None

### Multiple BlackHole devices

| Option | Description | Selected |
|--------|-------------|----------|
| Prefer BlackHole 2ch | Pick 2ch if found, fall back to others if 2ch absent | ✓ |
| Ask user to choose | List found devices and prompt selection | |
| You decide | Claude picks simplest approach | |

**User's choice:** Prefer BlackHole 2ch
**Notes:** BlackHole 2ch is the recommended install per project constraints

---

## Status Tracking

### Status mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| PID file in ~/.mote/ | Write .pid file on start, remove on clean stop. Standard Unix pattern. | ✓ |
| Lock file with flock | File locking on status file. More robust but more complex. | |
| You decide | Claude picks simplest reliable approach | |

**User's choice:** PID file in ~/.mote/
**Notes:** None

### Concurrency handling

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse with message | If PID alive, refuse. If PID stale, warn and clean up, then allow. | ✓ |
| Always allow | Start regardless, user manages multiple instances | |
| You decide | Claude picks safest approach | |

**User's choice:** Refuse with message
**Notes:** None

---

## Claude's Discretion

- sounddevice stream configuration details
- Rich layout specifics
- WAV file naming convention
- Exact error message wording
- Signal handler implementation

## Deferred Ideas

None — discussion stayed within phase scope
