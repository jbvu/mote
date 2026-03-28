# Phase 3: Model Management - Research

**Researched:** 2026-03-28
**Domain:** HuggingFace Hub cache API, faster-whisper model loading, KBLab KB-Whisper models
**Confidence:** HIGH — all findings verified against live library code in the project venv

## Summary

Phase 3 implements model management (list, download, delete) using `huggingface_hub` APIs that are already present as transitive dependencies of `faster-whisper`. No new top-level dependencies are needed. The `huggingface_hub` library (version 1.8.0 in the venv) provides `scan_cache_dir()`, `snapshot_download()`, and `HFCacheInfo.delete_revisions()` which cover all three operations cleanly.

`faster-whisper`'s `WhisperModel` calls `download_model()` internally, which delegates to `snapshot_download()` with a fixed `allow_patterns` list (`model.bin`, `config.json`, `preprocessor_config.json`, `tokenizer.json`, `vocabulary.*`). This means the HF cache is the single source of truth — our `mote models download` command must mirror those same `allow_patterns` so the downloaded files are immediately usable by `WhisperModel` without re-downloading.

The `tqdm.rich` adapter is available in the venv (via `tqdm` 4.67.3 which ships `tqdm.rich`), and `snapshot_download()` accepts a `tqdm_class` parameter. Passing `tqdm.rich.tqdm` as `tqdm_class` gives a Rich-styled download progress bar with no additional wiring beyond what's already installed.

**Primary recommendation:** Implement `models.py` using `snapshot_download()` with `tqdm_class=tqdm.rich.tqdm` for downloads, `scan_cache_dir()` for list/size/delete, and `try_to_load_from_cache()` as the fast check for MOD-04 guard.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use HuggingFace cache (`~/.cache/huggingface/hub/`) as the storage location. faster-whisper's built-in HF hub integration handles download and loading by repo ID. No custom model directory.
- **D-02:** Use short aliases for model names in CLI — `tiny`, `base`, `small`, `medium`, `large`. Map internally to HuggingFace repo IDs (`KBLab/kb-whisper-{size}`). Matches existing config format (`model = "kb-whisper-medium"`).
- **D-03:** Explicit pre-download via `mote models download <name>`. The command downloads the model immediately — no lazy download at transcription time.
- **D-04:** Show size confirmation prompt before starting downloads. E.g., "kb-whisper-medium is 1.5 GB. Continue? [Y/n]"
- **D-05:** Use Rich progress bar during download — with download speed, ETA, percentage, and file size. Consistent with Rich usage elsewhere in the project.
- **D-06:** `mote models list` shows: model name, size, downloaded status. Mark the active model from config.
- **D-07:** Show approximate expected sizes for all models (hardcoded). Downloaded models show actual disk size.
- **D-08:** Ctrl+C during download cleans up partial files. No resume support — next download starts fresh.
- **D-09:** Deleting the active model (the one set in config) is allowed but prints a warning.
- **D-10:** Re-downloading an already-downloaded model skips with message unless --force.

### Claude's Discretion

- How to detect whether a model is downloaded in the HF cache (inspect cache directory structure vs. use huggingface_hub API)
- Exact Rich formatting and table layout for `mote models list`
- Error messages for invalid model names, network failures, disk space issues

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOD-01 | User can list available and downloaded models | `scan_cache_dir()` provides per-repo download status and size; `try_to_load_from_cache()` for fast per-model check |
| MOD-02 | User can download a specific KB-Whisper model with progress display | `snapshot_download()` with `tqdm_class=tqdm.rich.tqdm` and same `allow_patterns` as faster-whisper |
| MOD-03 | User can delete a downloaded model | `scan_cache_dir()` → `HFCacheInfo.delete_revisions(*hashes).execute()` |
| MOD-04 | Tool refuses to transcribe locally if no model is downloaded and shows clear instructions | `try_to_load_from_cache('KBLab/kb-whisper-{size}', 'model.bin')` returns `None` when not cached |
| CLI-02 | `mote models list/download/delete` manages transcription models | Click `@cli.group() def models()` with three subcommands, following existing pattern in `cli.py` |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies — all already installed)

