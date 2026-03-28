# Phase 4: Transcription Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 04-transcription-engine
**Areas discussed:** Auto-transcribe flow, Engine abstraction, Progress & feedback, OpenAI chunking

---

## Auto-Transcribe Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in record command | After WAV is written, record_command() calls transcribe() directly. Single mote record does capture + transcribe. | ✓ |
| Separate mote transcribe command | record only captures audio. User runs mote transcribe separately. | |
| Both — auto + standalone | record auto-transcribes by default, but mote transcribe also exists. | |

**User's choice:** Inline in record command
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add --no-transcribe flag | Gives users an escape hatch for WAV-only capture. | ✓ |
| No, always transcribe | Keep it simple. Recording always leads to transcription. | |

**User's choice:** Yes, add --no-transcribe flag
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Delete after successful transcription | WAV files pile up at ~1.9MB/min. Delete immediately after transcript written. Keep on failure. | ✓ |
| Keep WAV, defer cleanup to Phase 5 | Let Phase 5 handle file lifecycle. | |
| You decide | Claude picks. | |

**User's choice:** Delete after successful transcription
**Notes:** None

---

## Engine Abstraction

| Option | Description | Selected |
|--------|-------------|----------|
| Simple functions | Two functions with a dispatch function. No classes. | |
| Protocol/ABC class | TranscriptionEngine protocol with LocalEngine and OpenAIEngine. | |
| You decide | Claude picks based on codebase patterns. | ✓ |

**User's choice:** You decide
**Notes:** Codebase is function-based throughout (models.py, audio.py, config.py). Claude's discretion.

| Option | Description | Selected |
|--------|-------------|----------|
| --engine flag on record | mote record --engine openai overrides config. Config default is 'local'. | ✓ |
| Separate mote config set only | No per-recording flag. | |
| Both flag and env var | --engine flag plus MOTE_ENGINE env var. | |

**User's choice:** --engine flag on record
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Config default 'sv' + --language flag | Default to Swedish in config. Override with --language en. | ✓ |
| Auto-detect with manual override | Let Whisper auto-detect. Risk of misidentifying Swedish. | |

**User's choice:** Config default 'sv' + --language flag
**Notes:** User initially selected auto-detect, then reconsidered after hearing about CLAUDE.md's warning on Swedish misdetection. Revised to explicit Swedish default.

---

## Progress & Feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Time-based progress bar | Percentage from (last_segment_end / total_duration). Rich progress bar. Spinner for OpenAI. | ✓ |
| Segment counter | Show segment count as they arrive. Simpler but less intuitive. | |
| You decide | Claude picks. | |

**User's choice:** Time-based progress bar
**Notes:** Local: `Transcribing  42%  ████████▓░░░░░░░  02:15/05:22`. OpenAI: `Transcribing via OpenAI...  ⠋`

---

## OpenAI Chunking

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-split silently | Split into ~12 min chunks automatically. User sees chunk counter. | ✓ |
| Warn and split | Warn user about splitting, then proceed. | |
| Refuse long recordings | Tell user to use local engine instead. | |

**User's choice:** Auto-split silently
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed time intervals | Split at ~12 min boundaries. Simple, predictable. | ✓ |
| Silence-based splitting | Detect silence gaps. More complex, over-engineered. | |
| You decide | Claude picks. | |

**User's choice:** Fixed time intervals
**Notes:** None

---

## Claude's Discretion

- Engine abstraction pattern (functions vs classes)
- Internal module API design
- Error handling patterns
- Rich widget specifics for progress

## Deferred Ideas

None — discussion stayed within phase scope
