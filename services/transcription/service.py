"""Transcription microservice — thin FastAPI wrapper over whisperforge_core.audio.

POST /transcribe   (multipart upload)  ->
                     {"text": str, "segments": list, "language": str|null, "filename": str}
GET  /health                           -> {"status": "healthy"}

Auth: X-API-Key: SERVICE_TOKEN header (see shared.security).
"""

import os
import shutil
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

    tmp_path = _copy_upload_to_temp(file, ext)

    try:
        details = audio.transcribe_audio_detailed(tmp_path)
        return {
            "text": details.text,
            "segments": details.segments,
            "language": details.language,
            "filename": file.filename,
        }
    except Exception as e:
        logger.exception("transcription failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _copy_upload_to_temp(file: UploadFile, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        try:
            file.file.seek(0)
            shutil.copyfileobj(file.file, tmp, length=1 << 20)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    return tmp_path
