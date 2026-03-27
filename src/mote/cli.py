"""Mote CLI entry point."""

import click

from mote import __version__
from mote.config import get_config_path, ensure_config, load_config, set_config_value


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
