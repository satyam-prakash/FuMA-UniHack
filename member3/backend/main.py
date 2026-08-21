"""
FuMA Member 3 application entrypoint.

Run with::

    .venv/bin/python -m uvicorn member3.backend.main:app --reload

Serves the API under ``/api`` and, when the frontend has been built, the SPA
from ``member3/frontend/dist`` so a single process powers the whole demo.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic request-validation failures use the same error envelope as every
    other API error, so clients only ever parse one error shape."""
    details: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        details.append(f"{location}: {error.get('msg', 'invalid')}")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "row_id": None,
                "details": details or ["invalid request"],
            }
        },
    )


app.include_router(router)


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    def _not_found(message: str) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": message, "row_id": None, "details": []}},
        )

    @app.get("/", include_in_schema=False)
    def spa_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str):
        # The API router is registered before this catch-all, so any path that
        # reaches here under /api is an UNKNOWN endpoint. Answer with the JSON
        # error envelope instead of SPA HTML so clients never parse HTML as JSON.
        if path == "api" or path.startswith("api/"):
            return _not_found("API endpoint not found")

        # Resolve against the frontend root and refuse anything that escapes it.
        # resolve() collapses ".." segments and symlinks; is_relative_to() is the
        # containment check. Encoded traversal (%2F, %2e%2e) is decoded by the
        # router before this point, so both arrive here as ".." and are rejected.
        frontend_root = FRONTEND_DIST.resolve()
        candidate = (frontend_root / path).resolve()
        if not candidate.is_relative_to(frontend_root):
            return _not_found("Not found")
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
