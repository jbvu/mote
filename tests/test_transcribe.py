"""Unit tests for mote transcription module."""

import wave as wave_mod
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import click
import pytest

from mote.transcribe import (
    get_wav_duration,
    transcribe_local,
    transcribe_openai,
    transcribe_file,
    _split_wav,
    OPENAI_CHUNK_FRAMES,
    OPENAI_LIMIT_BYTES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav(path: Path, duration_sec: float = 1.0) -> Path:
    """Write a valid 16kHz mono 16-bit WAV with silence for the given duration."""
    n_frames = int(16000 * duration_sec)
    data = b"\x00\x00" * n_frames  # silence
    with wave_mod.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(data)
    return path


def _make_segment(text: str, end: float) -> MagicMock:
    """Build a mock faster-whisper Segment-like object."""
    seg = MagicMock()
    seg.text = text
    seg.end = end
    return seg


# ---------------------------------------------------------------------------
# get_wav_duration
# ---------------------------------------------------------------------------


def test_get_wav_duration(tmp_path):
    """get_wav_duration returns correct seconds for a 16kHz mono WAV."""
    wav = _make_wav(tmp_path / "test.wav", duration_sec=5.0)
    duration = get_wav_duration(wav)
    assert abs(duration - 5.0) < 0.01


def test_get_wav_duration_short(tmp_path):
    """get_wav_duration works for very short clips (0.5s)."""
    wav = _make_wav(tmp_path / "short.wav", duration_sec=0.5)
    duration = get_wav_duration(wav)
    assert abs(duration - 0.5) < 0.01


# ---------------------------------------------------------------------------
# transcribe_local
# ---------------------------------------------------------------------------


@patch("mote.transcribe.Progress")
@patch("faster_whisper.WhisperModel")
@patch("mote.models.require_model_downloaded")
def test_transcribe_local_calls_model(mock_require, mock_whisper_cls, mock_progress_cls, tmp_path):
    """transcribe_local calls WhisperModel with device=cpu, compute_type=int8, and correct repo ID."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=2.0)

    seg1 = _make_segment("Hej världen", 1.0)
    seg2 = _make_segment(" från Sverige", 2.0)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([seg1, seg2]), MagicMock())
    mock_whisper_cls.return_value = mock_model

    # Mock Progress context manager
    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_progress.add_task.return_value = 0

    result = transcribe_local(wav, model_alias="medium", language="sv")

    # WhisperModel called with KBLab repo ID and cpu/int8
    mock_whisper_cls.assert_called_once_with(
        "KBLab/kb-whisper-medium", device="cpu", compute_type="int8"
    )
    # transcribe called with str path, language, log_progress=False
    mock_model.transcribe.assert_called_once_with(
        str(wav), language="sv", log_progress=False
    )
    assert result == "Hej världen från Sverige"


@patch("mote.transcribe.Progress")
@patch("faster_whisper.WhisperModel")
@patch("mote.models.require_model_downloaded")
def test_transcribe_local_returns_joined_text(mock_require, mock_whisper_cls, mock_progress_cls, tmp_path):
    """transcribe_local returns stripped joined segment text."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=3.0)

    segments = [
        _make_segment("Segment one.", 1.0),
        _make_segment(" Segment two.", 2.0),
        _make_segment(" Segment three.", 3.0),
    ]
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(segments), MagicMock())
    mock_whisper_cls.return_value = mock_model

    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_progress.add_task.return_value = 0

    result = transcribe_local(wav, model_alias="medium", language="sv")
    assert result == "Segment one. Segment two. Segment three."


