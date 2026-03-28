"""Transcription engine."""

import os
import tempfile
import wave
from pathlib import Path

import click
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

# 12 minutes at 16kHz = 11,520,000 frames
OPENAI_CHUNK_FRAMES = 12 * 60 * 16000
OPENAI_LIMIT_BYTES = 25 * 1024 * 1024


def get_wav_duration(wav_path: Path) -> float:
    """Return WAV duration in seconds."""
    with wave.open(str(wav_path)) as wf:
        return wf.getnframes() / wf.getframerate()


def transcribe_local(wav_path: Path, model_alias: str, language: str) -> str:
    """Transcribe using local KB-Whisper via faster-whisper."""
    from faster_whisper import WhisperModel

    from mote.models import MODELS, require_model_downloaded

    require_model_downloaded(model_alias)
    total_duration = get_wav_duration(wav_path)

    model = WhisperModel(MODELS[model_alias], device="cpu", compute_type="int8")
    segments_gen, info = model.transcribe(
        str(wav_path), language=language, log_progress=False
    )

    texts = []
    with Progress(
        TextColumn("Transcribing"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("", total=total_duration)
        for segment in segments_gen:
            texts.append(segment.text)
            progress.update(task, completed=segment.end)

    return "".join(texts).strip()


def transcribe_openai(wav_path: Path, language: str, api_key: str) -> str:
    """Transcribe using OpenAI Whisper API. Auto-chunks if file > 25MB."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    file_size = wav_path.stat().st_size

    if file_size <= OPENAI_LIMIT_BYTES:
        with Progress(SpinnerColumn(), TextColumn("Transcribing via OpenAI...")) as progress:
            progress.add_task("")
            with open(wav_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-1", file=f, language=language
                )
        return result.text

    # Chunked path
    chunks = _split_wav(wav_path, OPENAI_CHUNK_FRAMES)
    texts = []
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("")
            for i, chunk_path in enumerate(chunks):
                progress.update(
                    task,
                    description=f"Transcribing via OpenAI...  (chunk {i + 1}/{len(chunks)})",
                )
                with open(chunk_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model="whisper-1", file=f, language=language
                    )
                texts.append(result.text)
    finally:
        for chunk_path in chunks:
            chunk_path.unlink(missing_ok=True)

    return " ".join(t.strip() for t in texts if t.strip())


def _split_wav(wav_path: Path, chunk_frames: int) -> list[Path]:
    """Split WAV into chunks of chunk_frames frames. Returns temp file paths."""
    chunk_paths = []
    with wave.open(str(wav_path)) as src:
        params = src.getparams()
        total_frames = src.getnframes()

        offset = 0
        while offset < total_frames:
            n = min(chunk_frames, total_frames - offset)
            src.setpos(offset)
            data = src.readframes(n)

            fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="mote_chunk_")
            os.close(fd)
            with wave.open(tmp, "wb") as dst:
                dst.setparams(params)
                dst.writeframes(data)
            chunk_paths.append(Path(tmp))
            offset += n

    return chunk_paths


def transcribe_file(
    wav_path: Path,
    engine: str,
    language: str,
    model_alias: str,
    openai_api_key: str | None = None,
) -> str:
    """Dispatch to the appropriate engine and return transcript text."""
    if engine == "local":
        return transcribe_local(wav_path, model_alias, language)
    elif engine == "openai":
        if not openai_api_key:
            raise click.ClickException(
                "OpenAI API key not set.\n"
                "Set it with: mote config set api_keys.openai sk-...\n"
                "Or set OPENAI_API_KEY environment variable."
            )
        return transcribe_openai(wav_path, language, openai_api_key)
    else:
        raise click.ClickException(f"Unknown engine '{engine}'. Choose: local, openai")
