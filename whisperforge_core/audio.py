"""Audio chunking and Whisper transcription.

Pure-logic: no Streamlit imports. UI layers pass a progress_callback if they
want to surface progress to the user.

Large files (>20MB) are split into ~25MB chunks (dynamically sized, capped at
20 chunks) because the Whisper API rejects files >25MB. Chunks are transcribed
sequentially and concatenated.
"""

import hashlib
import math
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from openai import OpenAI
from pydub import AudioSegment

from . import cache
from .config import (
    CHUNKER,
    DEFAULT_CHUNK_TARGET_MB,
    MLX_WHISPER_MODEL,
    OPENAI_API_KEY,
    TRANSCRIPTION_BACKEND,
    WHISPER_MODEL,
    WHISPERX_COMPUTE,
    WHISPERX_DEVICE,
    WHISPERX_DIARIZATION,
    WHISPERX_HF_TOKEN,
    WHISPERX_MODEL,
)
from .logging import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int, str], None]  # (current, total, label) -> None


@dataclass
class TranscriptionDetails:
    """Rich transcription result. Returned by transcribe_audio_detailed().

    Non-rich backends (OpenAI, MLX, whisper.cpp) produce empty ``segments`` —
    callers should treat the absence of segments as "timestamps unavailable"
    and fall back to text-only behavior.
    """

    text: str
    # [{"start": float seconds, "end": float seconds, "text": str,
    #   "speaker": Optional[str]}]
    segments: List[dict] = field(default_factory=list)
    language: Optional[str] = None

CHUNK_THRESHOLD_BYTES = 20 * 1024 * 1024
MIN_CHUNK_LENGTH_MS = 5_000
MAX_CHUNKS = 20


def _openai() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)


def chunk_audio(
    audio_path: str | Path,
    target_size_mb: int = DEFAULT_CHUNK_TARGET_MB,
    progress: Optional[ProgressCallback] = None,
) -> Tuple[List[str], Optional[str]]:
    """Split an audio file into chunks of roughly ``target_size_mb`` MB.

    Dispatches to the VAD-based chunker when CHUNKER=vad, else uses the
    fixed-size byte-count chunker (default; preserves pre-VAD behavior).

    Returns (chunk_file_paths, temp_dir). Caller is responsible for cleaning up
    the temp_dir once done. On failure returns ([], None) and logs.
    """
    if (CHUNKER or "").lower() == "vad":
        try:
            return _chunk_audio_vad(audio_path, target_size_mb, progress)
        except Exception as e:
            logger.warning("VAD chunker failed (%s) — falling back to size-based", e)

    return _chunk_audio_size(audio_path, target_size_mb, progress)


