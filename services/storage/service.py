"""Storage microservice — Notion export via whisperforge_core.notion.

POST /save    ContentBundle -> {"url": str}
GET  /health

Auth: X-API-Key: SERVICE_TOKEN header.
"""

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from shared.security import verify_service_token
from whisperforge_core import notion
from whisperforge_core.logging import get_logger

logger = get_logger("storage")
app = FastAPI(title="WhisperForge Storage Service")


class SaveRequest(BaseModel):
    title: str
    transcript: str = ""
    wisdom: str = ""
    outline: str = ""
    social_content: str = ""
    image_prompts: str = ""
    article: str = ""
    summary: str = ""
    tags: List[str] = []
    audio_filename: Optional[str] = None
    models_used: List[str] = []
    database_id: Optional[str] = None  # override config if caller wants


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "storage"}


@app.post("/save")
async def save(req: SaveRequest, _: str = Depends(verify_service_token)):
    bundle = notion.ContentBundle(
        title=req.title,
        transcript=req.transcript,
        wisdom=req.wisdom,
        outline=req.outline,
        social_content=req.social_content,
        image_prompts=req.image_prompts,
        article=req.article,
        summary=req.summary,
        tags=req.tags,
        audio_filename=req.audio_filename,
        models_used=req.models_used,
    )
    try:
        url = notion.create_page(bundle, database_id=req.database_id)
    except Exception as e:
        logger.exception("notion save failed")
        raise HTTPException(status_code=500, detail=str(e))
    if not url:
        raise HTTPException(status_code=500, detail="Notion returned no page URL")
    return {"url": url}
