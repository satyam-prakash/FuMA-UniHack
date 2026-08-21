"""
FuMA Member 3 application entrypoint.

Run with::

    .venv/bin/python -m uvicorn member3.backend.main:app --reload

Serves the API under ``/api`` and, when the frontend has been built, the SPA
from ``member3/frontend/dist`` so a single process powers the whole demo.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from member3.backend.routes.api import router
from member3.delivery.columns import DELIVERY_COLUMN_COUNT

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

app = FastAPI(
    title="FuMA Delivery API",
    version="1.0.0",
    description=(
        "Member 3 integration layer: orchestrates Member 1 normalization and "
        f"Member 2 enrichment, then emits the exact {DELIVERY_COLUMN_COUNT}-column delivery file."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def spa_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        candidate = FRONTEND_DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
