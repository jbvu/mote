"""KB-Whisper model management."""

import shutil
from pathlib import Path

import click
import huggingface_hub
from huggingface_hub import scan_cache_dir, snapshot_download, try_to_load_from_cache
from huggingface_hub.errors import CacheNotFound
from huggingface_hub.file_download import repo_folder_name
from tqdm.rich import tqdm as rich_tqdm


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODELS: dict[str, str] = {
    "tiny": "KBLab/kb-whisper-tiny",
    "base": "KBLab/kb-whisper-base",
    "small": "KBLab/kb-whisper-small",
    "medium": "KBLab/kb-whisper-medium",
    "large": "KBLab/kb-whisper-large",
}

# Approximate download sizes in bytes (faster-whisper files only, verified 2026-03-28)
APPROX_SIZES: dict[str, int] = {
    "tiny": 77 * 1024 * 1024,
    "base": 143 * 1024 * 1024,
    "small": 466 * 1024 * 1024,
    "medium": 1462 * 1024 * 1024,
    "large": 2949 * 1024 * 1024,
}

# Mirror of faster-whisper's allow_patterns — must match exactly so downloaded
# files are immediately usable by WhisperModel without re-downloading.
ALLOW_PATTERNS: list[str] = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]


# ---------------------------------------------------------------------------
# Alias helpers
# ---------------------------------------------------------------------------


def config_value_to_alias(config_model: str) -> str | None:
    """Convert config value 'kb-whisper-medium' to CLI alias 'medium'.

    Returns None for unknown values.
    """
    for alias in MODELS:
        if config_model == f"kb-whisper-{alias}":
            return alias
    return None


# ---------------------------------------------------------------------------
# Cache inspection
# ---------------------------------------------------------------------------


def is_model_downloaded(alias: str) -> bool:
    """Return True if the model's model.bin is present in the HF cache.

    Uses try_to_load_from_cache for a fast single-file check — does NOT
    load the model into RAM.
    """
    repo_id = MODELS[alias]
    result = try_to_load_from_cache(repo_id, "model.bin")
    return result is not None


def get_downloaded_models() -> dict[str, int]:
    """Return {alias: size_bytes} for all downloaded KB-Whisper models.

    Returns {} when the HF cache directory has never been created.
    """
    try:
        cache = scan_cache_dir()
    except CacheNotFound:
        return {}

    result: dict[str, int] = {}
    for repo in cache.repos:
        if repo.repo_type != "model":
            continue
        for alias, repo_id in MODELS.items():
            if repo.repo_id == repo_id:
                result[alias] = repo.size_on_disk
    return result


def get_models_status(active_config_value: str) -> list[dict]:
    """Return list of model info dicts for display in `mote models list`.

    Each dict has keys: alias, approx_size, downloaded, actual_size, active.
    """
    active_alias = config_value_to_alias(active_config_value)
    downloaded = get_downloaded_models()

    rows = []
    for alias in MODELS:
        downloaded_size = downloaded.get(alias)
        rows.append(
            {
                "alias": alias,
                "approx_size": APPROX_SIZES[alias],
                "downloaded": downloaded_size is not None,
                "actual_size": downloaded_size,
                "active": alias == active_alias,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download_model(alias: str, force: bool = False) -> None:
    """Download a KB-Whisper model to the HF cache with Rich progress.

    Raises KeyError for invalid alias.
    """
    repo_id = MODELS[alias]  # raises KeyError for invalid alias
    snapshot_download(
        repo_id,
        allow_patterns=ALLOW_PATTERNS,
        tqdm_class=rich_tqdm,
        force_download=force,
    )


def cleanup_partial_download(alias: str) -> None:
    """Remove the entire model cache directory to clean up a partial download.

    Called after Ctrl+C to ensure next download starts fresh (D-08).
    """
    repo_id = MODELS[alias]
    cache_dir = Path(huggingface_hub.constants.HF_HUB_CACHE)
    folder = repo_folder_name(repo_id=repo_id, repo_type="model")
    model_dir = cache_dir / folder
    if model_dir.exists():
        shutil.rmtree(model_dir)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_model(alias: str) -> int:
    """Delete all cached revisions of a model from the HF cache.

    Returns bytes freed (0 if model was not cached or cache dir missing).
    Uses delete_revisions().execute() for HF cache consistency — handles
    blob deduplication correctly.
    """
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


# ---------------------------------------------------------------------------
# Guard for transcription
# ---------------------------------------------------------------------------


def require_model_downloaded(alias: str) -> None:
    """Raise ClickException if the model is not in the HF cache.

    Call this before loading WhisperModel to provide clear user instructions
    rather than a cryptic download-on-demand (MOD-04).
    """
    if not is_model_downloaded(alias):
        raise click.ClickException(
            f"Model '{alias}' is not downloaded.\n"
            f"Run: mote models download {alias}"
        )