| Library | Version in venv | Purpose | Status |
|---------|----------------|---------|--------|
| huggingface_hub | 1.8.0 | Cache scan, download, delete | Transitive dep of faster-whisper — already present |
| tqdm | 4.67.3 | Progress bar via `tqdm.rich` adapter | Transitive dep of huggingface_hub — already present |
| rich | 14.3.3 | Table formatting for `models list` | Already a direct project dependency |
| faster-whisper | 1.2.1 | Declares `huggingface-hub>=0.21` requirement | Direct project dependency |

**No new entries needed in pyproject.toml.** All required libraries are reachable through the existing dependency tree.

### Key imports

```python
from huggingface_hub import scan_cache_dir, snapshot_download, try_to_load_from_cache
from huggingface_hub.errors import CacheNotFound
from huggingface_hub.file_download import repo_folder_name
from tqdm.rich import tqdm as rich_tqdm
from rich.console import Console
from rich.table import Table
```

---

## KBLab Model Data

### Exact repo IDs

| Alias (CLI) | Config value | HuggingFace repo ID |
|-------------|-------------|---------------------|
| tiny | kb-whisper-tiny | `KBLab/kb-whisper-tiny` |
| base | kb-whisper-base | `KBLab/kb-whisper-base` |
| small | kb-whisper-small | `KBLab/kb-whisper-small` |
| medium | kb-whisper-medium | `KBLab/kb-whisper-medium` |
| large | kb-whisper-large | `KBLab/kb-whisper-large` |

### Verified download sizes (faster-whisper files only)

Sizes are for the 5 files faster-whisper actually downloads (`model.bin`, `config.json`, `preprocessor_config.json`, `tokenizer.json`, `vocabulary.*`). The HF repo contains many other formats (ggml, onnx, safetensors) that are NOT downloaded. Verified 2026-03-28 via `HfApi.model_info(files_metadata=True)`.

| Alias | Download size | model.bin | Notes |
|-------|--------------|-----------|-------|
| tiny  | ~77 MB | 72 MB | Fast, lower accuracy |
| base  | ~143 MB | 139 MB | Good speed/quality for quick tasks |
| small | ~466 MB | 461 MB | Balanced |
| medium | ~1.46 GB | 1.46 GB | Recommended default |
| large | ~2.88 GB | 2.94 GB | Best Swedish accuracy |

These are the values to hardcode in `models.py` for D-07 (approximate expected sizes).

### Stage 2 variants

No Stage 2 variants exist on HuggingFace as of 2026-03-28. KBLab publishes exactly 5 repos: `KBLab/kb-whisper-{tiny,base,small,medium,large}`. The only other KBLab whisper repos are `whisper-tiny-rixvox` and `whisper-small-rixvox` (different training set, out of scope). No "v2" or "stage2" suffixes exist.

---

## Architecture Patterns

### Recommended file structure

```
src/mote/
├── models.py        # Model management logic (currently empty stub)
└── cli.py           # Add @cli.group() models + 3 subcommands
tests/
└── test_models.py   # New test file for model management
```

### Pattern 1: Alias and repo ID mapping

```python
# Source: verified against existing config.py default ("kb-whisper-medium")
MODELS = {
    "tiny":   "KBLab/kb-whisper-tiny",
    "base":   "KBLab/kb-whisper-base",
    "small":  "KBLab/kb-whisper-small",
    "medium": "KBLab/kb-whisper-medium",
    "large":  "KBLab/kb-whisper-large",
}

# Approximate sizes in bytes (hardcoded per D-07)
# Verified 2026-03-28 via HfApi.model_info(files_metadata=True)
APPROX_SIZES = {
    "tiny":   77 * 1024 * 1024,
    "base":   143 * 1024 * 1024,
    "small":  466 * 1024 * 1024,
    "medium": 1462 * 1024 * 1024,
    "large":  2949 * 1024 * 1024,
}

# Config -> alias mapping (config stores "kb-whisper-medium", CLI uses "medium")
def config_value_to_alias(config_model: str) -> str | None:
    """Convert config value 'kb-whisper-medium' -> alias 'medium'."""
    for alias in MODELS:
        if config_model == f"kb-whisper-{alias}":
            return alias
    return None
```

