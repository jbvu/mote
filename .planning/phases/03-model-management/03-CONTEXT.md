# Phase 3: Model Management - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

User can manage KB-Whisper models on disk — list available/downloaded models, download a chosen model with progress, and delete models — so local transcription (Phase 4) has a model to use.

Requirements: MOD-01, MOD-02, MOD-03, MOD-04, CLI-02

</domain>

<decisions>
## Implementation Decisions

### Model Storage
- **D-01:** Use HuggingFace cache (`~/.cache/huggingface/hub/`) as the storage location. faster-whisper's built-in HF hub integration handles download and loading by repo ID. No custom model directory.
- **D-02:** Use short aliases for model names in CLI — `tiny`, `base`, `small`, `medium`, `large`. Map internally to HuggingFace repo IDs (`KBLab/kb-whisper-{size}`). Matches existing config format (`model = "kb-whisper-medium"`).

### Download Experience
- **D-03:** Explicit pre-download via `mote models download <name>`. The command downloads the model immediately — no lazy download at transcription time.
- **D-04:** Show size confirmation prompt before starting downloads. E.g., "kb-whisper-medium is 1.5 GB. Continue? [Y/n]"
- **D-05:** Use Rich progress bar during download — with download speed, ETA, percentage, and file size. Consistent with Rich usage elsewhere in the project.

### List Display
- **D-06:** `mote models list` shows: model name, size, downloaded status. Mark the active model from config. Format:
  ```
  tiny      ~75 MB     not downloaded
  medium    ~1.5 GB    downloaded (active)
  large     ~3.0 GB    not downloaded
  ```
- **D-07:** Show approximate expected sizes for all models (hardcoded). Downloaded models show actual disk size.

### Error & Edge Cases
- **D-08:** Ctrl+C during download cleans up partial files. No resume support — next download starts fresh.
- **D-09:** Deleting the active model (the one set in config) is allowed but prints a warning: "Note: medium is your active model. Local transcription will fail until you download a model."
- **D-10:** Re-downloading an already-downloaded model skips with message: "kb-whisper-medium is already downloaded (1.5 GB). Use --force to re-download."

### Claude's Discretion
- How to detect whether a model is downloaded in the HF cache (inspect cache directory structure vs. use huggingface_hub API)
- Exact Rich formatting and table layout for `mote models list`
- Error messages for invalid model names, network failures, disk space issues

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Stack
- `CLAUDE.md` — Technology stack section defines faster-whisper 1.2.1, KBLab model details, huggingface_hub patterns
- `.planning/REQUIREMENTS.md` — MOD-01 through MOD-04 acceptance criteria, CLI-02

### Existing Code
- `src/mote/models.py` — Empty stub, target module for model management logic
- `src/mote/config.py` — Config defaults (`transcription.model = "kb-whisper-medium"`, `transcription.engine = "local"`)
- `src/mote/cli.py` — CLI structure with Click groups, pattern to follow for `@cli.group()` models subcommand

### External
- https://huggingface.co/KBLab/kb-whisper-large — KBLab model repo, ctranslate2 format, 5 sizes
- https://github.com/SYSTRAN/faster-whisper — faster-whisper API for WhisperModel loading

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mote/config.py`: `load_config()`, `get_config_dir()`, `ensure_config()` — for reading active model from config
- `src/mote/cli.py`: Click group pattern (`@cli.group()` + `@group.command()`) — reuse for `mote models` subcommand group
- Rich library already in project dependencies — available for progress bars and tables

### Established Patterns
- Click CLI with `@cli.group()` for command groups, `@click.argument()` for positional args
- Config values accessed via `load_config()` returning a tomlkit document
- Error handling via `click.ClickException` for user-facing errors

### Integration Points
- `cli.py` — Add `@cli.group() def models()` with `list`, `download`, `delete` subcommands
- `models.py` — Implement model management logic (currently empty stub)
- `config.py` — Read `transcription.model` to determine active model for list display

</code_context>

<specifics>
## Specific Ideas

- User asked about Ollama — not applicable since KBLab models are CTranslate2 format for faster-whisper, not GGUF/Ollama-compatible. This is a faster-whisper + HuggingFace Hub workflow only.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-model-management*
*Context gathered: 2026-03-28*
