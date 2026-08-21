"""
Request/response models and the single error shape for the FuMA API.

Every failure the frontend can see is an :class:`ApiException`, rendered by the
handler in ``main.py`` as ``{"error": {...}}``. Nothing in this app returns
FastAPI's default ``{"detail": ...}`` body.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    """The `error` payload; the wire body is `{"error": <this>}`."""

    code: str
    message: str
    row_id: Optional[int] = None
    details: List[str] = Field(default_factory=list)


class ApiException(Exception):
    """Raise anywhere in a route to emit the contract error body."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        row_id: Optional[int] = None,
        details: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = ApiError(code=code, message=message, row_id=row_id, details=details or [])

    def body(self) -> Dict[str, Any]:
        """The exact JSON body for this failure."""
        return {"error": self.error.model_dump()}


class HealthResponse(BaseModel):
    status: str
    service: str
    delivery_columns: int


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    rows: int
    columns: List[str]
    status: str


class EnrichRequest(BaseModel):
    job_id: str
    mode: str = "demo"


class EnrichResponse(BaseModel):
    job_id: str
    status: str
    total: int


class StageState(BaseModel):
    key: str
    label: str
    state: str


class JobStatusResponse(BaseModel):
    job_id: str
    filename: str
    mode: str
    status: str
    total: int
    processed: int
    success: int
    review: int
    errors: int
    progress: int
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    stages: List[StageState]
    export: Dict[str, Any]


class ResultsPage(BaseModel):
    job_id: str
    page: int
    page_size: int
    total: int
    pages: int
    rows: List[Dict[str, Any]]


class ReviewDecisionRequest(BaseModel):
    action: str
    comment: str = ""


class ExportStatusResponse(BaseModel):
    """Pre-download gate shown in the Export Center."""

    delivery_columns: int
    valid: bool
    errors: List[str] = []
    row_count: int
    rows_needing_review: int


#: Historical alias: routes import ``ReviewRequest``.
ReviewRequest = ReviewDecisionRequest
