"""Mote configuration management."""

import os
import stat
import tomlkit
from pathlib import Path


def get_config_dir() -> Path:
    """Return the Mote config directory. Respects MOTE_HOME env var for testing."""
    return Path(os.environ.get("MOTE_HOME", str(Path.home() / ".mote")))


def get_config_path() -> Path:
    """Return path to config.toml."""
    return get_config_dir() / "config.toml"


def ensure_config() -> Path:
    """Create default config if it does not exist. Returns config path."""
    path = get_config_path()
    if not path.exists():
        _write_default_config(path)
    return path


def load_config() -> dict:
    """Load config from disk. Env vars override api_keys section (per D-05)."""
    path = ensure_config()
    with path.open() as f:
        cfg = tomlkit.load(f)
    # Env vars take priority over config file for API keys
    if "OPENAI_API_KEY" in os.environ:
        cfg.setdefault("api_keys", tomlkit.table())["openai"] = os.environ["OPENAI_API_KEY"]
    if "MISTRAL_API_KEY" in os.environ:
        cfg.setdefault("api_keys", tomlkit.table())["mistral"] = os.environ["MISTRAL_API_KEY"]
    return cfg


def set_config_value(key: str, value: str) -> None:
    """Set a dotted key in config file, e.g. 'general.language'.

    Preserves comments via tomlkit. Re-applies chmod 600 after write.
    """
    path = ensure_config()
    with path.open() as f:
        doc = tomlkit.load(f)
    parts = key.split(".")
    if len(parts) != 2:
        raise ValueError(f"Key must be in 'section.key' format, got: {key}")
    section, field = parts
    if section not in doc:
        raise KeyError(f"Unknown config section: {section}")
    if field not in doc[section]:
        raise KeyError(f"Unknown config key: {key}")
    doc[section][field] = value
    path.write_text(tomlkit.dumps(doc))
    path.chmod(0o600)


def _write_default_config(path: Path) -> None:
    """Write the default config template with comments (per D-06)."""
    doc = tomlkit.document()
    doc.add(tomlkit.comment("Mote configuration"))
    doc.add(tomlkit.nl())

    general = tomlkit.table()
    general.add(tomlkit.comment("Transcription language: sv (Swedish), no, da, fi, en"))
    general.add("language", "sv")
    doc.add("general", general)

    transcription = tomlkit.table()
    transcription.add(tomlkit.comment("Engine: local (KBLab KB-Whisper) or openai"))
    transcription.add("engine", "local")
    transcription.add(tomlkit.comment("Model size: tiny, base, small, medium, large"))
    transcription.add("model", "kb-whisper-medium")
    transcription.add(tomlkit.comment("Language: sv, no, da, fi, en"))
    transcription.add("language", "sv")
    doc.add("transcription", transcription)

    output_table = tomlkit.table()
    output_table.add(tomlkit.comment("Output formats: markdown, txt"))
    output_table.add("format", ["markdown", "txt"])
    output_table.add("dir", str(Path.home() / "Documents" / "mote"))
    doc.add("output", output_table)

    api_keys = tomlkit.table()
    api_keys.add(tomlkit.comment("API keys - environment variables take priority"))
    api_keys.add("openai", "")
    api_keys.add("mistral", "")
    doc.add("api_keys", api_keys)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc))
    path.chmod(0o600)
