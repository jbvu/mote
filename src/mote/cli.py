"""Mote CLI entry point."""

import click

from mote import __version__


@click.group()
@click.version_option(version=__version__, prog_name="mote")
def cli():
    """Mote - Swedish meeting transcription."""
    pass


@cli.group()
def config():
    """View and edit configuration."""
    pass
