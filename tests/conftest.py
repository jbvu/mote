import pytest
from pathlib import Path


@pytest.fixture
def mote_home(tmp_path, monkeypatch):
    """Isolated ~/.mote/ equivalent for tests.

    Sets MOTE_HOME env var so config.py never touches real ~/.mote/.
    """
    home = tmp_path / ".mote"
    home.mkdir()
    monkeypatch.setenv("MOTE_HOME", str(home))
    return home
