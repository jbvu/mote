# Phase 5: Output and Transcript Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 05-output-and-transcript-management
**Areas discussed:** Markdown structure, Filename convention, Transcript listing, Write integration
**Mode:** Auto (all areas auto-selected, recommended defaults chosen)

---

## Markdown Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Header + full text | YAML-style metadata header, then continuous transcript | ✓ |
| Per-segment timestamps | Each segment with start/end time markers | |
| Raw text only | No metadata in Markdown | |

**User's choice:** [auto] Header with date/duration/engine, then full transcript text
**Notes:** Per-segment timestamps add complexity without clear value for NotebookLM consumption workflow

---

## Filename Convention

| Option | Description | Selected |
|--------|-------------|----------|
| YYYY-MM-DD_HHMM_{name} | ISO date + time + optional name | ✓ |
| YYYY-MM-DD_{name} | Date only, no time | |
| Sequential numbering | transcript_001, transcript_002 | |

**User's choice:** [auto] `--name` flag on `mote record`, format: `2026-03-28_1430_standup.md`
**Notes:** Matches ROADMAP.md example pattern. HHMM adds uniqueness for multiple recordings per day.

---

## Transcript Listing

| Option | Description | Selected |
|--------|-------------|----------|
| Rich table, last 20 | Table with filename, date, duration, words, engine | ✓ |
| Simple list | Just filenames | |
| Detailed with preview | Include first line of transcript | |

**User's choice:** [auto] Rich table with last 20, `--all` flag for full list
**Notes:** Consistent with `mote models list` Rich table pattern

---

## Write Integration

| Option | Description | Selected |
|--------|-------------|----------|
| New output.py module | Separate module called from record_command | ✓ |
| Inline in cli.py | Write logic directly in record_command | |
| Transcribe module | Add to transcribe.py | |

**User's choice:** [auto] New output.py module — keeps cli.py lean
**Notes:** Follows established pattern of one module per concern

---

## Claude's Discretion

- Internal structure of output.py
- Exact Markdown header format
- Rich table styling for mote list
- Error handling for write failures

## Deferred Ideas

None