def _chunk_audio_size(
    audio_path: str | Path,
    target_size_mb: int,
    progress: Optional[ProgressCallback],
) -> Tuple[List[str], Optional[str]]:
    """Size-based chunker: fixed ms-length chunks, regardless of content."""
    try:
        audio = AudioSegment.from_file(str(audio_path))
    except Exception as e:
        logger.error("Failed to load audio %s: %s", audio_path, e)
        return [], None

    file_size = os.path.getsize(audio_path)
    total_chunks = max(1, math.ceil(file_size / (target_size_mb * 1024 * 1024)))
    if total_chunks > MAX_CHUNKS:
        target_size_mb = math.ceil(file_size / (MAX_CHUNKS * 1024 * 1024))
        total_chunks = MAX_CHUNKS

    chunk_length_ms = max(len(audio) // total_chunks, MIN_CHUNK_LENGTH_MS)
    temp_dir = tempfile.mkdtemp(prefix="whisperforge_chunks_")
    chunks: List[str] = []

    for i in range(0, len(audio), chunk_length_ms):
        piece = audio[i : i + chunk_length_ms]
        if len(piece) < MIN_CHUNK_LENGTH_MS and len(chunks) > 0:
            # Attach any trailing sliver to the last chunk instead of dropping it.
            continue
        idx = i // chunk_length_ms
        chunk_path = os.path.join(temp_dir, f"chunk_{idx}.mp3")
        piece.export(chunk_path, format="mp3")
        chunks.append(chunk_path)
        if progress:
            progress(idx + 1, total_chunks, "chunking")

    return chunks, temp_dir


def _chunk_audio_vad(
    audio_path: str | Path,
    target_size_mb: int,
    progress: Optional[ProgressCallback],
) -> Tuple[List[str], Optional[str]]:
    """VAD-based chunker: cuts on silences, drops silent segments.

    Uses Silero VAD to find speech timestamps, then groups adjacent speech
    segments into chunks that each stay under target_size_mb. Speech between
    chunks is contiguous (no silence gaps within a chunk), and silences
    between chunks drop out of the pipeline entirely — less audio sent to
    the transcription model, no mid-word cuts.
    """
    import numpy as np
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad

    audio = AudioSegment.from_file(str(audio_path))
    # Silero VAD wants mono float32 at 16 kHz.
    probe = audio.set_channels(1).set_frame_rate(16000)
    samples = np.array(probe.get_array_of_samples()).astype(np.float32) / 32768.0
    wav = torch.from_numpy(samples)

    model = load_silero_vad()
    speech = get_speech_timestamps(wav, model, sampling_rate=16000, return_seconds=True)
    if not speech:
        logger.info("VAD found no speech — falling back to size-based")
        return _chunk_audio_size(audio_path, target_size_mb, progress)

    logger.info("VAD found %d speech segments", len(speech))

    # Estimate bytes-per-second from the full source to budget chunks.
    file_size = os.path.getsize(audio_path)
    total_sec = max(len(audio) / 1000.0, 0.001)
    bytes_per_sec = file_size / total_sec
    target_sec = (target_size_mb * 1024 * 1024) / max(bytes_per_sec, 1)

    # Greedy packing: accumulate speech segments into groups that each span
    # at most target_sec of source audio.
    groups: List[List[dict]] = [[]]
    group_start = speech[0]["start"]
    for seg in speech:
        span = seg["end"] - group_start
        if groups[-1] and span > target_sec:
            groups.append([seg])
            group_start = seg["start"]
        else:
            groups[-1].append(seg)
            if len(groups[-1]) == 1:
                group_start = seg["start"]

    temp_dir = tempfile.mkdtemp(prefix="whisperforge_chunks_")
    chunks: List[str] = []
    total = len(groups)
    for idx, group in enumerate(groups):
        # Concatenate the underlying audio pieces (from the FULL-quality source,
        # not the 16 kHz mono probe) with tiny pads between to avoid clipping.
        piece = AudioSegment.empty()
        for seg in group:
            start_ms = int(seg["start"] * 1000)
            end_ms = int(seg["end"] * 1000)
            piece += audio[start_ms:end_ms]
        if len(piece) < MIN_CHUNK_LENGTH_MS:
            continue
        chunk_path = os.path.join(temp_dir, f"chunk_{idx}.mp3")
        piece.export(chunk_path, format="mp3")
        chunks.append(chunk_path)
        if progress:
            progress(idx + 1, total, "chunking (vad)")

    return chunks, temp_dir


def _transcribe_chunk_openai(chunk_path: str | Path) -> str:
    with open(chunk_path, "rb") as f:
        result = _openai().audio.transcriptions.create(model=WHISPER_MODEL, file=f)
    return result.text


def _transcribe_chunk_mlx(chunk_path: str | Path) -> str:
    # Imported lazily so the cloud path doesn't pay mlx startup cost.
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(chunk_path),
        path_or_hf_repo=MLX_WHISPER_MODEL,
    )
    return result.get("text", "").strip()


# WhisperX is heavy to load (whisper model + alignment model + maybe pyannote).
# Cache the loaded models per-process so repeated calls don't pay startup cost.
_WHISPERX_CACHE: dict = {}


