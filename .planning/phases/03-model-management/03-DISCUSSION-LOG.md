# Phase 3: Model Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 03-model-management
**Areas discussed:** Model storage, Download experience, List display, Error & edge cases

---

## Model Storage

| Option | Description | Selected |
|--------|-------------|----------|
| HuggingFace cache | Let faster-whisper use its default HF cache (~/.cache/huggingface/). Models load by repo ID directly. | :heavy_check_mark: |
| Custom ~/.mote/models/ | Download and manage models in Mote's own directory. Full control over layout. | |
| Configurable path | Default to HF cache but allow overriding via config. | |

**User's choice:** HuggingFace cache
**Notes:** User initially asked about Ollama — clarified that Ollama doesn't support Whisper/audio models; KBLab models are CTranslate2 format for faster-whisper only.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit pre-download | Running 'mote models download medium' downloads immediately with progress bar. | :heavy_check_mark: |
| Lazy download at transcription time | 'mote models download' just validates. Actual download at first transcription. | |

**User's choice:** Explicit pre-download
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Short aliases | 'mote models download medium' — map short names to HF repo IDs internally. | :heavy_check_mark: |
| Full HF repo IDs | 'mote models download KBLab/kb-whisper-medium' — explicit but verbose. | |
| Both accepted | Accept either form. | |

**User's choice:** Short aliases
**Notes:** None

---

## Download Experience

| Option | Description | Selected |
|--------|-------------|----------|
| Show size, start immediately | Print size info then start with progress bar. No confirmation. | |
| Confirm before large downloads | Prompt 'Continue? [Y/n]' for models over a threshold. | :heavy_check_mark: |
| Silent start | Just start downloading, no size info upfront. | |

**User's choice:** Confirm before large downloads
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Rich progress bar | Rich library progress bar with speed, ETA, percentage, file size. | :heavy_check_mark: |
| Simple text updates | Print percentage updates. | |
| You decide | Claude picks. | |

**User's choice:** Rich progress bar
**Notes:** None

---

## List Display

| Option | Description | Selected |
|--------|-------------|----------|
| Name + status + disk size | Show each model with status and disk size. Mark active model from config. | :heavy_check_mark: |
| Minimal: name + status only | Just name and downloaded/not-downloaded. | |
| Rich table with details | Rich-formatted table with name, size, status, recommended use case. | |

**User's choice:** Name + status + disk size
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Show approximate sizes for all | Hardcode approximate sizes for all models. Downloaded show actual. | :heavy_check_mark: |
| Only show size when downloaded | Blank or '?' for not-downloaded models. | |

**User's choice:** Show approximate sizes for all
**Notes:** None

---

## Error & Edge Cases

| Option | Description | Selected |
|--------|-------------|----------|
| Clean up partial files | Delete incomplete download artifacts on Ctrl+C. Next download starts fresh. | :heavy_check_mark: |
| Keep partial for resume | Leave partial files for resume capability. | |
| You decide | Claude picks based on huggingface_hub support. | |

**User's choice:** Clean up partial files
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Warn but allow | Print warning about active model, then delete. | :heavy_check_mark: |
| Block deletion | Refuse to delete active model. | |
| Delete and clear config | Delete model and reset config. | |

**User's choice:** Warn but allow
**Notes:** None

---

| Option | Description | Selected |
|--------|-------------|----------|
| Skip with message | Already-downloaded message with --force hint. | :heavy_check_mark: |
| Re-download silently | Always download, overwriting. | |
| Prompt user | Ask each time. | |

**User's choice:** Skip with message
**Notes:** None

---

## Claude's Discretion

- HF cache detection method (directory inspection vs. huggingface_hub API)
- Rich formatting and table layout for model list
- Error messages for invalid names, network failures, disk space issues

## Deferred Ideas

None — discussion stayed within phase scope
