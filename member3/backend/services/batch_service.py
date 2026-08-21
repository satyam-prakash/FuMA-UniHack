"""
Job store and batch runner for FuMA Member 3.

In-process job registry. A job holds the uploaded rows, per-row results and
counters. Rows are processed synchronously in a worker thread so the HTTP
request can return immediately while the dashboard polls for progress.

One bad row never aborts a batch: ``enrich_raw_row`` already converts row
failures into ``status="error"`` results.
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from member3.backend.services.pipeline_service import enrich_raw_row

def _new_job_id() -> str:
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"


class JobStore:
    """Thread-safe in-memory job registry."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ create

    def create_job(self, filename: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        job_id = _new_job_id()
        job = {
            "job_id": job_id,
            "filename": filename,
            "status": "uploaded",
            "total": len(rows),
            "processed": 0,
            "success": 0,
            "review": 0,
            "errors": 0,
            "progress": 0,
            "elapsed_seconds": 0.0,
            "rows": rows,
            "results": [],
        }
        with self._lock:
            self._jobs[job_id] = job
        return self.summary(job_id)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Job state without the heavy ``rows``/``results`` payloads."""
        job = self.get(job_id)
        if job is None:
            return None
        return {k: v for k, v in job.items() if k not in ("rows", "results")}

    # ------------------------------------------------------------------- run

    def run_job(self, job_id: str) -> Dict[str, Any]:
        """Processes every row. Safe to call directly or from a thread."""
        job = self.get(job_id)
        if job is None:
            raise KeyError(job_id)

        started = time.time()
        job["status"] = "processing"
        job["results"] = []
        job["processed"] = job["success"] = job["review"] = job["errors"] = 0
        job["progress"] = 0

        for index, raw in enumerate(job["rows"], start=1):
            result = enrich_raw_row(raw, row_id=index)
            job["results"].append(result)
            job["processed"] = index
            status = result.get("status")
            if status == "success":
                job["success"] += 1
            elif status == "error":
                job["errors"] += 1
            else:
                job["review"] += 1
            job["progress"] = int(index / job["total"] * 100) if job["total"] else 100
            job["elapsed_seconds"] = round(time.time() - started, 3)

        job["elapsed_seconds"] = round(time.time() - started, 3)
        job["status"] = "completed_with_review" if (job["review"] or job["errors"]) else "completed"
        return self.summary(job_id)

    def start_job_async(self, job_id: str) -> Dict[str, Any]:
        """Marks a job queued and runs it on a daemon thread."""
        job = self.get(job_id)
        if job is None:
            raise KeyError(job_id)
        job["status"] = "queued"

        def _worker() -> None:
            try:
                self.run_job(job_id)
            except Exception as exc:  # pragma: no cover - defensive
                job["status"] = "failed"
                job["error"] = str(exc)

        threading.Thread(target=_worker, daemon=True).start()
        return self.summary(job_id)

    # --------------------------------------------------------------- results

    def list_results(
        self,
        job_id: str,
        page: int = 1,
        page_size: int = 50,
        status: str = "all",
        search: str = "",
    ) -> Optional[Dict[str, Any]]:
        job = self.get(job_id)
        if job is None:
            return None

        rows = job["results"]
        if status and status != "all":
            rows = [r for r in rows if r.get("status") == status]
        if search:
            needle = search.lower()
            rows = [r for r in rows if needle in _searchable(r)]

        page = max(1, page)
        page_size = max(1, min(page_size, 500))
        start = (page - 1) * page_size
        total = len(rows)
        pages = (total + page_size - 1) // page_size
        return {
            "job_id": job_id,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
            "rows": rows[start : start + page_size],
        }

    def get_result(self, job_id: str, row_id: int) -> Optional[Dict[str, Any]]:
        job = self.get(job_id)
        if job is None:
            return None
        for result in job["results"]:
            if result.get("row_id") == row_id:
                return result
        return None

    def review_rows(self, job_id: str) -> Optional[List[Dict[str, Any]]]:
        """Compact queue entries. Deliberately NOT full RowResults: the queue can
        hold most of a batch, and shipping 252-column delivery rows for every
        entry would turn a 250 KB response into a multi-megabyte one."""
        job = self.get(job_id)
        if job is None:
            return None
        return [
            {
                "row_id": r["row_id"],
                "mpn": r["mpn"],
                "part_desc": r["part_desc"],
                "brand_name": r["brand_name"],
                "confidence_score": r["confidence_score"],
                "status": r["status"],
                "reasons": r["review"]["reasons"],
                "categories": r["review"]["categories"],
                "decision": r["review"]["decision"],
            }
            for r in job["results"]
            if r["review"]["needs_review"] or r["status"] == "error"
        ]

    def set_review(
        self, job_id: str, row_id: int, action: str, comment: str = ""
    ) -> Optional[Dict[str, Any]]:
        result = self.get_result(job_id, row_id)
        if result is None:
            return None
        result["review"]["decision"] = {
            "action": action,
            "comment": comment,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if action in ("approve", "mark_reviewed", "override"):
            result["review"]["needs_review"] = False
        return result


def _searchable(result: Dict[str, Any]) -> str:
    enriched = result.get("enriched") or {}
    raw = result.get("raw") or {}
    parts = [
        str(enriched.get("mfg_part_num", "")),
        str(enriched.get("brand_name", "")),
        str(enriched.get("product_name", "")),
        str(enriched.get("classpath", "")),
        str(raw.get("Mfg_Part_Num", "")),
        str(raw.get("Part_Desc", "")),
    ]
    return " ".join(parts).lower()


_STORE = JobStore()


def get_job_store() -> JobStore:
    return _STORE
