"""CLI smoke tests for mote entry point."""

from click.testing import CliRunner
from mote.cli import cli


def test_help():
    """mote --help exits 0 and shows description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Mote" in result.output


def test_version():
    """mote --version exits 0 and shows version string."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_config_group_help():
    """mote config --help exits 0 and shows config description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "View and edit" in result.output