### Pattern 2: Check if model is downloaded

Two approaches verified — use `try_to_load_from_cache` for a fast single-file check:

```python
# Source: verified in venv via try_to_load_from_cache('KBLab/kb-whisper-medium', 'model.bin')
from huggingface_hub import try_to_load_from_cache

def is_model_downloaded(alias: str) -> bool:
    """Return True if the model's model.bin is present in the HF cache."""
    repo_id = MODELS[alias]
    result = try_to_load_from_cache(repo_id, "model.bin")
    # Returns None when not cached, a path string when cached
    return result is not None
```

For `mote models list` (which also needs disk size), use `scan_cache_dir()` instead:

```python
from huggingface_hub import scan_cache_dir
from huggingface_hub.errors import CacheNotFound

def get_downloaded_models() -> dict[str, int]:
    """Return {alias: size_bytes} for all downloaded KB-Whisper models."""
    try:
        cache = scan_cache_dir()
    except CacheNotFound:
        return {}
    result = {}
    for repo in cache.repos:
        if repo.repo_type != "model":
            continue
        for alias, repo_id in MODELS.items():
            if repo.repo_id == repo_id:
                result[alias] = repo.size_on_disk
    return result
```

### Pattern 3: Download with Rich progress bar

```python
# Source: verified - snapshot_download accepts tqdm_class; tqdm.rich.tqdm is a proper subclass
from huggingface_hub import snapshot_download
from tqdm.rich import tqdm as rich_tqdm

ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]

def download_model(alias: str) -> None:
    """Download a KB-Whisper model to the HF cache with Rich progress."""
    repo_id = MODELS[alias]
    snapshot_download(
        repo_id,
        allow_patterns=ALLOW_PATTERNS,
        tqdm_class=rich_tqdm,
    )
```

**Important:** Use the same `allow_patterns` as `faster_whisper.utils.download_model` uses. If these diverge, `WhisperModel` may silently re-download missing files on first transcription.

### Pattern 4: Delete a cached model

```python
# Source: verified - HFCacheInfo.delete_revisions(*hashes).execute() is the API-safe path
from huggingface_hub import scan_cache_dir
from huggingface_hub.errors import CacheNotFound

def delete_model(alias: str) -> int:
    """Delete all cached revisions of a model. Returns bytes freed (0 if not cached)."""
    repo_id = MODELS[alias]
    try:
        cache = scan_cache_dir()
    except CacheNotFound:
        return 0
    for repo in cache.repos:
        if repo.repo_id == repo_id and repo.repo_type == "model":
            hashes = [rev.commit_hash for rev in repo.revisions]
            strategy = cache.delete_revisions(*hashes)
            freed = strategy.expected_freed_size
            strategy.execute()
            return freed
    return 0
```

### Pattern 5: Ctrl+C cleanup (D-08)

HuggingFace Hub downloads incomplete files to `{cache_dir}/models--KBLab--kb-whisper-{size}/blobs/{hash}.incomplete`. When `snapshot_download` is interrupted by `KeyboardInterrupt`, these `.incomplete` files remain on disk. The library does support resuming from them on a subsequent download — but D-08 says no resume: start fresh.

```python
import shutil
from huggingface_hub.file_download import repo_folder_name
from pathlib import Path
import huggingface_hub

def cleanup_partial_download(alias: str) -> None:
    """Remove the entire model cache dir to clean up a partial download."""
    repo_id = MODELS[alias]
    cache_dir = Path(huggingface_hub.constants.HF_HUB_CACHE)
    folder = repo_folder_name(repo_id=repo_id, repo_type="model")
    model_dir = cache_dir / folder
    if model_dir.exists():
        shutil.rmtree(model_dir)
```

Wrap the download in a try/except and call `cleanup_partial_download` from the except clause:

```python
try:
    download_model(alias)
except KeyboardInterrupt:
    click.echo("\nDownload cancelled.")
    cleanup_partial_download(alias)
    click.echo("Partial files cleaned up.")
    raise SystemExit(1)
```

