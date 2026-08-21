"""
Request models for the FuMA Member 3 API.

Only request bodies live here. Responses are plain dicts: the shapes are
assembled from the job store, the pipeline and the delivery validator, and
mirroring each one as a second Pydantic class bought nothing but a place for
the two definitions to drift apart.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EnrichRequest(BaseModel):
    """Body of ``POST /api/enrich``."""

    job_id: str
    mode: str = "demo"


class ReviewRequest(BaseModel):
    """Body of ``POST /api/jobs/{job_id}/review/{row_id}``."""

    action: str = Field(pattern="^(approve|reject|override|mark_reviewed)$")
    comment: str = ""
