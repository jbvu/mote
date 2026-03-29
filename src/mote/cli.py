"""Mote CLI entry point."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mote import __version__
from mote.config import get_config_dir, get_config_path, ensure_config, load_config, set_config_value, validate_config, cleanup_old_wavs
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


AUDIO_RESTORE_FILE = "audio_restore.json"


# ---------------------------------------------------------------------------
# SwitchAudioSource helpers
# ---------------------------------------------------------------------------


def _detect_switch_audio_source() -> bool:
    """Return True if SwitchAudioSource is on PATH."""
    return shutil.which("SwitchAudioSource") is not None


def _get_current_output_device() -> str | None:
    """Return current audio output device name, or None on failure."""
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-t", "output", "-c"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, OSError):
        return None


def _set_output_device(device_name: str) -> bool:
    """Switch audio output to device_name. Return True on success."""
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-t", "output", "-s", device_name],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _write_audio_restore(config_dir: Path, device_name: str) -> None:
    """Write crash recovery file before switching audio output."""
    restore_path = config_dir / AUDIO_RESTORE_FILE
    restore_path.write_text(json.dumps({"device": device_name}))


def _read_audio_restore(config_dir: Path) -> str | None:
    """Read device name from crash recovery file, or None if absent/malformed."""
    restore_path = config_dir / AUDIO_RESTORE_FILE
    if not restore_path.exists():
        return None
    try:
        data = json.loads(restore_path.read_text())
        return data.get("device")
    except (json.JSONDecodeError, OSError):
        return None


def _delete_audio_restore(config_dir: Path) -> None:
    """Remove crash recovery file."""
    (config_dir / AUDIO_RESTORE_FILE).unlink(missing_ok=True)


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


@config.command("validate")
def config_validate():
    """Run pre-flight configuration checks."""
    cfg = load_config()
    errors, warnings = validate_config(cfg)

    for w in warnings:
        click.echo(f"Warning: {w}")
    for e in errors:
        click.echo(f"Error: {e}")

    if errors:
        raise click.ClickException(
            f"Found {len(errors)} error(s). Fix before recording."
        )

    if warnings:
        click.echo(f"\nConfiguration OK ({len(warnings)} warning(s)).")
    else:
        click.echo("Configuration OK.")


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
@click.option("--destination", "destinations_override", multiple=True,
              type=click.Choice(["local", "drive", "notebooklm"]),
              help="Override active destinations for this run.")
def record_command(engine, language, no_transcribe, name, extra_formats, destinations_override):
    """Start recording system audio via BlackHole."""
    config_dir = get_config_dir()
    pid_path = config_dir / "mote.pid"
    recordings_dir = config_dir / "recordings"

    # Crash recovery: restore audio if previous session crashed (D-09)
    crashed_device = _read_audio_restore(config_dir)
    if crashed_device:
        if _detect_switch_audio_source():
            ok = _set_output_device(crashed_device)
            if ok:
                _delete_audio_restore(config_dir)
                click.echo(f"Restored audio output to {crashed_device} (from previous crash)")
            else:
                click.echo(
                    f"Warning: Could not restore audio to {crashed_device}. "
                    f"File kept at {config_dir / AUDIO_RESTORE_FILE}"
                )
        else:
            click.echo(
                f"Warning: audio_restore.json found but SwitchAudioSource not installed. "
                f"Manually switch audio to {crashed_device} or run: "
                f"brew install switchaudio-osx && mote audio restore"
            )

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

    # Pre-flight config validation (D-04)
    cfg = load_config()
    errors, warnings = validate_config(cfg)
    for w in warnings:
        click.echo(f"Warning: {w}")
    if errors:
        for e in errors:
            click.echo(f"Error: {e}")
        raise click.ClickException("Fix configuration errors before recording.")

    # Auto-cleanup expired WAVs (D-14)
    retention_days = cfg.get("cleanup", {}).get("wav_retention_days", 7)
    if retention_days > 0:
        cleanup_old_wavs(recordings_dir, retention_days)

    # Check for orphaned recordings (D-05)
    orphans = find_orphan_recordings(recordings_dir)
    if orphans:
        click.echo(f"Warning: Found {len(orphans)} orphaned recording(s) in {recordings_dir}:")
        for o in orphans:
            size_mb = o.stat().st_size / (1024 * 1024)
            click.echo(f"  {o.name} ({size_mb:.1f} MB)")
        click.echo("These may be from a previous crashed session.")
        click.echo("Transcribe them with: mote transcribe <file>")
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

    # Audio output switching (D-02, D-03, D-04)
    has_switcher = _detect_switch_audio_source()
    original_device: str | None = None

    if has_switcher:
        original_device = _get_current_output_device()
        if original_device:
            _write_audio_restore(config_dir, original_device)
            ok = _set_output_device("BlackHole 2ch")
            if ok:
                click.echo(f"Switched audio output to BlackHole 2ch (was: {original_device})")
            else:
                _delete_audio_restore(config_dir)
                original_device = None
                click.echo("Warning: Could not switch audio to BlackHole. Route audio manually.")
        else:
            click.echo("Warning: Could not detect current audio output device. Skipping auto-switch.")
    else:
        click.echo(
            "Advisory: SwitchAudioSource not installed \u2014 route audio to BlackHole manually.\n"
            "Install with: brew install switchaudio-osx"
        )

    # Start recording (blocks until Ctrl+C)
    try:
        try:
            wav_path = record_session(device_index, recordings_dir, pid_path)
            click.echo(f"\nRecording saved: {wav_path}")
        except Exception as e:
            raise click.ClickException(f"Recording failed: {e}")
    finally:
        if original_device:
            try:
                _set_output_device(original_device)
                _delete_audio_restore(config_dir)
                click.echo(f"Restored audio output to {original_device}")
            except Exception:
                pass  # Best-effort restore; don't mask original exception (Pitfall 4)

    # --- Auto-transcription (D-01, D-02, D-03) ---
    if no_transcribe:
        return

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

    if destinations_override:
        resolved_destinations = list(destinations_override)
    else:
        resolved_destinations = cfg.get("destinations", {}).get("active", ["local"])

    while True:
        try:
            _run_transcription(
                wav_path, resolved_engine, resolved_language, model_alias,
                api_key, output_dir, formats, sanitized_name,
                destinations=resolved_destinations,
                config_dir=config_dir,
                cfg=cfg,
            )
            break
        except click.ClickException:
            raise
        except Exception as e:
            click.echo(f"Transcription failed: {e}")
            click.echo(f"WAV kept at: {wav_path}")
            if not click.confirm("Retry transcription?", default=True):
                raise click.ClickException(f"Transcription failed. WAV kept at: {wav_path}")


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


@cli.command("cleanup")
def cleanup_command():
    """Delete expired WAV recordings older than retention period."""
    cfg = load_config()
    retention_days = cfg.get("cleanup", {}).get("wav_retention_days", 7)

    if retention_days <= 0:
        click.echo("WAV retention disabled (wav_retention_days = 0). No files deleted.")
        return

    config_dir = get_config_dir()
    recordings_dir = config_dir / "recordings"
    deleted = cleanup_old_wavs(recordings_dir, retention_days)

    if deleted:
        click.echo(f"Deleted {len(deleted)} expired WAV file(s):")
        for d in deleted:
            click.echo(f"  {d.name}")
    else:
        click.echo("No expired WAV files found.")


# ---------------------------------------------------------------------------
# audio command group
# ---------------------------------------------------------------------------


@cli.group()
def audio():
    """Audio device management."""
    pass


@audio.command("restore")
def audio_restore_command():
    """Restore system audio output if left on BlackHole after a crash."""
    config_dir = get_config_dir()
    device = _read_audio_restore(config_dir)
    if device is None:
        click.echo("No audio restore file found \u2014 audio output is not stuck.")
        return
    if not _detect_switch_audio_source():
        raise click.ClickException(
            "SwitchAudioSource not installed. Cannot restore automatically.\n"
            "Install with: brew install switchaudio-osx\n"
            f"Then run: SwitchAudioSource -t output -s '{device}'"
        )
    ok = _set_output_device(device)
    if ok:
        _delete_audio_restore(config_dir)
        click.echo(f"Restored audio output to {device}")
    else:
        raise click.ClickException(f"Failed to switch to '{device}'. Is the device available?")


# ---------------------------------------------------------------------------
# auth command group
# ---------------------------------------------------------------------------


@cli.group()
def auth():
    """Manage third-party service authentication."""
    pass


@auth.command("google")
def auth_google():
    """Authenticate with Google Drive (OAuth2 browser flow)."""
    from mote.drive import get_token_path, get_credentials, run_auth_flow

    config_dir = get_config_dir()
    token_path = get_token_path(config_dir)

    creds = get_credentials(token_path)
    if creds is not None:
        # Already authenticated — show status (D-10)
        email = "authenticated (email unavailable)"
        try:
            from googleapiclient.discovery import build as build_svc
            service = build_svc("oauth2", "v2", credentials=creds)
            user_info = service.userinfo().get().execute()
            email = user_info.get("email", "authenticated (email unavailable)")
        except Exception:
            pass

        click.echo(f"Google Drive: {email}")
        click.echo(f"Token: {token_path}")
        if not click.confirm("Re-authenticate?", default=False):
            return

    creds = run_auth_flow(token_path)

    # Show success with email (D-11)
    email = "authenticated (email unavailable)"
    try:
        from googleapiclient.discovery import build as build_svc
        service = build_svc("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email", "authenticated (email unavailable)")
    except Exception:
        pass

    click.echo(f"Authenticated with Google Drive as {email}")
    click.echo(f"Token stored at {token_path}")


@auth.command("notebooklm")
def auth_notebooklm():
    """Authenticate with NotebookLM (experimental, Playwright browser flow)."""
    from mote.notebooklm import get_session_path, is_authenticated, run_login

    config_dir = get_config_dir()
    session_path = get_session_path(config_dir)

    if session_path.exists():
        click.echo(f"NotebookLM: session file exists at {session_path}")
        if not click.confirm("Re-authenticate?", default=False):
            return

    # Check for Playwright Chromium binary before attempting login
    # (RESEARCH.md Pitfall 1: playwright install chromium must be run after
    # installing notebooklm-py[browser], otherwise login fails with a cryptic error)
    if shutil.which("playwright") is not None:
        result = subprocess.run(
            ["playwright", "install", "--check", "chromium"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            click.echo(
                "Playwright Chromium browser not found. "
                "Run: playwright install chromium"
            )
            raise click.Abort()
    else:
        click.echo(
            "Playwright not found. Install the notebooklm extra and Chromium:\n"
            "  pip install 'mote[notebooklm]'\n"
            "  playwright install chromium"
        )
        raise click.Abort()

    try:
        run_login(session_path)
    except RuntimeError as e:
        raise click.ClickException(str(e))

    click.echo(f"NotebookLM session stored at {session_path}")


# ---------------------------------------------------------------------------
# upload command
# ---------------------------------------------------------------------------


@cli.command("upload")
@click.argument("file", required=False, type=click.Path(exists=True, path_type=Path))
@click.option("--last", is_flag=True, default=False, help="Upload the most recent transcript.")
def upload_command(file, last):
    """Upload a transcript file to Google Drive."""
    if file is None and not last:
        raise click.ClickException(
            "Provide a file path or use --last to upload the most recent transcript."
        )

    cfg = load_config()
    config_dir = get_config_dir()
    folder_name = cfg.get("destinations", {}).get("drive", {}).get("folder_name", "Mote Transcripts")

    if last:
        output_dir = Path(cfg.get("output", {}).get("dir", "~/Documents/mote")).expanduser()
        records = list_transcripts(output_dir)
        if not records:
            raise click.ClickException("No transcripts found.")
        # Find all files sharing the stem of the most recent transcript
        latest_name = records[0]["filename"]
        latest_stem = Path(latest_name).stem
        files_to_upload = [
            p for p in output_dir.iterdir()
            if p.stem == latest_stem and p.suffix in (".md", ".txt", ".json")
        ]
        if not files_to_upload:
            raise click.ClickException(f"Could not find transcript files for {latest_name}")
    else:
        files_to_upload = [file]

    try:
        from mote.drive import upload_transcripts
        upload_transcripts(config_dir, files_to_upload, folder_name)
        names = ", ".join(p.name for p in files_to_upload)
        click.echo(f"Uploaded to Google Drive: {names}")
    except RuntimeError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Upload failed: {e}")


@cli.command("transcribe")
@click.argument("wav_file", type=click.Path(exists=True, path_type=Path))
@click.option("--engine", type=click.Choice(["local", "openai"]), default=None,
              help="Transcription engine (overrides config).")
@click.option("--language", type=click.Choice(["sv", "no", "da", "fi", "en"]), default=None,
              help="Language code (overrides config).")
@click.option("--name", default=None, help="Optional name for output files.")
@click.option("--output-format", "extra_formats", multiple=True,
              type=click.Choice(["json"]), help="Additional output formats.")
@click.option("--destination", "destinations_override", multiple=True,
              type=click.Choice(["local", "drive", "notebooklm"]),
              help="Override active destinations for this run.")
def transcribe_command(wav_file, engine, language, name, extra_formats, destinations_override):
    """Transcribe an existing WAV file."""
    cfg = load_config()
    errors, warnings = validate_config(cfg)
    for w in warnings:
        click.echo(f"Warning: {w}")
    if errors:
        for e in errors:
            click.echo(f"Error: {e}")
        raise click.ClickException("Fix configuration errors before transcribing.")

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

    if destinations_override:
        resolved_destinations = list(destinations_override)
    else:
        resolved_destinations = cfg.get("destinations", {}).get("active", ["local"])

    # Use WAV file mtime as timestamp (per Pitfall 5 / D-11)
    ts = datetime.fromtimestamp(wav_file.stat().st_mtime)

    # Overwrite detection (D-11)
    from mote.output import _build_filename
    for fmt_name, ext in [("markdown", "md"), ("txt", "txt"), ("json", "json")]:
        if fmt_name in formats:
            predicted = output_dir / _build_filename(ts, sanitized_name, ext)
            if predicted.exists():
                if not click.confirm(
                    f"Output file {predicted.name} already exists. Overwrite?",
                    default=False,
                ):
                    raise click.ClickException("Aborted — existing files not overwritten.")

    while True:
        try:
            _run_transcription(
                wav_file, resolved_engine, resolved_language, model_alias,
                api_key, output_dir, formats, sanitized_name,
                delete_wav=False, timestamp=ts,
                destinations=resolved_destinations,
                config_dir=get_config_dir(),
                cfg=cfg,
            )
            break
        except click.ClickException:
            raise
        except Exception as e:
            click.echo(f"Transcription failed: {e}")
            click.echo(f"WAV kept at: {wav_file}")
            if not click.confirm("Retry transcription?", default=True):
                raise click.ClickException(f"Transcription failed. WAV kept at: {wav_file}")


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
    destinations: list[str] | None = None,
    config_dir: Path | None = None,
    cfg: dict | None = None,
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

    # Drive upload (D-05: local always written first, D-09: failures are warnings)
    active_destinations = destinations or (cfg or {}).get("destinations", {}).get("active", ["local"])
    if "drive" in active_destinations:
        try:
            from mote.drive import upload_transcripts
            effective_config_dir = config_dir or get_config_dir()
            folder_name = (cfg or {}).get("destinations", {}).get("drive", {}).get("folder_name", "Mote Transcripts")
            upload_transcripts(effective_config_dir, written, folder_name)
        except Exception as e:
            click.echo(
                f"Warning: Drive upload failed: {e}. "
                "Transcripts saved locally. Run 'mote upload' to retry."
            )

    # NotebookLM upload (D-08: failures are warnings, D-09: never propagates)
    if "notebooklm" in active_destinations:
        try:
            from mote.notebooklm import upload_transcript
            effective_config_dir = config_dir or get_config_dir()
            notebook_name = (
                (cfg or {})
                .get("destinations", {})
                .get("notebooklm", {})
                .get("notebook_name", "Mote Transcripts")
            )
            upload_transcript(effective_config_dir, written, notebook_name)
        except Exception as e:
            click.echo(
                f"Warning: NotebookLM upload failed: {e}. "
                "Run 'mote auth notebooklm' if session expired."
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
