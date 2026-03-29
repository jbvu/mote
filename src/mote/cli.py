"""Mote CLI entry point."""

from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mote import __version__
from mote.config import get_config_dir, get_config_path, ensure_config, load_config, set_config_value
from mote.audio import (
    find_blackhole_device,
    record_session,
    is_recording_active,
    find_orphan_recordings,
)
from mote.models import (
    MODELS,
    APPROX_SIZES,
    is_model_downloaded,
    get_models_status,
    download_model,
    delete_model,
    cleanup_partial_download,
    config_value_to_alias,
)
from mote.transcribe import transcribe_file, get_wav_duration
from mote.output import write_transcript, list_transcripts, _sanitize_name


@click.group()
@click.version_option(version=__version__, prog_name="mote")
def cli():
    """Mote - Swedish meeting transcription."""
    pass


@cli.group()
def config():
    """View and edit configuration."""
    pass


@config.command("show")
def config_show():
    """Print current configuration."""
    path = ensure_config()
    click.echo(path.read_text())


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value (e.g., general.language en)."""
    try:
        set_config_value(key, value)
        click.echo(f"Set {key} = {value}")
    except (KeyError, ValueError) as e:
        raise click.ClickException(str(e))


@config.command("path")
def config_path():
    """Print path to config file."""
    click.echo(str(get_config_path()))


@cli.command("status")
def status_command():
    """Show whether a recording is in progress or idle."""
    pid_path = get_config_dir() / "mote.pid"
    alive, pid = is_recording_active(pid_path)
    if alive:
        click.echo(f"Recording in progress (PID {pid})")
    else:
        if pid is not None:
            # Stale PID — clean up
            pid_path.unlink(missing_ok=True)
        click.echo("Idle")


@cli.command("record")
@click.option("--engine", type=click.Choice(["local", "openai"]), default=None,
              help="Transcription engine (overrides config).")
@click.option("--language", type=click.Choice(["sv", "no", "da", "fi", "en"]), default=None,
              help="Language code (overrides config).")
@click.option("--no-transcribe", is_flag=True, default=False,
              help="Save WAV only, skip transcription.")
@click.option("--name", default=None, help="Optional name for output files (e.g., 'standup').")
@click.option("--output-format", "extra_formats", multiple=True,
              type=click.Choice(["json"]), help="Additional output formats.")
def record_command(engine, language, no_transcribe, name, extra_formats):
    """Start recording system audio via BlackHole."""
    config_dir = get_config_dir()
    pid_path = config_dir / "mote.pid"
    recordings_dir = config_dir / "recordings"

    # Check for active recording (D-12)
    alive, pid = is_recording_active(pid_path)
    if alive:
        raise click.ClickException(
            f"Recording already in progress (PID {pid}). "
            "Stop the other recording first, or run 'mote status' to check."
        )
    if pid is not None:
        # Stale PID file — warn and clean up (D-12)
        click.echo(f"Warning: Found stale PID file (process {pid} is dead). Cleaning up.")
        pid_path.unlink(missing_ok=True)

    # Check for orphaned recordings (D-05)
    orphans = find_orphan_recordings(recordings_dir)
    if orphans:
        click.echo(f"Warning: Found {len(orphans)} orphaned recording(s) in {recordings_dir}:")
        for o in orphans:
            size_mb = o.stat().st_size / (1024 * 1024)
            click.echo(f"  {o.name} ({size_mb:.1f} MB)")
        click.echo("These may be from a previous crashed session.")
        click.echo()

    # Detect BlackHole (D-07, D-08, D-09)
    device = find_blackhole_device()
    if device is None:
        raise click.ClickException(
            "BlackHole audio device not found.\n"
            "Install it with: brew install blackhole-2ch\n"
            "Then restart your audio routing."
        )

    device_index = device["index"]
    click.echo(f"Recording from {device['name']} (16kHz mono)")

    # Start recording (blocks until Ctrl+C)
    try:
        wav_path = record_session(device_index, recordings_dir, pid_path)
        click.echo(f"\nRecording saved: {wav_path}")
    except Exception as e:
        raise click.ClickException(f"Recording failed: {e}")

    # --- Auto-transcription (D-01, D-02, D-03) ---
    if no_transcribe:
        return

    cfg = load_config()
    resolved_engine = engine or cfg.get("transcription", {}).get("engine", "local")
    resolved_language = language or cfg.get("transcription", {}).get("language", "sv")
    model_config = cfg.get("transcription", {}).get("model", "kb-whisper-medium")
    model_alias = config_value_to_alias(model_config) or "medium"
    api_key = cfg.get("api_keys", {}).get("openai") or None
    if api_key == "":
        api_key = None

    output_cfg = cfg.get("output", {})
    output_dir = Path(output_cfg.get("dir", "~/Documents/mote")).expanduser()
    formats = list(output_cfg.get("format", ["markdown", "txt"]))
    for fmt in extra_formats:
        if fmt not in formats:
            formats.append(fmt)
    sanitized_name = _sanitize_name(name) if name else None

    try:
        _run_transcription(
            wav_path, resolved_engine, resolved_language, model_alias,
            api_key, output_dir, formats, sanitized_name,
        )
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Transcription failed: {e}\nWAV kept at: {wav_path}")


@cli.command("list")
@click.option("--all", "show_all", is_flag=True, default=False,
              help="Show all transcripts, not just the last 20.")
def list_command(show_all):
    """Show recent transcripts."""
    cfg = load_config()
    output_dir = Path(cfg.get("output", {}).get("dir", "~/Documents/mote")).expanduser()

    records = list_transcripts(output_dir)
    if not show_all:
        records = records[:20]

    if not records:
        click.echo("No transcripts found.")
        return

    console = Console()
    table = Table(title="Recent Transcripts", show_header=True, header_style="bold")
    table.add_column("Filename", style="cyan")
    table.add_column("Date", no_wrap=True)
    table.add_column("Duration", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Engine")
    for r in records:
        mins, secs = divmod(r["duration"], 60)
        table.add_row(
            r["filename"],
            r["date"],
            f"{mins}:{secs:02d}",
            f"{r['words']:,}",
            r["engine"],
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_transcription(
    wav_path: Path,
    engine: str,
    language: str,
    model_alias: str,
    api_key: str | None,
    output_dir: Path,
    formats: list[str],
    name: str | None,
    delete_wav: bool = True,
    timestamp: datetime | None = None,
) -> list[Path]:
    """Shared post-recording transcription pipeline.

    Used by both record_command and transcribe_command (D-12).
    Returns list of written file paths.
    """
    duration = get_wav_duration(wav_path)
    transcript = transcribe_file(wav_path, engine, language, model_alias, api_key)

    written = write_transcript(
        transcript, output_dir, formats, duration, engine,
        language, model_alias, name, timestamp=timestamp,
    )

    if delete_wav:
        wav_path.unlink(missing_ok=True)

    word_count = len(transcript.split())
    mins, secs = divmod(int(duration), 60)
    names_str = ", ".join(p.name for p in written)
    click.echo(f"Transcription complete ({mins}:{secs:02d}, {word_count:,} words) \u2192 {names_str}")

    return written


def _human_size(bytes_: int) -> str:
    """Format byte count as a human-readable string (e.g. '77 MB', '1.5 GB')."""
    gb = bytes_ / (1024 ** 3)
    if gb >= 1.0:
        return f"{gb:.1f} GB"
    mb = bytes_ / (1024 ** 2)
    return f"{mb:.0f} MB"


# ---------------------------------------------------------------------------
# models command group
# ---------------------------------------------------------------------------


@cli.group()
def models():
    """Manage KB-Whisper transcription models."""
    pass


@models.command("list")
def models_list():
    """Show all available KB-Whisper models with download status."""
    cfg = load_config()
    active_config_value = cfg.get("transcription", {}).get("model", "kb-whisper-medium")
    rows = get_models_status(active_config_value)

    console = Console()
    table = Table(title="KB-Whisper Models", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Size", justify="right")
    table.add_column("Status")

    for row in rows:
        alias = row["alias"]
        if row["downloaded"] and row["actual_size"] is not None:
            size_str = _human_size(row["actual_size"])
        else:
            size_str = f"~{_human_size(row['approx_size'])}"

        if row["downloaded"] and row["active"]:
            status = "[green]downloaded[/green] [bold](active)[/bold]"
        elif row["downloaded"]:
            status = "[green]downloaded[/green]"
        elif row["active"]:
            status = "not downloaded [bold](active)[/bold]"
        else:
            status = "not downloaded"

        table.add_row(alias, size_str, status)

    console.print(table)


@models.command("download")
@click.argument("name")
@click.option("--force", is_flag=True, help="Re-download even if already present.")
def models_download(name, force):
    """Download a KB-Whisper model to the local HF cache."""
    if name not in MODELS:
        valid = ", ".join(MODELS.keys())
        raise click.ClickException(
            f"Unknown model '{name}'. Valid names: {valid}"
        )

    if is_model_downloaded(name) and not force:
        click.echo(
            f"kb-whisper-{name} is already downloaded. "
            "Use --force to re-download."
        )
        return

    approx = _human_size(APPROX_SIZES[name])
    click.confirm(
        f"kb-whisper-{name} is approximately {approx}. Continue?",
        default=True,
        abort=True,
    )

    try:
        download_model(name, force=force)
        click.echo(f"\nDownloaded kb-whisper-{name}.")
    except KeyboardInterrupt:
        click.echo("\nDownload cancelled.")
        cleanup_partial_download(name)
        click.echo("Partial files cleaned up.")
        raise SystemExit(1)


@models.command("delete")
@click.argument("name")
def models_delete(name):
    """Delete a downloaded KB-Whisper model from the local HF cache."""
    if name not in MODELS:
        valid = ", ".join(MODELS.keys())
        raise click.ClickException(
            f"Unknown model '{name}'. Valid names: {valid}"
        )

    if not is_model_downloaded(name):
        click.echo(f"kb-whisper-{name} is not downloaded.")
        return

    # Warn if deleting the active model (D-09)
    cfg = load_config()
    active_config_value = cfg.get("transcription", {}).get("model", "kb-whisper-medium")
    active_alias = config_value_to_alias(active_config_value)
    if name == active_alias:
        click.echo(
            f"Warning: {name} is your active model. "
            "Local transcription will fail until you download a model."
        )

    freed = delete_model(name)
    click.echo(f"Deleted kb-whisper-{name}. Freed {_human_size(freed)}.")
