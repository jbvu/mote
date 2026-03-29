"""NotebookLM API wrapper for Mote transcript uploads (experimental)."""

import asyncio
import json
from pathlib import Path

SESSION_FILE = "notebooklm_session.json"


def get_session_path(config_dir: Path) -> Path:
    """Return path to NotebookLM session file."""
    return config_dir / SESSION_FILE


def is_authenticated(config_dir: Path) -> bool:
    """Return True if session file exists (does not validate session)."""
    return get_session_path(config_dir).exists()


def run_login(session_path: Path) -> None:
    """Invoke notebooklm login with custom storage path.

    Raises RuntimeError if login command fails.
    """
    import subprocess

    result = subprocess.run(
        ["notebooklm", "login", "--storage", str(session_path)],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "NotebookLM login failed. Try running 'notebooklm login' manually."
        )
    session_path.chmod(0o600)


def _load_notebook_id(session_path: Path) -> str | None:
    """Read cached notebook ID from session file. Returns None if absent or invalid."""
    if not session_path.exists():
        return None
    try:
        data = json.loads(session_path.read_text())
        return data.get("notebook_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_notebook_id(session_path: Path, notebook_id: str) -> None:
    """Embed notebook_id in existing session file and set permissions 600."""
    data = json.loads(session_path.read_text())
    data["notebook_id"] = notebook_id
    session_path.write_text(json.dumps(data))
    session_path.chmod(0o600)


async def _get_or_create_notebook(client, notebook_name: str) -> str:
    """Return notebook ID by name, creating if absent."""
    notebooks = await client.notebooks.list()
    for nb in notebooks:
        if nb.title == notebook_name:
            return nb.id
    nb = await client.notebooks.create(notebook_name)
    return nb.id


async def _upload_async(
    session_path: Path, notebook_name: str, title: str, content: str
) -> None:
    """Async inner: get/create notebook and upload text source."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage(str(session_path)) as client:
        notebook_id = _load_notebook_id(session_path)
        if not notebook_id:
            notebook_id = await _get_or_create_notebook(client, notebook_name)
            _save_notebook_id(session_path, notebook_id)
        try:
            await client.sources.add_text(notebook_id, title, content)
        except Exception:
            # Notebook ID may be stale — retry with fresh lookup (Pitfall 4)
            notebook_id = await _get_or_create_notebook(client, notebook_name)
            _save_notebook_id(session_path, notebook_id)
            await client.sources.add_text(notebook_id, title, content)


def upload_transcript(
    config_dir: Path, files: list[Path], notebook_name: str
) -> None:
    """Upload markdown transcript to NotebookLM.

    Only uploads the .md file (D-06). Raises RuntimeError if not authenticated.
    """
    session_path = get_session_path(config_dir)
    if not session_path.exists():
        raise RuntimeError(
            "Not authenticated with NotebookLM. Run: mote auth notebooklm"
        )

    md_files = [f for f in files if f.suffix == ".md"]
    if not md_files:
        return  # No markdown file in this upload set — silent no-op

    for md_file in md_files:
        title = md_file.stem  # e.g. "2026-03-29-standup"
        content = md_file.read_text()
        asyncio.run(_upload_async(session_path, notebook_name, title, content))