**Alternative for D-10 re-download with --force:** Pass `force_download=True` to `snapshot_download`. This removes the `.incomplete` file before starting, ensuring a clean restart.

### Pattern 6: MOD-04 guard (refuse transcription if no model)

```python
# In the transcription code (Phase 4), call this guard before loading WhisperModel
def require_model_downloaded(alias: str) -> None:
    """Raise ClickException if the model is not in the HF cache."""
    if not is_model_downloaded(alias):
        raise click.ClickException(
            f"Model '{alias}' is not downloaded.\n"
            f"Run: mote models download {alias}"
        )
```

### Pattern 7: CLI command group structure

Follow the existing `@cli.group()` pattern from `cli.py`:

```python
@cli.group()
def models():
    """Manage KB-Whisper transcription models."""
    pass

@models.command("list")
def models_list():
    ...

@models.command("download")
@click.argument("name")
@click.option("--force", is_flag=True, help="Re-download even if already present.")
def models_download(name, force):
    ...

@models.command("delete")
@click.argument("name")
def models_delete(name):
    ...
```

### Anti-Patterns to Avoid

- **Calling `WhisperModel(repo_id)` to check if downloaded:** This loads the model into RAM (several GB). Use `try_to_load_from_cache()` instead.
- **Using `shutil.rmtree` for delete without scan_cache_dir:** Direct filesystem deletion works but bypasses the lock/blob deduplication logic. Use `delete_revisions().execute()` so HF's internal consistency is maintained.
- **Checking only for `model.bin` in snapshots directory:** The snapshots directory contains symlinks to blobs. Checking the blob itself via `try_to_load_from_cache` is more reliable.
- **Different `allow_patterns` than faster-whisper:** If you download with `allow_patterns=None` (all files), you get 10+ GB of onnx/ggml files. Always use the same allow_patterns as `faster_whisper.utils.download_model`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Download progress display | Custom HTTP download with progress tracking | `snapshot_download(tqdm_class=rich_tqdm)` | HF handles chunked download, retries, auth, parallel files, ETA |
| Cache directory inspection | Custom glob of `~/.cache/huggingface/hub/` | `scan_cache_dir()` | Returns structured dataclasses with sizes, revision hashes, file lists |
| Model deletion | `shutil.rmtree` on model folder | `delete_revisions().execute()` | Handles blob deduplication — shared blobs between revisions aren't double-deleted |
| Cache path computation | Hardcoded `~/.cache/huggingface/hub/` | `huggingface_hub.constants.HF_HUB_CACHE` | Respects `HF_HUB_CACHE` env var, XDG conventions |
| Checking if model exists | Custom directory walk | `try_to_load_from_cache(repo_id, 'model.bin')` | Handles revision pinning, symlink resolution |

**Key insight:** `huggingface_hub` is a mature cache management library specifically designed for this problem. The only custom logic needed is the alias mapping, the `allow_patterns` mirror, and the Ctrl+C cleanup handler.

---

## Common Pitfalls

### Pitfall 1: Downloading all files instead of just model files

**What goes wrong:** Calling `snapshot_download('KBLab/kb-whisper-medium')` without `allow_patterns` downloads 10+ GB of onnx, ggml, safetensors, and other format files that faster-whisper doesn't use.

**Why it happens:** The HF repo contains model files for every framework. Without filtering, all files are downloaded.

**How to avoid:** Always pass `allow_patterns = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]` — the exact same list that `faster_whisper.utils.download_model` uses. Verified in source: `faster_whisper/utils.py` line defining `allow_patterns`.

**Warning signs:** Download size much larger than expected (e.g., 12 GB for medium instead of 1.5 GB).

### Pitfall 2: CacheNotFound exception when cache dir doesn't exist

**What goes wrong:** `scan_cache_dir()` raises `huggingface_hub.errors.CacheNotFound` when `~/.cache/huggingface/hub/` has never been created (i.e., no model has ever been downloaded on this machine).

**Why it happens:** The library requires the directory to exist before it can scan it.

**How to avoid:** Always wrap `scan_cache_dir()` calls in a `try/except CacheNotFound` block and return an empty result. Verified: `try_to_load_from_cache()` does NOT raise this error — it returns `None` safely.