@patch("mote.models.require_model_downloaded")
def test_transcribe_local_no_model(mock_require, tmp_path):
    """When require_model_downloaded raises ClickException, transcribe_local propagates it."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)
    mock_require.side_effect = click.ClickException("Model 'large' is not downloaded.")

    with pytest.raises(click.ClickException, match="is not downloaded"):
        transcribe_local(wav, model_alias="large", language="sv")


@patch("mote.transcribe.Progress")
@patch("faster_whisper.WhisperModel")
@patch("mote.models.require_model_downloaded")
def test_transcribe_local_progress(mock_require, mock_whisper_cls, mock_progress_cls, tmp_path):
    """transcribe_local calls progress.update with segment.end values."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=3.0)

    seg1 = _make_segment("First", 1.5)
    seg2 = _make_segment(" Second", 3.0)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([seg1, seg2]), MagicMock())
    mock_whisper_cls.return_value = mock_model

    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)
    task_id = 42
    mock_progress.add_task.return_value = task_id

    transcribe_local(wav, model_alias="medium", language="sv")

    # progress.update called once per segment with completed=segment.end
    calls = mock_progress.update.call_args_list
    assert len(calls) == 2
    assert calls[0] == call(task_id, completed=1.5)
    assert calls[1] == call(task_id, completed=3.0)


# ---------------------------------------------------------------------------
# transcribe_openai
# ---------------------------------------------------------------------------


@patch("mote.transcribe.Progress")
@patch("openai.OpenAI")
def test_transcribe_openai_calls_api(mock_openai_cls, mock_progress_cls, tmp_path):
    """transcribe_openai creates OpenAI client and calls audio.transcriptions.create."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.audio.transcriptions.create.return_value = MagicMock(text="Hej Sverige")

    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_progress.add_task.return_value = 0

    result = transcribe_openai(wav, language="sv", api_key="sk-test-key")

    mock_openai_cls.assert_called_once_with(api_key="sk-test-key")
    create_call = mock_client.audio.transcriptions.create
    assert create_call.called
    call_kwargs = create_call.call_args
    assert call_kwargs.kwargs.get("model") == "whisper-1" or call_kwargs[1].get("model") == "whisper-1"
    assert result == "Hej Sverige"


@patch("mote.transcribe.Progress")
@patch("openai.OpenAI")
def test_transcribe_openai_language_passed(mock_openai_cls, mock_progress_cls, tmp_path):
    """transcribe_openai passes language param to API call."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.audio.transcriptions.create.return_value = MagicMock(text="Hei Norge")

    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)

    transcribe_openai(wav, language="no", api_key="sk-test")

    call_kwargs = mock_client.audio.transcriptions.create.call_args
    assert "language" in str(call_kwargs)


@patch("mote.transcribe._split_wav")
@patch("mote.transcribe.Progress")
@patch("openai.OpenAI")
def test_transcribe_openai_chunking(mock_openai_cls, mock_progress_cls, mock_split, tmp_path):
    """For a WAV > 25MB, transcribe_openai splits into chunks and makes multiple API calls."""
    # Create a large WAV (> 25MB): 830s * 16000 * 2 bytes = 26,560,000 bytes > 26,214,400 (25MB)
    wav = _make_wav(tmp_path / "big.wav", duration_sec=830)

    chunk1 = _make_wav(tmp_path / "chunk1.wav", duration_sec=1.0)
    chunk2 = _make_wav(tmp_path / "chunk2.wav", duration_sec=1.0)
    mock_split.return_value = [chunk1, chunk2]

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.audio.transcriptions.create.side_effect = [
        MagicMock(text="Del ett"),
        MagicMock(text="Del tva"),
    ]

    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_progress.add_task.return_value = 0

    result = transcribe_openai(wav, language="sv", api_key="sk-test")

    mock_split.assert_called_once_with(wav, OPENAI_CHUNK_FRAMES)
    assert mock_client.audio.transcriptions.create.call_count == 2
    assert result == "Del ett Del tva"


@patch("mote.transcribe._split_wav")
@patch("mote.transcribe.Progress")
@patch("openai.OpenAI")
def test_transcribe_openai_cleans_chunks(mock_openai_cls, mock_progress_cls, mock_split, tmp_path):
    """Temp chunk files are deleted even if an API call fails."""
    wav = _make_wav(tmp_path / "big.wav", duration_sec=830)

    chunk1 = _make_wav(tmp_path / "chunk1.wav", duration_sec=1.0)
    chunk2 = _make_wav(tmp_path / "chunk2.wav", duration_sec=1.0)
    mock_split.return_value = [chunk1, chunk2]

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    # First call succeeds, second fails
    mock_client.audio.transcriptions.create.side_effect = [
        MagicMock(text="First chunk"),
        RuntimeError("Network error"),
    ]

    mock_progress = MagicMock()
    mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress)
    mock_progress_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_progress.add_task.return_value = 0

    with pytest.raises(RuntimeError, match="Network error"):
        transcribe_openai(wav, language="sv", api_key="sk-test")

    # Both chunk files must be deleted despite the exception
    assert not chunk1.exists()
    assert not chunk2.exists()


