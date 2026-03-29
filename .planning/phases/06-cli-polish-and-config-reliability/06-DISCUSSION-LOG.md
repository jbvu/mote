# Phase 6: CLI Polish and Config Reliability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 06-cli-polish-and-config-reliability
**Areas discussed:** Retry & recovery UX, Config validation, JSON output structure, Transcribe command UX

---

## Retry & Recovery UX

### Retry after failure

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive prompt | After failure, ask "Retry transcription? [Y/n]" — retranscribes immediately | ✓ |
| Separate retry command | `mote retry` finds last failed WAV and retranscribes | |
| Both prompt + command | Interactive prompt after failure AND a `mote retry` command | |

**User's choice:** Interactive prompt
**Notes:** Simple, matches single-user CLI nature.

### Orphaned WAV handling

| Option | Description | Selected |
|--------|-------------|----------|
| Offer each for transcription | List orphans, ask "Transcribe these?" before recording | |
| Per-file skip option | Let user pick which orphans to transcribe, skip, or delete | |
| Warn + point to transcribe command | Keep warning, add "Run `mote transcribe <file>`" | ✓ |

**User's choice:** Just warn, point to transcribe command
**Notes:** Non-blocking — don't slow down record startup.

---

## Config Validation

### What to validate

| Option | Description | Selected |
|--------|-------------|----------|
| Engine name | Reject unknown engine values | ✓ |
| Model availability | Check configured model is downloaded (if engine=local) | ✓ |
| Output dir writability | Check output.dir exists or can be created | ✓ |
| API key presence | Warn if engine=openai but no API key configured | ✓ |

**User's choice:** All four checks
**Notes:** Comprehensive validation to catch issues before wasting meeting time.

### When to validate

| Option | Description | Selected |
|--------|-------------|----------|
| Before record & transcribe only | Validate only when it matters | ✓ |
| On every command | Validate on all CLI commands | |
| Explicit `mote config validate` | Dedicated validate command only | ✓ |

**User's choice:** Both — automatic before record/transcribe AND a manual `mote config validate` command
**Notes:** User initially selected automatic-only, then clarified they want both options.

---

## JSON Output Structure

### JSON structure

| Option | Description | Selected |
|--------|-------------|----------|
| Flat metadata + text | Mirror YAML frontmatter fields plus "transcript" field | ✓ |
| Metadata + segments array | Same fields plus per-segment text with timestamps | |
| You decide | Claude picks based on downstream consumption needs | |

**User's choice:** Flat metadata + text
**Notes:** Simple, consistent with .md structure.

### JSON default behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Opt-in via flag only | `--output-format json` or add to config | |
| Add to default config | New installs get json by default | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** None.

---

## Transcribe Command UX

### File handling

| Option | Description | Selected |
|--------|-------------|----------|
| Single file only | `mote transcribe <file>` accepts one WAV at a time | ✓ |
| Multiple files | Accept multiple WAV arguments | |
| Single file + glob | Expand glob patterns | |

**User's choice:** Single file only
**Notes:** Simple, clear error handling, matches single-meeting workflow.

### Existing output handling

| Option | Description | Selected |
|--------|-------------|----------|
| Overwrite silently | Just write the new transcript | |
| Warn and ask | "Output file already exists. Overwrite? [Y/n]" | ✓ |
| Append suffix | Add _2, _3 to avoid conflicts | |

**User's choice:** Warn and ask
**Notes:** User preferred the safer option over silent overwrite.

### WAV cleanup after transcribe

| Option | Description | Selected |
|--------|-------------|----------|
| Keep WAV | Don't delete user's input file | |
| Delete WAV after success | Match `mote record` behavior | |
| Ask the user | Prompt after each transcription | |

**User's choice:** WAV retention with time-based cleanup (custom response)
**Notes:** User raised disk space concerns. Decided on `cleanup.wav_retention_days` config (default 7 days). Auto-cleanup on `mote record` startup plus manual `mote cleanup` command.

---

## Claude's Discretion

- Whether JSON output is opt-in only or added to default config for new installs

## Deferred Ideas

None — discussion stayed within phase scope