**Warning signs:** `AttributeError` or `CacheNotFound` on first run on a fresh machine.

### Pitfall 3: HF cache resumes downloads by default

**What goes wrong:** If you cancel a download and restart without cleanup, HuggingFace resumes from `.incomplete` files. D-08 mandates no resume — start fresh.

**Why it happens:** `huggingface_hub` saves partial blobs as `{hash}.incomplete` and resumes them on the next call unless `force_download=True` clears them.

**How to avoid:** Catch `KeyboardInterrupt` during download, then call `cleanup_partial_download()` which uses `shutil.rmtree` on the model's cache directory. For `--force` re-download, pass `force_download=True` to `snapshot_download`.

**Warning signs:** `mote models download medium` after a cancelled download completes faster than expected (resume happened silently).

### Pitfall 4: Config model value vs CLI alias mismatch

**What goes wrong:** Config stores `transcription.model = "kb-whisper-medium"` but the CLI uses alias `"medium"`. Code that passes the config value directly to `MODELS[config_model]` will raise a `KeyError`.

**Why it happens:** Two naming conventions exist: the config format (`kb-whisper-{size}`) predates the CLI alias design.

**How to avoid:** Implement `config_value_to_alias()` that strips the `kb-whisper-` prefix. Use this whenever reading the active model from config for comparison in `models list`.

### Pitfall 5: delete_revisions needs ALL revision hashes, not just "main"

**What goes wrong:** A model repo may have multiple cached revisions (e.g., both `main` and a specific commit). Passing only one hash leaves orphaned blobs.

**Why it happens:** `delete_revisions` is revision-level, not repo-level. Blobs shared between revisions are only deleted when all referencing revisions are removed.

**How to avoid:** Collect all revision hashes: `hashes = [rev.commit_hash for rev in repo.revisions]` and pass all to `delete_revisions(*hashes)`.

---

## Code Examples

### Complete is_model_downloaded pattern

```python
# Source: verified in venv - try_to_load_from_cache returns None when not cached
from huggingface_hub import try_to_load_from_cache

def is_model_downloaded(alias: str) -> bool:
    repo_id = MODELS[alias]
    result = try_to_load_from_cache(repo_id, "model.bin")
    return result is not None
```

### Complete download with Rich progress and Ctrl+C cleanup

```python
import click
import shutil
from pathlib import Path
import huggingface_hub
from huggingface_hub import snapshot_download
from huggingface_hub.file_download import repo_folder_name
from tqdm.rich import tqdm as rich_tqdm

ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]

def download_model(alias: str, force: bool = False) -> None:
    repo_id = MODELS[alias]
    try:
        snapshot_download(
            repo_id,
            allow_patterns=ALLOW_PATTERNS,
            tqdm_class=rich_tqdm,
            force_download=force,
        )
    except KeyboardInterrupt:
        click.echo("\nDownload cancelled.")
        cache_dir = Path(huggingface_hub.constants.HF_HUB_CACHE)
        folder = repo_folder_name(repo_id=repo_id, repo_type="model")
        model_dir = cache_dir / folder
        if model_dir.exists():
            shutil.rmtree(model_dir)
            click.echo("Partial files cleaned up.")
        raise SystemExit(1)
```

### Complete delete pattern

```python
from huggingface_hub import scan_cache_dir
from huggingface_hub.errors import CacheNotFound

def delete_model(alias: str) -> int:
    """Delete all cached revisions. Returns bytes freed."""
    repo_id = MODELS[alias]
    try:
        cache = scan_cache_dir()
    except CacheNotFound:
        return 0
    for repo in cache.repos:
        if repo.repo_id == repo_id and repo.repo_type == "model":
            hashes = [rev.commit_hash for rev in repo.revisions]
            strategy = cache.delete_revisions(*hashes)
            freed = strategy.expected_freed_size
            strategy.execute()
            return freed
    return 0
```

### Complete models list data assembly

