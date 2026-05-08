"""Storage microservice — Notion export via whisperforge_core.notion.

POST /save    ContentBundle -> {"url": str}
GET  /health

Auth: X-API-Key: SERVICE_TOKEN header.
"""

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from shared.security import verify_service_token
from whisperforge_core import notion
from whisperforge_core.logging import get_logger

logger = get_logger("storage")
app = FastAPI(title="WhisperForge Storage Service")


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    transcript: str = ""
    wisdom: str = ""
    outline: str = ""
    social_content: str = ""
    image_prompts: str = ""
    article: str = ""
    summary: str = ""
    tags: List[str] = Field(default_factory=list)
    audio_filename: Optional[str] = None
    models_used: List[str] = Field(default_factory=list)
    database_id: Optional[str] = None  # override config if caller wants
    chapters: List[dict] = Field(default_factory=list)
    article_compare: Optional[str] = None
    compare_label: Optional[str] = None
    persona_articles: List[dict] = Field(default_factory=list)
    article_critique: Optional[str] = None
    fact_check_flags: List[dict] = Field(default_factory=list)
    fact_check_ran: bool = False
    run_metrics: Optional[dict] = None


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
        chapters=req.chapters,
        article_compare=req.article_compare,
        compare_label=req.compare_label,
        persona_articles=req.persona_articles,
        article_critique=req.article_critique,
        fact_check_flags=req.fact_check_flags,
        fact_check_ran=req.fact_check_ran,
        run_metrics=req.run_metrics,
    )
    try:
        url = notion.create_page(bundle, database_id=req.database_id)
    except Exception as e:
        logger.exception("notion save failed")
        raise HTTPException(status_code=500, detail=str(e))
    if not url:
        raise HTTPException(status_code=500, detail="Notion returned no page URL")
    return {"url": url}
