"""Transcript output formatting."""

import re
from datetime import datetime
from pathlib import Path

_HEADER_TEMPLATE = """\
---
date: {date}
duration: {duration}
words: {words}
engine: {engine}
language: {language}
model: {model}
---

{transcript}"""

_HEADER_RE = re.compile(
    r"^---\n"
    r"date: (?P<date>[^\n]+)\n"
    r"duration: (?P<duration>\d+)\n"
    r"words: (?P<words>\d+)\n"
    r"engine: (?P<engine>[^\n]+)\n"
    r"language: (?P<language>[^\n]+)\n"
    r"model: (?P<model>[^\n]+)\n"
    r"---",
)


def _sanitize_name(raw: str) -> str:
    """Sanitize a meeting name for use in a filename.

    Lowercases, strips whitespace, replaces spaces with hyphens,
    removes non-alphanumeric characters, collapses multiple hyphens,
    and strips leading/trailing hyphens.
    """
    s = raw.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s


def _build_filename(ts: datetime, name: str | None, ext: str) -> str:
    """Build a transcript filename from a timestamp, optional name, and extension.

    Pattern: YYYY-MM-DD_HHMM[_{name}].{ext}
    """
    base = ts.strftime("%Y-%m-%d_%H%M")
    if name:
        sanitized = _sanitize_name(name)
        if sanitized:
            base = f"{base}_{sanitized}"
    return f"{base}.{ext}"


def write_transcript(
    transcript: str,
    output_dir: Path,
    formats: list[str],
    duration_seconds: float,
    engine: str,
    language: str,
    model_alias: str,
    name: str | None = None,
    timestamp: datetime | None = None,
) -> list[Path]:
    """Write transcript to one or more files in output_dir.

    Args:
        transcript: The transcript text.
        output_dir: Directory where files are written (created if absent).
        formats: List of output formats — "markdown" and/or "txt".
        duration_seconds: Recording duration in seconds (rounded to int).
        engine: Transcription engine name (e.g. "local", "openai").
        language: Language code (e.g. "sv").
        model_alias: Model identifier (e.g. "kb-whisper-medium").
        name: Optional meeting name for the filename.
        timestamp: Timestamp to use for filenames; defaults to now().

    Returns:
        List of Path objects for the files written.
    """
    ts = timestamp or datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    if "markdown" in formats:
        header = _HEADER_TEMPLATE.format(
            date=ts.isoformat(),
            duration=round(duration_seconds),
            words=len(transcript.split()),
            engine=engine,
            language=language,
            model=model_alias,
            transcript=transcript,
        )
        md_path = output_dir / _build_filename(ts, name, "md")
        md_path.write_text(header, encoding="utf-8")
        written.append(md_path)

    if "txt" in formats:
        txt_path = output_dir / _build_filename(ts, name, "txt")
        txt_path.write_text(transcript, encoding="utf-8")
        written.append(txt_path)

    return written


def list_transcripts(output_dir: Path) -> list[dict]:
    """List transcripts in output_dir, parsed from .md files, newest first.

    Args:
        output_dir: Directory to scan for .md transcript files.

    Returns:
        List of dicts with keys: filename, date, duration (int), words (int), engine.
        Returns [] if directory does not exist or contains no valid transcripts.
    """
    if not output_dir.exists():
        return []

    md_files = list(output_dir.glob("*.md"))
    # Sort by modification time, newest first
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    results = []
    for md_path in md_files:
        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError:
            continue

        match = _HEADER_RE.match(content)
        if not match:
            continue

        results.append(
            {
                "filename": md_path.name,
                "date": match.group("date"),
                "duration": int(match.group("duration")),
                "words": int(match.group("words")),
                "engine": match.group("engine"),
            }
        )

    return results
