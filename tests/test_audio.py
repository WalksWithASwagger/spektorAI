"""Tests for whisperforge_core.audio.

Pydub requires a real audio file to load, so we generate short silent WAV
fixtures programmatically and spill them to disk. WAV keeps the unit suite
independent of an external ffmpeg binary. Whisper API calls are mocked at the
client boundary — no network traffic.
"""

import json
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


def media_probe_fixture(
    *,
    duration="120.0",
    audio_codec="aac",
    sample_rate="48000",
    channels=2,
    video=False,
    container="wav",
):
    streams = []
    if video:
        streams.append({
            "codec_type": "video",
            "codec_name": "h264",
            "duration": duration,
        })
    streams.append({
        "codec_type": "audio",
        "codec_name": audio_codec,
        "sample_rate": sample_rate,
        "channels": channels,
        "duration": duration,
    })
    return {
        "streams": streams,
        "format": {"duration": duration, "format_name": container},
    }


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

    def test_transcribe_audio_detailed_uses_chunk_aware_text_path(self, tmp_path, monkeypatch):
        path = tmp_path / "large.wav"
        path.write_bytes(b"0" * (audio.CHUNK_THRESHOLD_BYTES + 1))
        calls = []

        def fake_large_file(file_path, progress=None):
            calls.append((file_path, progress))
            return "chunked transcript"

        def fail_single_chunk(_path):
            raise AssertionError("large detailed transcription should not call transcribe_chunk")

        monkeypatch.setattr(audio, "transcribe_large_file", fake_large_file)
        monkeypatch.setattr(audio, "transcribe_chunk", fail_single_chunk)

        details = audio.transcribe_audio_detailed(path, suffix=".wav")

        assert details.text == "chunked transcript"
        assert details.segments == []
        assert details.language is None
        assert calls == [(str(path), None)]

    def test_chunk_failure_yields_empty_string(self, silent_wav, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("whisper is down")

        client = MagicMock()
        client.audio.transcriptions.create.side_effect = boom
        monkeypatch.setattr(audio, "_openai", lambda: client)
        # Single-chunk call returns "" on failure rather than raising.
        assert audio.transcribe_chunk(silent_wav) == ""


class TestTranscriptionRouterPlan:
    def test_probe_media_uses_ffprobe_json(self, silent_wav, monkeypatch):
        probe = media_probe_fixture(
            duration="42.5",
            audio_codec="pcm_s16le",
            sample_rate="16000",
            channels=1,
        )
        result = MagicMock()
        result.stdout = json.dumps(probe)
        calls = {}

        def fake_run(argv, check, capture_output, text):
            calls["argv"] = argv
            calls["check"] = check
            calls["capture_output"] = capture_output
            calls["text"] = text
            return result

        monkeypatch.setattr(audio.subprocess, "run", fake_run)

        assert audio.probe_media(silent_wav) == probe
        assert calls["argv"][0] == "ffprobe"
        assert str(silent_wav) in calls["argv"]
        assert calls["check"] is True
        assert calls["capture_output"] is True
        assert calls["text"] is True

    def test_plan_does_not_probe_media_by_default(self, tmp_path, monkeypatch):
        path = tmp_path / "small.wav"
        path.write_bytes(b"audio")

        def fail_probe(_path):
            raise AssertionError("ffprobe should not run by default")

        monkeypatch.setattr(audio, "probe_media", fail_probe)

        plan = audio.build_transcription_plan(path, backend="openai")

        assert plan["strategy"] == "single_pass"
        assert plan["media"]["probe_available"] is False
        assert plan["normalization"]["commands"] == []

    def test_plan_inspects_media_when_requested(self, tmp_path, monkeypatch):
        path = tmp_path / "clip.mp4"
        path.write_bytes(b"video")
        probe = media_probe_fixture(video=True, container="mov,mp4,m4a,3gp,3g2,mj2")
        calls = []

        def fake_probe(source_path):
            calls.append(source_path)
            return probe

        monkeypatch.setattr(audio, "probe_media", fake_probe)

        plan = audio.build_transcription_plan(
            path,
            backend="openai",
            inspect_media=True,
        )

        assert calls == [path]
        assert plan["media"]["probe_available"] is True
        assert plan["media"]["has_video"] is True
        assert plan["normalization"]["required"] is True
        assert "ffprobe" in plan["privacy"]["local_processing_steps"]

    def test_transcription_capabilities_reports_whisperx_supports_segments(self):
        caps = audio.transcription_capabilities("whisperx")
        assert caps["backend"] == "whisperx"
        assert caps["supports_segments"] is True
        assert caps["supports_diarization"] is True
        assert caps["privacy_mode"] == "local"

    def test_plan_cloud_backend_receipt_shows_upload_and_billable_minutes(self, tmp_path):
        path = tmp_path / "meeting.wav"
        path.write_bytes(b"audio")
        probe = media_probe_fixture(
            duration="90.0",
            audio_codec="pcm_s16le",
            sample_rate="16000",
            channels=1,
        )

        plan = audio.build_transcription_plan(
            path,
            backend="openai",
            media_probe=probe,
        )

        assert plan["privacy"]["mode"] == "cloud"
        assert plan["privacy"]["audio_leaves_device"] is True
        assert plan["privacy"]["cloud_provider"] == "openai"
        assert plan["cost"]["provider_api_billable"] is True
        assert plan["cost"]["estimated_billable_minutes"] == 1.5
        assert plan["cost"]["pricing_review_required"] is True

    def test_plan_local_private_backend_receipt_stays_offline(self, tmp_path):
        path = tmp_path / "private.m4a"
        path.write_bytes(b"audio")
        probe = media_probe_fixture(
            duration="60.0",
            audio_codec="aac",
            sample_rate="44100",
            channels=2,
            container="mov,mp4,m4a,3gp,3g2,mj2",
        )

        plan = audio.build_transcription_plan(path, backend="mlx", media_probe=probe)

        assert plan["strategy"] == "single_pass"
        assert plan["privacy"]["mode"] == "local"
        assert plan["privacy"]["audio_leaves_device"] is False
        assert plan["privacy"]["cloud_provider"] is None
        assert plan["cost"]["provider_api_billable"] is False
        assert plan["normalization"]["required"] is False

    def test_plan_large_openai_uses_size_chunking(self, tmp_path):
        path = tmp_path / "large.wav"
        path.write_bytes(b"0" * (audio.CHUNK_THRESHOLD_BYTES + 1024))

        plan = audio.build_transcription_plan(path, backend="openai", chunker="size")

        assert plan["strategy"] == "chunked_size"
        assert "exceeds_chunk_threshold" in plan["reasons"]
        assert plan["requires_ffmpeg"] is False

    def test_plan_large_audio_fixture_adds_ffmpeg_normalization(self, tmp_path):
        path = tmp_path / "large.wav"
        path.write_bytes(b"0" * (audio.CHUNK_THRESHOLD_BYTES + 1024))
        normalized = tmp_path / "normalized.wav"
        probe = media_probe_fixture(
            duration="125.0",
            audio_codec="aac",
            sample_rate="48000",
            channels=2,
        )

        plan = audio.build_transcription_plan(
            path,
            backend="openai",
            chunker="size",
            media_probe=probe,
            normalized_audio_path=normalized,
        )

        assert plan["strategy"] == "chunked_size"
        assert plan["requires_ffmpeg"] is True
        assert plan["media"]["duration_seconds"] == 125.0
        assert plan["normalization"]["required"] is True
        assert plan["normalization"]["target"]["sample_rate_hz"] == 16000
        assert plan["normalization"]["target"]["channels"] == 1
        assert plan["normalization"]["output_path"] == str(normalized)
        assert plan["normalization"]["commands"][0]["argv"][0] == "ffmpeg"
        assert str(normalized) in plan["normalization"]["commands"][0]["argv"]
        assert "ffprobe" in plan["privacy"]["local_processing_steps"]
        assert "ffmpeg_normalization" in plan["privacy"]["local_processing_steps"]
        assert "chunking" in plan["privacy"]["local_processing_steps"]
        assert plan["privacy"]["temp_artifacts"] == ["normalized_audio", "chunks"]
        assert plan["cost"]["ffmpeg_compute_required"] is True

    def test_plan_large_whisperx_prefers_whole_file_without_vad(self, tmp_path):
        path = tmp_path / "large.wav"
        path.write_bytes(b"0" * (audio.CHUNK_THRESHOLD_BYTES + 1024))

        plan = audio.build_transcription_plan(path, backend="whisperx", chunker="size")

        assert plan["strategy"] == "whole_file"
        assert plan["capabilities"]["supports_segments"] is True
        assert plan["output_contract"]["timestamps"] == "segments"

    def test_plan_large_whisperx_uses_vad_when_requested(self, tmp_path):
        path = tmp_path / "large.wav"
        path.write_bytes(b"0" * (audio.CHUNK_THRESHOLD_BYTES + 1024))

        plan = audio.build_transcription_plan(path, backend="whisperx", chunker="vad")

        assert plan["strategy"] == "chunked_vad"

    def test_plan_whisperx_fixture_is_timestamped_and_diarization_capable(self, tmp_path):
        path = tmp_path / "interview.wav"
        path.write_bytes(b"0" * (audio.CHUNK_THRESHOLD_BYTES + 1024))
        probe = media_probe_fixture(
            duration="600.0",
            audio_codec="pcm_s16le",
            sample_rate="16000",
            channels=1,
        )

        plan = audio.build_transcription_plan(
            path,
            backend="whisperx",
            chunker="size",
            media_probe=probe,
        )

        assert plan["strategy"] == "whole_file"
        assert plan["output_contract"]["segments"] is True
        assert plan["output_contract"]["timestamps"] == "segments"
        assert plan["output_contract"]["diarization"]["capable"] is True
        assert plan["output_contract"]["diarization"]["requires_hf_token"] is True
        assert plan["privacy"]["mode"] == "local"
        assert plan["privacy"]["audio_leaves_device"] is False
        assert plan["cost"]["provider_api_billable"] is False
        assert plan["normalization"]["required"] is False

    def test_plan_video_source_flags_ffmpeg_requirement(self, tmp_path):
        path = tmp_path / "clip.mp4"
        path.write_bytes(b"video-bytes")

        plan = audio.build_transcription_plan(path, backend="openai")

        assert plan["requires_ffmpeg"] is True
        assert "video_source_requires_extraction" in plan["reasons"]
        assert plan["normalization"]["required"] is True
        assert plan["normalization"]["commands"][0]["argv"][0] == "ffmpeg"
