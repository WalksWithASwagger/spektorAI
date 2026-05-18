"""Processing microservice — LLM content generation over whisperforge_core.

POST /generate   single stage              -> {"result": str}
POST /pipeline   full 5-stage pipeline     -> {"wisdom": ..., "outline": ..., ...}
GET  /health

Auth: X-API-Key: SERVICE_TOKEN header.
"""

from dataclasses import asdict
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from shared.security import verify_service_token
from whisperforge_core import llm, pipeline
from whisperforge_core.logging import get_logger

logger = get_logger("processing")
app = FastAPI(title="WhisperForge Processing Service")


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str
    context: Dict[str, str]
    provider: str
    model: str
    prompt: Optional[str] = None
    knowledge_base: Optional[Dict[str, str]] = None
    max_tokens: Optional[int] = None
    user: Optional[str] = None
    rag_mode: str = "auto"


class PipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript: str
    provider: str
    model: str
    prompts: Optional[Dict[str, str]] = None
    knowledge_base: Optional[Dict[str, str]] = None
    cleanup: bool = True
    chapters: bool = True
    segments: Optional[List[dict]] = None
    agentic: bool = False
    fact_check: bool = False
    generate_images: bool = False
    image_style: Optional[str] = None
    image_aspect_ratio: str = "16:9"
    image_model: str = "gemini-2.5-flash-image"
    image_output_dir: Optional[str] = None
    article_length_words: int = 1500
    user: Optional[str] = None
    rag_mode: str = "auto"
    compare_provider: Optional[str] = None
    compare_model: Optional[str] = None
    personas: Optional[List[str]] = None
    recipe: Optional[dict] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "processing"}


@app.post("/generate")
async def generate(req: GenerateRequest, _: str = Depends(verify_service_token)):
    try:
        result = llm.generate(
            req.content_type, req.context, req.provider, req.model,
            prompt=req.prompt, knowledge_base=req.knowledge_base,
            max_tokens=req.max_tokens, user=req.user, rag_mode=req.rag_mode,
        )
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline")
async def run_pipeline(req: PipelineRequest, _: str = Depends(verify_service_token)):
    try:
        result = pipeline.run(
            req.transcript, req.provider, req.model,
            prompts=req.prompts, knowledge_base=req.knowledge_base,
            cleanup=req.cleanup, chapters=req.chapters, segments=req.segments,
            agentic=req.agentic, fact_check=req.fact_check,
            generate_images=req.generate_images, image_style=req.image_style,
            image_aspect_ratio=req.image_aspect_ratio,
            image_model=req.image_model, image_output_dir=req.image_output_dir,
            article_length_words=req.article_length_words,
            user=req.user, rag_mode=req.rag_mode,
            compare_provider=req.compare_provider, compare_model=req.compare_model,
            personas=req.personas,
            recipe=req.recipe,
        )
        return asdict(result)
    except Exception as e:
        logger.exception("pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))
