"""Processing microservice — LLM content generation over whisperforge_core.

POST /generate   single stage              -> {"result": str}
POST /pipeline   full 5-stage pipeline     -> {"wisdom": ..., "outline": ..., ...}
GET  /health

Auth: X-API-Key: SERVICE_TOKEN header.
"""

from typing import Dict, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from shared.security import verify_service_token
from whisperforge_core import llm, pipeline
from whisperforge_core.logging import get_logger

logger = get_logger("processing")
app = FastAPI(title="WhisperForge Processing Service")


class GenerateRequest(BaseModel):
    content_type: str
    context: Dict[str, str]
    provider: str
    model: str
    prompt: Optional[str] = None
    knowledge_base: Optional[Dict[str, str]] = None


class PipelineRequest(BaseModel):
    transcript: str
    provider: str
    model: str
    prompts: Optional[Dict[str, str]] = None
    knowledge_base: Optional[Dict[str, str]] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "processing"}


@app.post("/generate")
async def generate(req: GenerateRequest, _: str = Depends(verify_service_token)):
    try:
        result = llm.generate(
            req.content_type, req.context, req.provider, req.model,
            prompt=req.prompt, knowledge_base=req.knowledge_base,
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
        )
        return {
            "wisdom": result.wisdom,
            "outline": result.outline,
            "social_posts": result.social_posts,
            "image_prompts": result.image_prompts,
            "article": result.article,
        }
    except Exception as e:
        logger.exception("pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))
