"""Unit tests for mote output module."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from mote.output import (
    _build_filename,
    _sanitize_name,
    list_transcripts,
    write_transcript,
)

# Fixed timestamp for deterministic filenames
_TS = datetime(2026, 3, 28, 14, 30)


# ---------------------------------------------------------------------------
# _sanitize_name
# ---------------------------------------------------------------------------


def test_sanitize_name():
    assert _sanitize_name("My Meeting!") == "my-meeting"
    assert _sanitize_name("  STANDUP  ") == "standup"
    assert _sanitize_name("a--b") == "a-b"
    assert _sanitize_name("---") == ""


def test_sanitize_name_spaces():
    assert _sanitize_name("team sync call") == "team-sync-call"


# ---------------------------------------------------------------------------
# _build_filename
# ---------------------------------------------------------------------------


def test_filename_no_name():
    result = _build_filename(_TS, None, "md")
    assert result == "2026-03-28_1430.md"


def test_filename_with_name():
    result = _build_filename(_TS, "standup", "md")
    assert result == "2026-03-28_1430_standup.md"


# ---------------------------------------------------------------------------
# write_transcript — formats
# ---------------------------------------------------------------------------


def test_write_markdown(tmp_path):
    paths = write_transcript(
        transcript="Hello world",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=90.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name=None,
        timestamp=_TS,
    )
    assert len(paths) == 1
    md_file = paths[0]
    assert md_file.suffix == ".md"
    content = md_file.read_text()
    assert content.startswith("---\n")
    assert "date:" in content
    assert "duration:" in content
    assert "words:" in content
    assert "engine:" in content
    assert "language:" in content
    assert "model:" in content
    assert "---\n\n" in content
    assert "Hello world" in content


def test_write_txt(tmp_path):
    paths = write_transcript(
        transcript="Hello world",
        output_dir=tmp_path,
        formats=["txt"],
        duration_seconds=90.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name=None,
        timestamp=_TS,
    )
    assert len(paths) == 1
    txt_file = paths[0]
    assert txt_file.suffix == ".txt"
    content = txt_file.read_text()
    assert content == "Hello world"
    assert "---" not in content


def test_write_both(tmp_path):
    paths = write_transcript(
        transcript="Hello world",
        output_dir=tmp_path,
        formats=["markdown", "txt"],
        duration_seconds=90.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name=None,
        timestamp=_TS,
    )
    assert len(paths) == 2
    suffixes = {p.suffix for p in paths}
    assert ".md" in suffixes
    assert ".txt" in suffixes


# ---------------------------------------------------------------------------
# write_transcript — filenames
# ---------------------------------------------------------------------------


def test_filename_no_name_in_write(tmp_path):
    paths = write_transcript(
        transcript="text",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=10.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-small",
        name=None,
        timestamp=_TS,
    )
    assert paths[0].name == "2026-03-28_1430.md"


def test_filename_with_name_in_write(tmp_path):
    paths = write_transcript(
        transcript="text",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=10.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-small",
        name="standup",
        timestamp=_TS,
    )
    assert paths[0].name == "2026-03-28_1430_standup.md"


# ---------------------------------------------------------------------------
# write_transcript — markdown header fields
# ---------------------------------------------------------------------------


def test_markdown_header_fields(tmp_path):
    paths = write_transcript(
        transcript="one two three",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=125.7,
        engine="openai",
        language="sv",
        model_alias="whisper-1",
        name=None,
        timestamp=_TS,
    )
    content = paths[0].read_text()
    # ISO 8601 date
    assert "date: 2026-03-28" in content
    # duration is integer seconds
    assert "duration: 126" in content
    # words count
    assert "words: 3" in content
    # engine and language and model
    assert "engine: openai" in content
    assert "language: sv" in content
    assert "model: whisper-1" in content


# ---------------------------------------------------------------------------
# write_transcript — creates output_dir
# ---------------------------------------------------------------------------


def test_creates_output_dir(tmp_path):
    nested_dir = tmp_path / "a" / "b" / "c"
    assert not nested_dir.exists()
    write_transcript(
        transcript="text",
        output_dir=nested_dir,
        formats=["txt"],
        duration_seconds=10.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name=None,
        timestamp=_TS,
    )
    assert nested_dir.exists()


# ---------------------------------------------------------------------------
# write_transcript — returns Path objects
# ---------------------------------------------------------------------------


def test_write_returns_paths(tmp_path):
    paths = write_transcript(
        transcript="hello",
        output_dir=tmp_path,
        formats=["markdown", "txt"],
        duration_seconds=5.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name=None,
        timestamp=_TS,
    )
    for p in paths:
        assert isinstance(p, Path)
        assert p.exists()


# ---------------------------------------------------------------------------
# write_transcript — injectable timestamp
# ---------------------------------------------------------------------------


def test_injectable_timestamp(tmp_path):
    ts1 = datetime(2024, 1, 15, 9, 5)
    paths = write_transcript(
        transcript="text",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=10.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name=None,
        timestamp=ts1,
    )
    assert paths[0].name == "2024-01-15_0905.md"


# ---------------------------------------------------------------------------
# list_transcripts
# ---------------------------------------------------------------------------


def test_list_transcripts_parses_metadata(tmp_path):
    write_transcript(
        transcript="Möte om budget",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=300.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-large",
        name="budget",
        timestamp=_TS,
    )
    results = list_transcripts(tmp_path)
    assert len(results) == 1
    item = results[0]
    assert "filename" in item
    assert "date" in item
    assert "duration" in item
    assert "words" in item
    assert "engine" in item
    assert item["duration"] == 300
    assert item["words"] == 3
    assert item["engine"] == "local"


def test_list_transcripts_newest_first(tmp_path):
    import time

    ts_old = datetime(2026, 1, 1, 10, 0)
    ts_new = datetime(2026, 3, 1, 10, 0)

    write_transcript(
        transcript="old meeting",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=60.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name="old",
        timestamp=ts_old,
    )
    # Brief pause ensures different mtime
    time.sleep(0.05)
    write_transcript(
        transcript="new meeting",
        output_dir=tmp_path,
        formats=["markdown"],
        duration_seconds=60.0,
        engine="local",
        language="sv",
        model_alias="kb-whisper-medium",
        name="new",
        timestamp=ts_new,
    )

    results = list_transcripts(tmp_path)
    assert len(results) == 2
    assert "new" in results[0]["filename"]
    assert "old" in results[1]["filename"]


def test_list_skips_malformed(tmp_path):
    # Write a .md file without valid YAML header
    bad_file = tmp_path / "bad.md"
    bad_file.write_text("No header here, just text.")

    results = list_transcripts(tmp_path)
    assert results == []


def test_list_empty_dir(tmp_path):
    results = list_transcripts(tmp_path)
    assert results == []


def test_list_nonexistent_dir(tmp_path):
    nonexistent = tmp_path / "does_not_exist"
    results = list_transcripts(nonexistent)
    assert results == []


# ---------------------------------------------------------------------------
# write_transcript — JSON format
# ---------------------------------------------------------------------------


def test_write_json(tmp_path):
    """write_transcript with formats=['json'] produces a .json file in output_dir."""
    paths = write_transcript("test text", tmp_path, ["json"], 90.0, "local", "sv", "medium", timestamp=_TS)
    assert len(paths) == 1
    assert paths[0].suffix == ".json"
    assert paths[0].exists()


def test_write_json_fields(tmp_path):
    """JSON file contains exactly 7 keys: date, duration, words, engine, language, model, transcript."""
    paths = write_transcript("hello world", tmp_path, ["json"], 120.0, "openai", "en", "whisper-1", timestamp=_TS)
    data = json.loads(paths[0].read_text(encoding="utf-8"))
    assert set(data.keys()) == {"date", "duration", "words", "engine", "language", "model", "transcript"}
    assert data["duration"] == 120
    assert data["words"] == 2
    assert data["engine"] == "openai"
    assert data["transcript"] == "hello world"


def test_write_json_field_types(tmp_path):
    """date is ISO string, duration is int, words is int, transcript is string."""
    paths = write_transcript("one two three", tmp_path, ["json"], 65.7, "local", "sv", "medium", timestamp=_TS)
    data = json.loads(paths[0].read_text(encoding="utf-8"))
    assert isinstance(data["date"], str)
    assert isinstance(data["duration"], int)
    assert isinstance(data["words"], int)
    assert isinstance(data["transcript"], str)


def test_write_json_swedish_chars(tmp_path):
    """Swedish chars stored as literal UTF-8 (no \\u escapes)."""
    swedish = "Hej och v\u00e4lkomna till m\u00f6tet"
    paths = write_transcript(swedish, tmp_path, ["json"], 60.0, "local", "sv", "medium", timestamp=_TS)
    raw = paths[0].read_text(encoding="utf-8")
    assert "\u00e4" in raw  # a-umlaut as literal character
    assert "\\u00e4" not in raw  # NOT as escape sequence


def test_write_json_alongside_md(tmp_path):
    """formats=['markdown', 'txt', 'json'] produces 3 files."""
    paths = write_transcript("text", tmp_path, ["markdown", "txt", "json"], 30.0, "local", "sv", "medium", timestamp=_TS)
    assert len(paths) == 3
    exts = {p.suffix for p in paths}
    assert exts == {".md", ".txt", ".json"}


def test_write_json_filename(tmp_path):
    """JSON filename follows same pattern as md/txt (YYYY-MM-DD_HHMM[_name].json)."""
    paths = write_transcript("text", tmp_path, ["json"], 30.0, "local", "sv", "medium", name="standup", timestamp=_TS)
    assert paths[0].name == "2026-03-28_1430_standup.json"
