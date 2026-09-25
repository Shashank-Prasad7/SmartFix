"""FastAPI entry point for official responses and source-backed previews."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from theme2.src.compiler import NonActionableSource
from theme2.src.hosted_llm import HostedQuotaError
from theme2.src.normalizer import FACT_KEYS, ComplaintNormalizer
from theme2.src.pipeline import AdmissionRejected, TroubleshootingPipeline
from theme2.src.schema import (
    ContextDeeplinkResponse,
    PreviewRequest,
    TroubleshootRequest,
)

ROOT = Path(__file__).resolve().parents[1]
_pipeline: TroubleshootingPipeline | None = None
_startup_error: str | None = None


def _ready_pipeline() -> TroubleshootingPipeline:
    global _pipeline, _startup_error
    if _pipeline is None:
        try:
            _pipeline = TroubleshootingPipeline.get_instance()
            _startup_error = None
        except (OSError, ValueError, sqlite3.Error) as exc:
            _startup_error = type(exc).__name__
            raise HTTPException(status_code=503, detail="Service is not ready") from exc
    return _pipeline


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        _ready_pipeline()
    except HTTPException:
        pass
    yield


app = FastAPI(title="Smart Guided Troubleshooting Engine", version="2.0.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_request_handler(_request, _exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default details can echo submitted input, including unknown fields.
    return JSONResponse(status_code=422, content={"detail": "Invalid request body"})


ASSETS = ROOT / "static" / "app" / "assets"
if ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")
origins = [item.strip() for item in os.getenv("PRISM_CORS_ORIGINS", "").split(",") if item.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


def _validate_request(request: TroubleshootRequest) -> None:
    if not request.query.strip() or not request.siis_response.content.strip():
        raise HTTPException(status_code=422, detail="Query and source content are required")


async def _execute(request: TroubleshootRequest, response: Response, request_id: str) -> tuple[ContextDeeplinkResponse, dict[str, str]]:
    _validate_request(request)
    started = time.perf_counter()
    try:
        result, metadata = await run_in_threadpool(_ready_pipeline().process, request.query, request.siis_response, started + 7.5)
    except NonActionableSource as exc:
        raise HTTPException(status_code=422, detail="Source contains no supported instruction") from exc
    except (AdmissionRejected, HostedQuotaError) as exc:
        raise HTTPException(status_code=429, detail="Inference capacity is unavailable") from exc
    except (TimeoutError, ValueError, OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail="Unable to produce a complete guide") from exc
    response.headers["X-Request-ID"] = request_id
    if time.perf_counter() >= started + 7.5:
        raise HTTPException(status_code=503, detail="Unable to produce a complete guide")
    response.headers["X-Cache-Status"] = metadata["X-Cache-Status"]
    response.headers["X-Processing-Time-Ms"] = f"{(time.perf_counter()-started)*1000:.2f}"
    return result, metadata


@app.get("/health")
async def health() -> dict[str, str]:
    _ready_pipeline()
    return {"status": "ok"}


@app.post("/v1/troubleshoot", response_model=ContextDeeplinkResponse)
async def troubleshoot(request: TroubleshootRequest, response: Response) -> ContextDeeplinkResponse:
    result, _ = await _execute(request, response, str(uuid.uuid4()))
    return result


@app.post("/v1/preview")
async def preview(request: PreviewRequest, response: Response) -> dict[str, object]:
    if request.facts and not set(request.facts) <= FACT_KEYS:
        raise HTTPException(status_code=422, detail="Unsupported preview fact")
    request_id = str(uuid.uuid4())
    request_started = time.perf_counter()
    result, metadata = await _execute(request, response, request_id)
    try:
        projection_started = time.perf_counter()
        projection = await run_in_threadpool(_ready_pipeline().preview, request.query, request.siis_response, request.facts)
        projection_ms = round((time.perf_counter() - projection_started) * 1000, 2)
    except (ValueError, OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail="Preview is unavailable") from exc
    normalization_started = time.perf_counter()
    normalized = ComplaintNormalizer.normalize(request.query)
    preview_normalization_ms = round((time.perf_counter() - normalization_started) * 1000, 2)
    if time.perf_counter() >= request_started + 7.5:
        raise HTTPException(status_code=503, detail="Preview is unavailable")
    response.headers["X-Processing-Time-Ms"] = f"{(time.perf_counter()-request_started)*1000:.2f}"
    merged = normalized.model_dump()
    merged["facts"] = projection["preview"]["facts"]
    return {
        "response": result,
        **projection,
        "normalized": merged,
        "trace": {"request_id": request_id, "cache_status": metadata["X-Cache-Status"], "processing_time_ms": response.headers["X-Processing-Time-Ms"],
                  "stages": {"normalization": "executed for preview" if metadata["X-Cache-Status"] == "exact_hit" else "executed",
                             "compilation": "executed" if metadata["X-Cache-Status"] == "miss" else "skipped",
                             "hosted_model_calls": int(metadata["X-Hosted-Calls"]),
                             "llm_mode": metadata["X-LLM-Mode"]},
                  "stage_timings_ms": {**json.loads(metadata["X-Stage-Timings-Json"]), "preview_projection": projection_ms,
                                       "preview_normalization": preview_normalization_ms}},
    }


@app.get("/api/samples")
async def samples() -> list[dict[str, str]]:
    source = ROOT / "data" / "official" / "student_kit" / "siis_responses.json"
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Samples unavailable")
    return [{"query": row["original_query"], "title": row["siis_response"]["title"], "content": row["siis_response"]["content"]} for row in data["responses"]]


@app.get("/api/development-sample")
async def development_sample() -> dict[str, str]:
    """One clearly labeled synthetic case for the scoped-facts demo."""
    source = ROOT / "data" / "fixtures" / "development_articles.json"
    try:
        item = json.loads(source.read_text(encoding="utf-8"))["articles"][0]
    except (OSError, ValueError, IndexError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="Development sample unavailable") from exc
    return {"query": "The inner display is black but the cover screen works", "title": item["title"], "content": item["content"], "provenance": "team-authored synthetic development fixture"}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    built = ROOT / "static" / "app" / "index.html"
    return FileResponse(built if built.is_file() else ROOT / "static" / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(ROOT / "static" / "app" / "favicon.svg")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("theme2.src.api:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), workers=1)