def _whisperx_detailed(chunk_path: str | Path) -> TranscriptionDetails:
    """Shared WhisperX workhorse — ASR + alignment + optional diarization,
    returning the full rich result. Both ``_transcribe_chunk_whisperx`` (text
    path) and ``transcribe_audio_detailed`` (timestamp path) route through
    this so the two stay in lock-step.
    """
    import whisperx  # lazy-load; adds ~5s to cold start

    device = WHISPERX_DEVICE
    compute = WHISPERX_COMPUTE if WHISPERX_COMPUTE != "default" else (
        "float16" if device == "cuda" else "int8"
    )

    # 1. Load (and cache) the ASR model.
    asr_model = _WHISPERX_CACHE.get(("asr", WHISPERX_MODEL, device, compute))
    if asr_model is None:
        asr_model = whisperx.load_model(WHISPERX_MODEL, device, compute_type=compute)
        _WHISPERX_CACHE[("asr", WHISPERX_MODEL, device, compute)] = asr_model

    audio_array = whisperx.load_audio(str(chunk_path))
    result = asr_model.transcribe(audio_array, batch_size=8)

    # 2. Align for word-level timestamps.
    lang = result.get("language") or "en"
    align_key = ("align", lang, device)
    align_entry = _WHISPERX_CACHE.get(align_key)
    if align_entry is None:
        try:
            model_a, meta = whisperx.load_align_model(language_code=lang, device=device)
            align_entry = (model_a, meta)
            _WHISPERX_CACHE[align_key] = align_entry
        except Exception as e:
            logger.warning("whisperx align model load failed for %s: %s", lang, e)
            align_entry = None

    if align_entry is not None:
        try:
            model_a, meta = align_entry
            result = whisperx.align(
                result["segments"], model_a, meta, audio_array, device,
                return_char_alignments=False,
            )
        except Exception as e:
            logger.warning("whisperx align failed: %s", e)

    # 3. Optional speaker diarization via pyannote.
    if WHISPERX_DIARIZATION and WHISPERX_HF_TOKEN:
        try:
            diar = _WHISPERX_CACHE.get(("diar", device))
            if diar is None:
                diar = whisperx.DiarizationPipeline(
                    use_auth_token=WHISPERX_HF_TOKEN, device=device,
                )
                _WHISPERX_CACHE[("diar", device)] = diar
            diarize_segments = diar(audio_array)
            result = whisperx.assign_word_speakers(diarize_segments, result)
        except Exception as e:
            logger.warning("whisperx diarization failed: %s", e)

    raw_segments = result.get("segments", []) if isinstance(result, dict) else result

    # Normalize segments into our TranscriptionDetails shape.
    normalized: List[dict] = []
    for seg in raw_segments:
        text_ = (seg.get("text") or "").strip()
        if not text_:
            continue
        normalized.append({
            "start": float(seg.get("start", 0.0)),
            "end": float(seg.get("end", 0.0)),
            "text": text_,
            "speaker": seg.get("speaker"),
        })

    # Assemble the plain-text rendering (diarization-prefixed if we have speakers).
    if WHISPERX_DIARIZATION and normalized and any(s.get("speaker") for s in normalized):
        out_lines: List[str] = []
        prev = None
        for s in normalized:
            spk = s.get("speaker") or "SPEAKER_??"
            if spk != prev:
                out_lines.append(f"[{spk}] {s['text']}")
                prev = spk
            else:
                out_lines[-1] += f" {s['text']}"
        text = "\n".join(out_lines)
    else:
        text = " ".join(s["text"] for s in normalized).strip()

    return TranscriptionDetails(text=text, segments=normalized, language=lang)


def _transcribe_chunk_whisperx(chunk_path: str | Path) -> str:
    """Transcribe with faster-whisper + wav2vec2 forced alignment via WhisperX.

    Returns plain text (with [SPEAKER_XX] prefixes when diarization is on).
    Use ``transcribe_audio_detailed()`` instead when you also want the
    per-segment start/end timestamps for downstream timestamp-aware features
    (chapters, quote extraction, jump-to-moment links).
    """
    return _whisperx_detailed(chunk_path).text


def _transcribe_chunk_whisper_cpp(chunk_path: str | Path) -> str:
    # Shells out to the whisper.cpp `whisper-cli` binary, which writes a txt
    # file next to the input. Assumes whisper-cli is on PATH.
    import subprocess

    model_path = os.getenv("WHISPER_CPP_MODEL", "")
    if not model_path:
        raise RuntimeError(
            "whisper_cpp backend requires WHISPER_CPP_MODEL env var "
            "(path to a ggml model, e.g. ggml-base.en.bin)"
        )
    out_base = str(chunk_path) + ".wf"
    subprocess.run(
        [
            "whisper-cli", "-m", model_path, "-f", str(chunk_path),
            "-otxt", "-of", out_base, "-nt",
        ],
        check=True, capture_output=True,
    )
    txt_path = out_base + ".txt"
    try:
        with open(txt_path) as f:
            return f.read().strip()
    finally:
        try:
            os.remove(txt_path)
        except OSError:
            pass


