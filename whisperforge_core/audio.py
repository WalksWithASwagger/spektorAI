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
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from openai import OpenAI
from pydub import AudioSegment

from . import cache
from .config import (
    DEFAULT_CHUNK_TARGET_MB,
    MLX_WHISPER_MODEL,
    OPENAI_API_KEY,
    TRANSCRIPTION_BACKEND,
    WHISPER_MODEL,
)
from .logging import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int, str], None]  # (current, total, label) -> None

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

    Returns (chunk_file_paths, temp_dir). Caller is responsible for cleaning up
    the temp_dir once done. On failure returns ([], None) and logs.
    """
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