# ---------------------------------------------------------------------------
# _split_wav
# ---------------------------------------------------------------------------


def test_split_wav(tmp_path):
    """_split_wav creates correct number of chunk files with valid WAV headers."""
    # 3 seconds of audio at 16kHz = 48000 frames
    # Split at 20000 frames => 3 chunks (20000, 20000, 8000)
    wav = _make_wav(tmp_path / "source.wav", duration_sec=3.0)
    chunks = _split_wav(wav, chunk_frames=20000)

    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk.exists()
        # Each chunk must be a valid WAV
        with wave_mod.open(str(chunk)) as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 16000
            assert wf.getsampwidth() == 2

    total_frames = sum(
        wave_mod.open(str(c)).getnframes() for c in chunks
    )
    assert total_frames == 48000  # 3s * 16000


def test_split_wav_single_chunk(tmp_path):
    """_split_wav with large chunk_frames returns single chunk for short audio."""
    wav = _make_wav(tmp_path / "source.wav", duration_sec=1.0)
    chunks = _split_wav(wav, chunk_frames=100000)

    assert len(chunks) == 1
    with wave_mod.open(str(chunks[0])) as wf:
        assert wf.getnframes() == 16000


def test_split_wav_cleanup_on_split(tmp_path):
    """Chunk files from _split_wav are real files that can be cleaned up."""
    wav = _make_wav(tmp_path / "source.wav", duration_sec=2.0)
    chunks = _split_wav(wav, chunk_frames=16000)

    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.exists()
        chunk.unlink()  # clean up
    for chunk in chunks:
        assert not chunk.exists()


# ---------------------------------------------------------------------------
# transcribe_file dispatcher
# ---------------------------------------------------------------------------


@patch("mote.transcribe.transcribe_local")
def test_transcribe_file_dispatches_local(mock_local, tmp_path):
    """transcribe_file(engine='local') calls transcribe_local."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)
    mock_local.return_value = "Transkript"

    result = transcribe_file(wav, engine="local", language="sv", model_alias="medium")

    mock_local.assert_called_once_with(wav, "medium", "sv")
    assert result == "Transkript"


@patch("mote.transcribe.transcribe_openai")
def test_transcribe_file_dispatches_openai(mock_openai, tmp_path):
    """transcribe_file(engine='openai') calls transcribe_openai with api_key."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)
    mock_openai.return_value = "Via OpenAI"

    result = transcribe_file(
        wav, engine="openai", language="sv", model_alias="medium", openai_api_key="sk-key"
    )

    mock_openai.assert_called_once_with(wav, "sv", "sk-key")
    assert result == "Via OpenAI"


def test_transcribe_openai_no_key(tmp_path):
    """transcribe_file with engine='openai' and no api_key raises ClickException."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)

    with pytest.raises(click.ClickException, match="OpenAI API key not set"):
        transcribe_file(wav, engine="openai", language="sv", model_alias="medium", openai_api_key=None)


def test_transcribe_openai_no_key_empty_string(tmp_path):
    """transcribe_file with engine='openai' and empty string api_key raises ClickException."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)

    with pytest.raises(click.ClickException, match="OpenAI API key not set"):
        transcribe_file(wav, engine="openai", language="sv", model_alias="medium", openai_api_key="")


def test_transcribe_file_unknown_engine(tmp_path):
    """transcribe_file(engine='foo') raises ClickException containing 'Unknown engine'."""
    wav = _make_wav(tmp_path / "rec.wav", duration_sec=1.0)

    with pytest.raises(click.ClickException, match="Unknown engine"):
        transcribe_file(wav, engine="foo", language="sv", model_alias="medium")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants():
    """Verify module-level constants have the expected values."""
    assert OPENAI_CHUNK_FRAMES == 12 * 60 * 16000
    assert OPENAI_LIMIT_BYTES == 25 * 1024 * 1024