def transcribe_chunk(chunk_path: str | Path) -> str:
    """Transcribe one audio chunk via the configured backend.

    Backend is selected by the TRANSCRIPTION_BACKEND env var. Returns empty
    string on failure rather than raising, because the chunked pipeline is
    tolerant of a missing piece — better to lose 30 s of text than the whole
    transcript.
    """
    backend = (TRANSCRIPTION_BACKEND or "openai").lower()
    try:
        if backend == "mlx":
            return _transcribe_chunk_mlx(chunk_path)
        if backend == "whisperx":
            return _transcribe_chunk_whisperx(chunk_path)
        if backend == "whisper_cpp":
            return _transcribe_chunk_whisper_cpp(chunk_path)
        return _transcribe_chunk_openai(chunk_path)
    except Exception as e:
        logger.warning(
            "Failed to transcribe chunk %s via %s: %s", chunk_path, backend, e
        )
        return ""


def transcribe_large_file(
    file_path: str | Path,
    progress: Optional[ProgressCallback] = None,
) -> str:
    """Chunk and transcribe a large audio file. Cleans up chunks + temp dir."""
    chunks, temp_dir = chunk_audio(file_path, progress=progress)
    if not chunks:
        return ""

    transcripts: List[str] = []
    total = len(chunks)
    try:
        for i, chunk_path in enumerate(chunks):
            if progress:
                progress(i + 1, total, "transcribing")
            transcripts.append(transcribe_chunk(chunk_path))
            try:
                os.remove(chunk_path)
            except OSError:
                pass
    finally:
        if temp_dir:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

    return " ".join(t for t in transcripts if t)


def transcribe_audio_detailed(
    source: str | Path | bytes,
    suffix: str = ".mp3",
) -> TranscriptionDetails:
    """Rich transcription: returns text + per-segment timestamps + language.

    Only the WhisperX backend populates segments today. All other backends
    return a ``TranscriptionDetails`` with just ``text`` set and empty
    ``segments`` — downstream code should check ``details.segments`` and
    fall back to text-only behavior when empty.

    Skips the chunker/cache wrapping that ``transcribe_audio()`` applies. Meant
    for short-to-medium audio where whole-file transcription is fine (WhisperX
    handles long audio internally via its own VAD). For very long files on
    non-WhisperX backends, call ``transcribe_audio()`` (text-only) instead.
    """
    # Resolve source → temp file path.
    owns_tmp = False
    if isinstance(source, (str, Path)):
        audio_path = str(source)
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(source)
            audio_path = tmp.name
            owns_tmp = True

    backend = (TRANSCRIPTION_BACKEND or "openai").lower()
    try:
        if backend == "whisperx":
            return _whisperx_detailed(audio_path)
        # Non-rich backends: fall through to the text path. No segments.
        text = transcribe_chunk(audio_path)
        return TranscriptionDetails(text=text, segments=[], language=None)
    except Exception as e:
        logger.warning("transcribe_audio_detailed failed (%s): %s", backend, e)
        return TranscriptionDetails(text="", segments=[], language=None)
    finally:
        if owns_tmp:
            try:
                os.remove(audio_path)
            except OSError:
                pass


def transcribe_audio(
    source: str | Path | bytes,
    suffix: str = ".mp3",
    progress: Optional[ProgressCallback] = None,
) -> str:
    """Transcribe audio from either a file path or raw bytes (e.g. uploaded file).

    Routes small files straight to Whisper and large ones through chunking.
    When WHISPERFORGE_CACHE=1, the result is cached by
    sha256(audio_bytes) + whisper_model so repeated runs on the same file
    skip the API call entirely.
    """
    owns_tmp = False
    if isinstance(source, (str, Path)):
        audio_path = str(source)
        content_hash = cache.file_hash(audio_path)
    else:
        # Assume bytes-like (e.g. Streamlit UploadedFile.getvalue())
        content_hash = hashlib.sha256(source).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(source)
            audio_path = tmp.name
            owns_tmp = True

    key = cache.make_key([content_hash, "transcribe", WHISPER_MODEL])

    def _compute() -> str:
        try:
            file_size = os.path.getsize(audio_path)
            if file_size > CHUNK_THRESHOLD_BYTES:
                return transcribe_large_file(audio_path, progress=progress)
            # Small-file fast path — single call through the active backend.
            return transcribe_chunk(audio_path)
        finally:
            if owns_tmp:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

    return cache.cached_or_compute(key, _compute)
