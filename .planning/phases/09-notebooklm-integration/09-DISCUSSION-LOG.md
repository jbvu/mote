# Phase 9: NotebookLM Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 09-notebooklm-integration
**Areas discussed:** Go/no-go viability, Auth mechanism, Upload scope, Failure & expiry UX

---

## Go/No-Go Viability

| Option | Description | Selected |
|--------|-------------|----------|
| Research first | Have research phase check notebooklm-py GitHub status. If dead, pivot to documentation. | ✓ |
| Build regardless | Implement even if flaky, accept breakage with clear errors. | |
| Skip Phase 9 entirely | Document Drive-as-intermediary workflow, no code. | |

**User's choice:** Research first
**Notes:** Research phase gates the entire phase. If notebooklm-py is dead/unmaintained, phase pivots to documentation instead of code.

---

## Auth Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Cookie extraction | Auto-extract Google session cookies from Chrome's cookie store. | ✓ |
| Manual token paste | User copies session token from DevTools manually. | |
| Reuse Drive OAuth token | Try existing Drive OAuth2 credentials. | |
| You decide | Claude picks based on research. | |

**User's choice:** Cookie extraction
**Notes:** Keeps auth friction low — user just needs to be logged into Google in Chrome.

---

## Upload Scope — Organization

| Option | Description | Selected |
|--------|-------------|----------|
| One notebook, add sources | Single "Mote Transcripts" notebook, each transcript as new source. | ✓ |
| New notebook per meeting | Separate notebook per transcription. | |
| You decide | Claude picks based on API capabilities. | |

**User's choice:** One notebook, add sources
**Notes:** Mirrors the Drive folder approach — simple, consistent.

## Upload Scope — Format

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown only | Upload just .md file. Best for NotebookLM source ingestion. | �� |
| All configured formats | Upload md, txt, json — consistent with Drive but redundant. | |
| You decide | Claude picks based on NotebookLM preferences. | |

**User's choice:** Markdown only
**Notes:** NotebookLM works best with rich text sources; plain text and JSON add no value.

---

## Failure & Expiry UX

| Option | Description | Selected |
|--------|-------------|----------|
| Warning on failure | Same as Drive: attempt silently, show re-auth hint on failure. | ✓ |
| Proactive session check | Test session before each upload, warn before transcription starts. | |
| You decide | Claude picks best UX balance. | |

**User's choice:** Warning on failure
**Notes:** Consistent with Drive pattern. No proactive checks — fail silently with clear re-auth message.

---

## Claude's Discretion

- Cookie extraction mechanism details
- Session credential storage format
- Whether `mote upload` supports NotebookLM target
- Notebook naming configurability

## Deferred Ideas

None — discussion stayed within phase scope
