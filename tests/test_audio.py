"""Tests for whisperforge_core.audio.

Pydub requires a real audio file to load, so we generate short silent WAV
fixtures programmatically and spill them to disk. WAV keeps the unit suite
independent of an external ffmpeg binary. Whisper API calls are mocked at the
client boundary — no network traffic.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydub import AudioSegment

from whisperforge_core import audio


@pytest.fixture
def silent_wav(tmp_path):
    """A 3-second silent WAV suitable for pydub's AudioSegment.from_file."""
    path = tmp_path / "silent.wav"
    AudioSegment.silent(duration=3_000).export(str(path), format="wav")
    return path


@pytest.fixture
def long_silent_wav(tmp_path):
    """A 2-minute silent WAV large enough to trigger chunking at size thresholds."""
    path = tmp_path / "long.wav"
    AudioSegment.silent(duration=120_000).export(str(path), format="wav")
    return path


@pytest.fixture
def mock_openai(monkeypatch):
    """Stub the OpenAI Whisper transcription client."""
    response = MagicMock()
    response.text = "transcribed text"
    client = MagicMock()
    client.audio.transcriptions.create.return_value = response
    monkeypatch.setattr(audio, "_openai", lambda: client)
    return client


class TestChunkAudio:
    def test_small_file_yields_single_chunk(self, silent_wav):
        chunks, tmp_dir = audio.chunk_audio(silent_wav, target_size_mb=25)
        try:
            assert len(chunks) == 1
            assert all(Path(c).exists() for c in chunks)
        finally:
            import shutil
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_chunks_are_under_max_count(self, long_silent_wav):
        # Tight target_size forces the cap at MAX_CHUNKS.
        chunks, tmp_dir = audio.chunk_audio(long_silent_wav, target_size_mb=1)
        try:
            assert len(chunks) <= audio.MAX_CHUNKS
        finally:
            import shutil
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_nonexistent_file_returns_empty(self, tmp_path):
        chunks, tmp_dir = audio.chunk_audio(tmp_path / "missing.mp3")
        assert chunks == []
        assert tmp_dir is None


class TestTranscribe:
    def test_transcribe_chunk_calls_whisper(self, silent_wav, mock_openai):
        text = audio.transcribe_chunk(silent_wav)
        assert text == "transcribed text"
        mock_openai.audio.transcriptions.create.assert_called_once()

    def test_transcribe_audio_path(self, silent_wav, mock_openai):
        text = audio.transcribe_audio(str(silent_wav))
        assert text == "transcribed text"

    def test_transcribe_audio_bytes_creates_temp(self, silent_wav, mock_openai):
        raw = silent_wav.read_bytes()
        text = audio.transcribe_audio(raw, suffix=".wav")
        assert text == "transcribed text"

    def test_chunk_failure_yields_empty_string(self, silent_wav, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("whisper is down")

        client = MagicMock()
        client.audio.transcriptions.create.side_effect = boom
        monkeypatch.setattr(audio, "_openai", lambda: client)
        # Single-chunk call returns "" on failure rather than raising.
        assert audio.transcribe_chunk(silent_wav) == ""