```python
def get_models_status(active_config_value: str) -> list[dict]:
    """Return list of model info dicts for display in `mote models list`."""
    active_alias = config_value_to_alias(active_config_value)
    downloaded = get_downloaded_models()  # {alias: actual_size_bytes}

    rows = []
    for alias in MODELS:
        downloaded_size = downloaded.get(alias)
        rows.append({
            "alias": alias,
            "approx_size": APPROX_SIZES[alias],
            "downloaded": downloaded_size is not None,
            "actual_size": downloaded_size,
            "active": alias == active_alias,
        })
    return rows
```

---

## HuggingFace Cache Directory Structure

Understanding this structure is required for the Ctrl+C cleanup and the `is_model_downloaded` check:

```
~/.cache/huggingface/hub/
└── models--KBLab--kb-whisper-medium/
    ├── blobs/
    │   ├── {sha256}            <- completed blob (model.bin content)
    │   ├── {sha256}.incomplete <- partial blob (Ctrl+C cleanup target)
    │   └── ...
    ├── refs/
    │   └── main               <- file containing the commit hash
    └── snapshots/
        └── {commit_hash}/
            ├── model.bin -> ../../blobs/{sha256}
            ├── config.json -> ../../blobs/{sha256}
            ├── tokenizer.json -> ../../blobs/{sha256}
            └── vocabulary.json -> ../../blobs/{sha256}
```

The cache folder name is deterministic: `models--{owner}--{model_name}`. Computed via `repo_folder_name(repo_id='KBLab/kb-whisper-medium', repo_type='model')` which returns `models--KBLab--kb-whisper-medium`.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| `hf_hub_download()` per file | `snapshot_download()` with allow_patterns | snapshot_download parallelizes with thread_map (8 workers) |
| Custom model directory | HF Hub cache (`~/.cache/huggingface/hub/`) | faster-whisper loads directly from HF cache by repo ID |
| `huggingface_hub.hf_hub_url()` + `requests` | `snapshot_download()` | snapshot_download handles auth, retries, partial resume |

**Available but not used here:**
- `HfApi.model_info(files_metadata=True)`: Fetches live metadata from HF API. Useful for displaying "latest available" sizes. Not needed here since sizes are hardcoded (D-07).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| huggingface_hub | scan_cache_dir, snapshot_download | ✓ | 1.8.0 | — (transitive dep of faster-whisper) |
| tqdm.rich | snapshot_download tqdm_class | ✓ | 4.67.3 | Plain tqdm (but Rich style preferred per D-05) |
| rich | Table display for models list | ✓ | 14.3.3 | — (direct project dep) |
| Internet connectivity | mote models download | Assumed present | — | Error message if download fails |
| HF cache dir | scan_cache_dir | Created on first download | — | CacheNotFound handled gracefully |

No missing dependencies. All required libraries are already installed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_models.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOD-01 | `models list` shows all 5 models with correct status | unit (mock scan_cache_dir) | `pytest tests/test_models.py::test_models_list_empty -x` | ❌ Wave 0 |
| MOD-01 | `models list` marks downloaded models and active model | unit (mock scan_cache_dir) | `pytest tests/test_models.py::test_models_list_with_downloaded -x` | ❌ Wave 0 |
| MOD-02 | `models download` calls snapshot_download with correct args | unit (mock snapshot_download) | `pytest tests/test_models.py::test_download_calls_snapshot -x` | ❌ Wave 0 |
| MOD-02 | `models download` already-downloaded skips without --force | unit (mock is_model_downloaded) | `pytest tests/test_models.py::test_download_skips_existing -x` | ❌ Wave 0 |
| MOD-02 | `models download` invalid name exits non-zero with error | unit | `pytest tests/test_models.py::test_download_invalid_name -x` | ❌ Wave 0 |
| MOD-02 | Ctrl+C during download cleans up partial files | unit (mock shutil.rmtree) | `pytest tests/test_models.py::test_download_ctrl_c_cleanup -x` | ❌ Wave 0 |
| MOD-03 | `models delete` calls delete_revisions for correct repo | unit (mock scan_cache_dir) | `pytest tests/test_models.py::test_delete_model -x` | ❌ Wave 0 |
| MOD-03 | `models delete` warns when deleting active model | unit | `pytest tests/test_models.py::test_delete_active_model_warning -x` | ❌ Wave 0 |
| MOD-04 | `require_model_downloaded` raises ClickException when not cached | unit (mock try_to_load_from_cache) | `pytest tests/test_models.py::test_require_model_downloaded_missing -x` | ❌ Wave 0 |
| CLI-02 | `mote models --help` exits 0 | smoke | `pytest tests/test_cli.py::test_models_group_help -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_models.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_models.py` — all model management unit tests (covers MOD-01 through MOD-04, CLI-02)
- [ ] `tests/conftest.py` already exists with `mote_home` fixture — reuse it; add `hf_cache_dir` fixture for isolated HF cache in tests

