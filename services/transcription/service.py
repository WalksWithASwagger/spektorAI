"""Transcription microservice — thin FastAPI wrapper over whisperforge_core.audio.

POST /transcribe   (multipart upload)  -> {"text": str, "filename": str}
GET  /health                           -> {"status": "healthy"}

Auth: X-API-Key: SERVICE_TOKEN header (see shared.security).
"""

import os
import tempfile

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from shared.security import verify_service_token
from whisperforge_core import audio
from whisperforge_core.logging import get_logger

logger = get_logger("transcription")
app = FastAPI(title="WhisperForge Transcription Service")

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "transcription"}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    _: str = Depends(verify_service_token),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Spill to a temp file so audio.transcribe_audio can size-check + chunk.
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        transcript = audio.transcribe_audio(tmp_path)
        return {"text": transcript, "filename": file.filename}
    except Exception as e:
        logger.exception("transcription failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
