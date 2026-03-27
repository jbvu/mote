"""Mote CLI entry point."""

import click

from mote import __version__
from mote.config import get_config_dir, get_config_path, ensure_config, load_config, set_config_value
from mote.audio import (
    find_blackhole_device,
    record_session,
    is_recording_active,
    find_orphan_recordings,
)


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
def record_command():
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
