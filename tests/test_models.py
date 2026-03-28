"""Unit tests for mote.models — model management logic."""

from unittest.mock import MagicMock, patch

import click
import pytest

from mote.models import (
    ALLOW_PATTERNS,
    APPROX_SIZES,
    MODELS,
    cleanup_partial_download,
    config_value_to_alias,
    delete_model,
    download_model,
    get_downloaded_models,
    get_models_status,
    is_model_downloaded,
    require_model_downloaded,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_models_dict_has_five_aliases():
    assert set(MODELS.keys()) == {"tiny", "base", "small", "medium", "large"}


def test_models_repo_ids():
    assert MODELS["tiny"] == "KBLab/kb-whisper-tiny"
    assert MODELS["base"] == "KBLab/kb-whisper-base"
    assert MODELS["small"] == "KBLab/kb-whisper-small"
    assert MODELS["medium"] == "KBLab/kb-whisper-medium"
    assert MODELS["large"] == "KBLab/kb-whisper-large"


def test_approx_sizes_has_five_aliases():
    assert set(APPROX_SIZES.keys()) == {"tiny", "base", "small", "medium", "large"}


def test_approx_sizes_values():
    assert APPROX_SIZES["tiny"] == 77 * 1024 * 1024
    assert APPROX_SIZES["base"] == 143 * 1024 * 1024
    assert APPROX_SIZES["small"] == 466 * 1024 * 1024
    assert APPROX_SIZES["medium"] == 1462 * 1024 * 1024
    assert APPROX_SIZES["large"] == 2949 * 1024 * 1024


def test_allow_patterns_contains_required_files():
    assert "model.bin" in ALLOW_PATTERNS
    assert "config.json" in ALLOW_PATTERNS
    assert "preprocessor_config.json" in ALLOW_PATTERNS
    assert "tokenizer.json" in ALLOW_PATTERNS
    assert any("vocabulary" in p for p in ALLOW_PATTERNS)


# ---------------------------------------------------------------------------
# config_value_to_alias
# ---------------------------------------------------------------------------


def test_config_value_to_alias_medium():
    assert config_value_to_alias("kb-whisper-medium") == "medium"


def test_config_value_to_alias_all():
    for alias in MODELS:
        assert config_value_to_alias(f"kb-whisper-{alias}") == alias


def test_config_value_to_alias_unknown():
    assert config_value_to_alias("some-unknown-model") is None


def test_config_value_to_alias_empty():
    assert config_value_to_alias("") is None


# ---------------------------------------------------------------------------
# is_model_downloaded
# ---------------------------------------------------------------------------


@patch("mote.models.try_to_load_from_cache")
def test_is_model_downloaded_true(mock_try):
    mock_try.return_value = "/some/cache/path/model.bin"
    assert is_model_downloaded("medium") is True
    mock_try.assert_called_once_with("KBLab/kb-whisper-medium", "model.bin")


@patch("mote.models.try_to_load_from_cache")
def test_is_model_downloaded_false(mock_try):
    mock_try.return_value = None
    assert is_model_downloaded("medium") is False


@patch("mote.models.try_to_load_from_cache")
def test_is_model_downloaded_small(mock_try):
    mock_try.return_value = "/some/path"
    assert is_model_downloaded("small") is True
    mock_try.assert_called_once_with("KBLab/kb-whisper-small", "model.bin")


# ---------------------------------------------------------------------------
# get_downloaded_models
# ---------------------------------------------------------------------------


def _make_mock_cache(alias="medium", size=None):
    """Build a minimal mock HFCacheInfo with one repo."""
    if size is None:
        size = APPROX_SIZES[alias]
    mock_repo = MagicMock()
    mock_repo.repo_id = f"KBLab/kb-whisper-{alias}"
    mock_repo.repo_type = "model"
    mock_repo.size_on_disk = size
    mock_rev = MagicMock()
    mock_rev.commit_hash = "abc123"
    mock_repo.revisions = [mock_rev]
    mock_cache = MagicMock()
    mock_cache.repos = [mock_repo]
    return mock_cache


@patch("mote.models.scan_cache_dir")
def test_get_downloaded_models_one_model(mock_scan):
    mock_scan.return_value = _make_mock_cache("medium")
    result = get_downloaded_models()
    assert "medium" in result
    assert result["medium"] == APPROX_SIZES["medium"]


@patch("mote.models.scan_cache_dir")
def test_get_downloaded_models_empty_cache(mock_scan):
    mock_cache = MagicMock()
    mock_cache.repos = []
    mock_scan.return_value = mock_cache
    result = get_downloaded_models()
    assert result == {}


@patch("mote.models.scan_cache_dir")
def test_get_downloaded_models_cache_not_found(mock_scan):
    from huggingface_hub.errors import CacheNotFound
    mock_scan.side_effect = CacheNotFound("no cache dir", cache_dir="/fake")
    result = get_downloaded_models()
    assert result == {}


@patch("mote.models.scan_cache_dir")
def test_get_downloaded_models_ignores_non_model_repos(mock_scan):
    mock_repo = MagicMock()
    mock_repo.repo_id = "KBLab/kb-whisper-medium"
    mock_repo.repo_type = "dataset"  # not a model
    mock_repo.size_on_disk = 100
    mock_cache = MagicMock()
    mock_cache.repos = [mock_repo]
    mock_scan.return_value = mock_cache
    result = get_downloaded_models()
    assert result == {}


# ---------------------------------------------------------------------------
# get_models_status
# ---------------------------------------------------------------------------


@patch("mote.models.get_downloaded_models")
def test_get_models_status_returns_five_rows(mock_downloaded):
    mock_downloaded.return_value = {}
    rows = get_models_status("kb-whisper-medium")
    assert len(rows) == 5


@patch("mote.models.get_downloaded_models")
def test_get_models_status_marks_active(mock_downloaded):
    mock_downloaded.return_value = {}
    rows = get_models_status("kb-whisper-medium")
    active_rows = [r for r in rows if r["active"]]
    assert len(active_rows) == 1
    assert active_rows[0]["alias"] == "medium"


@patch("mote.models.get_downloaded_models")
def test_get_models_status_marks_downloaded(mock_downloaded):
    mock_downloaded.return_value = {"medium": 1462 * 1024 * 1024}
    rows = get_models_status("kb-whisper-medium")
    medium_row = next(r for r in rows if r["alias"] == "medium")
    assert medium_row["downloaded"] is True
    assert medium_row["actual_size"] == 1462 * 1024 * 1024


@patch("mote.models.get_downloaded_models")
def test_get_models_status_not_downloaded(mock_downloaded):
    mock_downloaded.return_value = {}
    rows = get_models_status("kb-whisper-medium")
    for row in rows:
        assert row["downloaded"] is False
        assert row["actual_size"] is None


@patch("mote.models.get_downloaded_models")
def test_get_models_status_row_fields(mock_downloaded):
    mock_downloaded.return_value = {}
    rows = get_models_status("kb-whisper-medium")
    for row in rows:
        assert "alias" in row
        assert "approx_size" in row
        assert "downloaded" in row
        assert "actual_size" in row
        assert "active" in row


# ---------------------------------------------------------------------------
# download_model
# ---------------------------------------------------------------------------


@patch("mote.models.snapshot_download")
def test_download_model_calls_snapshot_download(mock_snap):
    download_model("medium")
    mock_snap.assert_called_once()
    call_kwargs = mock_snap.call_args
    # First positional arg is repo_id
    assert call_kwargs[0][0] == "KBLab/kb-whisper-medium"


@patch("mote.models.snapshot_download")
def test_download_model_passes_allow_patterns(mock_snap):
    download_model("medium")
    call_kwargs = mock_snap.call_args
    assert call_kwargs[1]["allow_patterns"] == ALLOW_PATTERNS


@patch("mote.models.snapshot_download")
def test_download_model_passes_tqdm_class(mock_snap):
    from tqdm.rich import tqdm as rich_tqdm
    download_model("medium")
    call_kwargs = mock_snap.call_args
    assert call_kwargs[1]["tqdm_class"] == rich_tqdm


@patch("mote.models.snapshot_download")
def test_download_model_force_false_by_default(mock_snap):
    download_model("medium")
    call_kwargs = mock_snap.call_args
    assert call_kwargs[1].get("force_download") is False


@patch("mote.models.snapshot_download")
def test_download_model_force_true(mock_snap):
    download_model("medium", force=True)
    call_kwargs = mock_snap.call_args
    assert call_kwargs[1].get("force_download") is True


def test_download_model_invalid_alias():
    with pytest.raises(KeyError):
        download_model("invalid_alias_xyz")


# ---------------------------------------------------------------------------
# cleanup_partial_download
# ---------------------------------------------------------------------------


@patch("mote.models.shutil.rmtree")
@patch("mote.models.Path")
def test_cleanup_partial_download_calls_rmtree_when_exists(mock_path_cls, mock_rmtree):
    mock_model_dir = MagicMock()
    mock_model_dir.exists.return_value = True
    # Path(HF_HUB_CACHE) / folder -> mock_model_dir
    mock_path_instance = MagicMock()
    mock_path_instance.__truediv__ = MagicMock(return_value=mock_model_dir)
    mock_path_cls.return_value = mock_path_instance
    cleanup_partial_download("medium")
    mock_rmtree.assert_called_once_with(mock_model_dir)


@patch("mote.models.shutil.rmtree")
@patch("mote.models.Path")
def test_cleanup_partial_download_skips_rmtree_when_not_exists(mock_path_cls, mock_rmtree):
    mock_model_dir = MagicMock()
    mock_model_dir.exists.return_value = False
    mock_path_instance = MagicMock()
    mock_path_instance.__truediv__ = MagicMock(return_value=mock_model_dir)
    mock_path_cls.return_value = mock_path_instance
    cleanup_partial_download("medium")
    mock_rmtree.assert_not_called()


# ---------------------------------------------------------------------------
# delete_model
# ---------------------------------------------------------------------------


@patch("mote.models.scan_cache_dir")
def test_delete_model_returns_freed_bytes(mock_scan):
    mock_cache = _make_mock_cache("medium")
    mock_strategy = MagicMock()
    mock_strategy.expected_freed_size = 1462 * 1024 * 1024
    mock_cache.delete_revisions.return_value = mock_strategy
    mock_scan.return_value = mock_cache

    freed = delete_model("medium")
    assert freed == 1462 * 1024 * 1024
    mock_strategy.execute.assert_called_once()


@patch("mote.models.scan_cache_dir")
def test_delete_model_passes_all_revision_hashes(mock_scan):
    mock_cache = _make_mock_cache("medium")
    # Add a second revision
    mock_rev2 = MagicMock()
    mock_rev2.commit_hash = "def456"
    mock_cache.repos[0].revisions.append(mock_rev2)

    mock_strategy = MagicMock()
    mock_strategy.expected_freed_size = 100
    mock_cache.delete_revisions.return_value = mock_strategy
    mock_scan.return_value = mock_cache

    delete_model("medium")
    call_args = mock_cache.delete_revisions.call_args[0]
    assert "abc123" in call_args
    assert "def456" in call_args


@patch("mote.models.scan_cache_dir")
def test_delete_model_not_in_cache_returns_zero(mock_scan):
    mock_cache = MagicMock()
    mock_cache.repos = []
    mock_scan.return_value = mock_cache
    freed = delete_model("medium")
    assert freed == 0


@patch("mote.models.scan_cache_dir")
def test_delete_model_cache_not_found_returns_zero(mock_scan):
    from huggingface_hub.errors import CacheNotFound
    mock_scan.side_effect = CacheNotFound("no cache", cache_dir="/fake")
    freed = delete_model("medium")
    assert freed == 0


# ---------------------------------------------------------------------------
# require_model_downloaded
# ---------------------------------------------------------------------------


@patch("mote.models.try_to_load_from_cache")
def test_require_model_downloaded_does_nothing_when_cached(mock_try):
    mock_try.return_value = "/some/path/model.bin"
    # Should not raise
    require_model_downloaded("medium")


@patch("mote.models.try_to_load_from_cache")
def test_require_model_downloaded_raises_when_not_cached(mock_try):
    mock_try.return_value = None
    with pytest.raises(click.ClickException) as exc_info:
        require_model_downloaded("medium")
    assert "mote models download medium" in str(exc_info.value.format_message())


@patch("mote.models.try_to_load_from_cache")
def test_require_model_downloaded_message_mentions_alias(mock_try):
    mock_try.return_value = None
    with pytest.raises(click.ClickException) as exc_info:
        require_model_downloaded("large")
    assert "large" in str(exc_info.value.format_message())
