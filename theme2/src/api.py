"""FastAPI Application for Samsung PRISM Hackathon Theme 2.
Implements:
- GET /health -> {"status": "ok"}
- POST /v1/troubleshoot -> ContextDeeplinkResponse
- POST /v1/preview -> Diagnostic preview endpoint
"""
from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from theme2.src.cache import MultiTierCache
from theme2.src.deeplink_resolver import DeeplinkResolver
from theme2.src.normalizer import ComplaintNormalizer
from theme2.src.pipeline import TroubleshootingPipeline
from theme2.src.schema import (
    ContextDeeplinkResponse,
    PreviewRequest,
    TroubleshootRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up resolver, embeddings, and caches on startup
    DeeplinkResolver.get_instance()
    MultiTierCache.get_instance()
    ComplaintNormalizer.get_instance()
    TroubleshootingPipeline.get_instance()
    yield


app = FastAPI(
    title="Smart Guided Troubleshooting Engine",
    description="Samsung PRISM GenAI Hackathon 3.0 (Theme 2)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


import os
import json
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")

@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Smart Guided Troubleshooting Engine API"}

@app.get("/api/samples")
async def get_samples():
    siis_path = os.path.join(base_dir, "data", "student_kit", "siis_responses.json")
    if not os.path.exists(siis_path):
        return []
    with open(siis_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = []
    for item in data.get("responses", []):
        raw = item.get("siis_response", {})
        samples.append({
            "query": item.get("original_query", ""),
            "title": raw.get("title", ""),
            "content": raw.get("content", "")
        })
    return samples

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Mandatory scoring gate G2 endpoint."""
    return {"status": "ok"}


@app.post(
    "/v1/troubleshoot",
    response_model=ContextDeeplinkResponse,
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=False,
)
async def troubleshoot(request: TroubleshootRequest, response: Response):
    """Main troubleshooting endpoint required by official evaluation harness."""
    query = request.query.strip() if request.query else ""
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query field cannot be empty.",
        )

    if not request.siis_response or not request.siis_response.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SIIS response content cannot be empty.",
        )

    req_id = str(uuid.uuid4())
    pipeline = TroubleshootingPipeline.get_instance()
    result, meta = pipeline.process(query, request.siis_response)

    # Set required diagnostic headers
    response.headers["X-Request-ID"] = req_id
    for k, v in meta.items():
        response.headers[k] = str(v)

    return result


@app.post("/v1/preview", status_code=status.HTTP_200_OK)
async def preview(request: PreviewRequest, response: Response):
    """Diagnostic preview endpoint for interactive demo and fact overrides."""
    query = request.query.strip() if request.query else ""
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query field cannot be empty.",
        )

    pipeline = TroubleshootingPipeline.get_instance()
    normalizer = ComplaintNormalizer.get_instance()

    norm = normalizer.normalize(query)
    # Apply facts if passed
    if request.facts:
        norm.facts.update(request.facts)

    result, meta = pipeline.process(query, request.siis_response)

    return {
        "response": result,
        "normalized": norm.model_dump(),
        "trace": {
            "meta": meta,
            "cache_status": meta.get("X-Cache-Status", "unknown"),
            "processing_time_ms": meta.get("X-Processing-Time-Ms", "0"),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("theme2.src.api:app", host="0.0.0.0", port=8000, reload=True)