---

## Open Questions

1. **`tqdm.rich` thread-safety with snapshot_download's thread_map**
   - What we know: `snapshot_download` uses `tqdm.contrib.concurrent.thread_map` with 8 workers. Each worker creates an `_AggregatedTqdm` that updates a shared `bytes_progress` bar. `tqdm.rich.tqdm` is passed as the `tqdm_class` for the outer bytes bar.
   - What's unclear: Whether `tqdm.rich` rendering is safe from multiple threads updating it via `_AggregatedTqdm`. In practice the `_AggregatedTqdm` is not rendered (it's a fake class), so only one Rich bar renders.
   - Recommendation: Test with an actual small download (e.g., `tiny` model at 77 MB) before finalizing. If Rich output is garbled, fall back to plain `tqdm.auto.tqdm` (the default) for the progress bar and use Rich only for the table display in `models list`.

2. **Config value format: `kb-whisper-medium` vs `medium`**
   - What we know: Config default is `transcription.model = "kb-whisper-medium"`. CLI uses `"medium"` alias. `set_config_value` in `config.py` does not validate against known model names.
   - What's unclear: Should `mote models download medium` also update the config? (No — D-03 says download is storage only; config management is out of scope for Phase 3.)
   - Recommendation: Implement `config_value_to_alias()` and document the two conventions clearly in `models.py`. Phase 4 transcription code will need the same helper.

---

## Project Constraints (from CLAUDE.md)

Directives from `CLAUDE.md` that constrain this phase:

- **Python 3.11+** — use `match`/`case` and `tomllib` if needed; no compatibility shims for older Python
- **faster-whisper 1.2.1** — load KBLab models via `WhisperModel("KBLab/kb-whisper-{size}")` in Phase 4; Phase 3 downloads must be compatible with this loading pattern
- **No custom model directory (D-01)** — use HF Hub cache only; `WhisperModel` `download_root` parameter should NOT be used
- **Rich for CLI output** — use `rich.table.Table` for `models list`, consistent with project style
- **Click for CLI** — use `click.ClickException` for user-facing errors; `click.confirm()` for the size confirmation prompt (D-04)
- **No threading for downloads** — `snapshot_download` already uses its own thread pool internally; no additional threading needed
- **Security**: no new network endpoints; `snapshot_download` connects only to `huggingface.co`

---

## Sources

### Primary (HIGH confidence)
- Live source inspection via `inspect.getsource()` in project venv — `faster_whisper/utils.py:download_model`, `huggingface_hub/_snapshot_download.py`, `huggingface_hub/utils/_cache_manager.py`
- `HfApi.model_info(files_metadata=True)` — KBLab model file sizes, verified 2026-03-28
- `huggingface_hub.list_models(author='KBLab', search='kb-whisper')` — confirmed 5 repo IDs, no Stage 2 variants

### Secondary (MEDIUM confidence)
- `huggingface_hub` 1.8.0 changelog and API — `tqdm_class` parameter in `snapshot_download`, `CacheNotFound` exception class, `try_to_load_from_cache` behavior

### Tertiary (LOW confidence — not needed, skipped)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified in venv, no new deps required
- KBLab model sizes: HIGH — fetched live from HF API
- Architecture patterns: HIGH — verified against library source code
- Pitfalls: HIGH — found by reading actual implementation in venv
- tqdm.rich thread-safety: MEDIUM — code inspection suggests it's safe, marked as open question

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (HuggingFace hub API is stable; model sizes may change if KBLab updates repos)
