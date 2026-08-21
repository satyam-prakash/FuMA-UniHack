"""
Row-level orchestration: Member 1 normalization -> Member 2 enrichment ->
schema check -> 252-column delivery mapping.

``enrich_raw_row`` is the only entry point the API and the batch runner use, and
it never raises: each of the four stages is wrapped, so a poisoned row becomes a
RowResult with ``status="error"`` instead of aborting the batch.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Mapping, Optional, Sequence

from fuma_engine.pipeline_interface import enrich_single_item
from fuma_engine.schema import ProductRecord
from fuma_rules.stage1_master_data import MasterDataPipelineStage
from member3.delivery.mapper import map_record_to_delivery

#: Columns an uploaded file must contain before we accept it.
REQUIRED_INPUT_COLUMNS = (
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
)

#: The six keys Member 1 adds on top of the raw row.
M1_ADDED_KEYS = (
    "CLEAN_DESC",
    "MANUFACTURER_NAME",
    "BRAND_NAME",
    "MANUFACTURER_PART_NUMBER",
    "STANDARDIZED_DIMENSIONS",
    "STAGE1_STATUS",
)

#: Business fields a row cannot live without. Blank values (not just missing
#: keys) put the row straight into the review queue with confidence 0.
REQUIRED_ROW_FIELDS = ("Mfg_Part_Num", "Part_Desc", "Part_Manuf")

REVIEW_CATEGORIES = (
    "low_confidence",
    "schema_failure",
    "no_attributes",
    "generic_taxonomy",
    "description_issue",
    "export_issue",
    "processing_error",
    "missing_required_field",
)

INVOICE_MAX = 40
MOBILE_SCHEMA_MAX = 85
MOBILE_TARGET = (60, 80)
CONFIDENCE_FLOOR = 80.0


class Pipeline:
    """Owns the reusable Member 1 stage (constructing it builds a brand catalog)."""

    def __init__(self) -> None:
        self.master_data = MasterDataPipelineStage()

    def normalize(self, raw_row: Mapping[str, Any]) -> Dict[str, Any]:
        return self.master_data.process_item(dict(raw_row))


def new_pipeline() -> Pipeline:
    """Builds a fresh Pipeline. Callers that just want one should use the shared default."""
    return Pipeline()


# ponytail: one lazily built process-wide Pipeline. It is read-only per row, so
# threads share it; give each worker its own only if M1 ever grows mutable state.
_DEFAULT: Optional[Pipeline] = None
_DEFAULT_LOCK = threading.Lock()


def default_pipeline() -> Pipeline:
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = new_pipeline()
        return _DEFAULT


def missing_input_columns(fieldnames: Sequence[str]) -> List[str]:
    """Required upload columns absent from ``fieldnames`` (case-insensitive)."""
    present = {str(name).strip().lower() for name in fieldnames or []}
    return [c for c in REQUIRED_INPUT_COLUMNS if c.lower() not in present]


def validation_flags(
    enriched: Mapping[str, Any],
    *,
    schema_valid: bool = True,
    schema_errors: Sequence[str] = (),
    export_warnings: Sequence[str] = (),
) -> Dict[str, Any]:
    """Grades one enriched record against every quality rule we can check locally.

    Pure and tolerant of partial dicts so tests can grade a hand-built record.
    """
    invoice = str(enriched.get("invoice_desc") or "")
    mobile = str(enriched.get("mobile_desc") or "")
    classpath = str(enriched.get("classpath") or "")
    return {
        "schema_valid": schema_valid,
        "schema_errors": list(schema_errors),
        "invoice_len": len(invoice),
        # Reported separately so the dashboard can attribute a failure to the
        # length rule or the casing rule instead of one merged verdict.
        "invoice_char_pass": 0 < len(invoice) <= INVOICE_MAX,
        "invoice_caps": bool(invoice) and invoice.isupper(),
        "invoice_pass": 0 < len(invoice) <= INVOICE_MAX and invoice.isupper(),
        "mobile_len": len(mobile),
        # Schema allowance is 0 < len <= 85: an EMPTY mobile description is not
        # "passing" anything, so it must not count toward the compliance rate.
        "schema_mobile_pass": 0 < len(mobile) <= MOBILE_SCHEMA_MAX,
        "mobile_target_pass": MOBILE_TARGET[0] <= len(mobile) <= MOBILE_TARGET[1],
        "attribute_count": len(enriched.get("attributes") or []),
        "feature_count": len(enriched.get("features") or []),
        "generic_classpath": not classpath or "General Hardware" in classpath,
        "export_warnings": list(export_warnings),
    }


def _categories(enriched: Mapping[str, Any], validation: Mapping[str, Any]) -> List[str]:
    flags = {
        "low_confidence": float(enriched.get("confidence_score") or 0.0) < CONFIDENCE_FLOOR,
        "schema_failure": not validation["schema_valid"],
        "no_attributes": validation["attribute_count"] == 0,
        "generic_taxonomy": validation["generic_classpath"],
        "description_issue": not validation["invoice_pass"] or not validation["mobile_target_pass"],
        "export_issue": bool(validation["export_warnings"]),
    }
    return [name for name, hit in flags.items() if hit]


def _base_result(raw: Dict[str, str], row_id: int) -> Dict[str, Any]:
    return {
        "row_id": row_id,
        "status": "error",
        "mpn": raw.get("Mfg_Part_Num", ""),
        "part_desc": raw.get("Part_Desc", ""),
        "brand_name": "",
        "product_name": "",
        "classpath": "",
        "confidence_score": 0.0,
        "confidence": 0.0,
        "raw": raw,
        "normalized": {},
        "enriched": {},
        "delivery_row": None,
        "validation": validation_flags({}, schema_valid=False),
        "review": {
            "needs_review": True,
            "reasons": [],
            "categories": [],
            "decision": None,
        },
        "error": None,
    }


def _fail(result: Dict[str, Any], stage: str, exc: BaseException) -> Dict[str, Any]:
    """Stamps a stage failure onto the RowResult and hands it back intact."""
    message = f"{type(exc).__name__}: {exc}".strip()
    result["status"] = "error"
    result["error"] = {"code": "STAGE_FAILED", "message": message, "stage": stage}
    result["review"] = {
        "needs_review": True,
        "reasons": [f"{stage} stage failed: {message}"],
        "categories": ["processing_error"],
        "decision": None,
    }
    return result


def _input_invalid_result(raw: Dict[str, str], row_id: int, missing: List[str]) -> Dict[str, Any]:
    """A row missing a required business field never enters the engines.

    There is nothing to normalize or enrich without the identity fields, so the
    row is graded ``review`` with confidence 0 and a reason naming the gap. It
    is also excluded from delivery (no ``enriched`` record), so a blank-MPN row
    can never ship or be counted as a clean success.
    """
    result = _base_result(raw, row_id)
    result["status"] = "review"
    result["review"] = {
        "needs_review": True,
        "reasons": [f"Required field is missing or blank: {', '.join(missing)}"],
        "categories": ["missing_required_field"],
        "decision": None,
    }
    return result


def enrich_raw_row(raw_row: dict, row_id: int = 0) -> dict:
    """Runs one upload row through the full pipeline and grades it. Never raises."""
    raw = {str(k): "" if v is None else str(v) for k, v in (raw_row or {}).items()}
    result = _base_result(raw, row_id)

    missing_fields = [f for f in REQUIRED_ROW_FIELDS if not str(raw.get(f, "")).strip()]
    if missing_fields:
        return _input_invalid_result(raw, row_id, missing_fields)

    try:
        normalized_full = default_pipeline().normalize(raw_row or {})
    except Exception as exc:  # noqa: BLE001 - stage isolation is the point
        return _fail(result, "member1", exc)
    result["normalized"] = {k: normalized_full.get(k, "") for k in M1_ADDED_KEYS}

    try:
        enriched = enrich_single_item(normalized_full)
    except Exception as exc:  # noqa: BLE001
        return _fail(result, "member2", exc)

    try:
        ProductRecord(**enriched)
    except Exception as exc:  # noqa: BLE001
        result["enriched"] = enriched
        return _fail(result, "schema", exc)

    try:
        delivery_row, export_warnings = map_record_to_delivery(enriched, raw)
    except Exception as exc:  # noqa: BLE001
        result["enriched"] = enriched
        return _fail(result, "delivery", exc)

    validation = validation_flags(enriched, export_warnings=export_warnings)

    # Member 3 flags a row for review when Member 2 asks for it OR when our own
    # delivery-side rules fail, so compliance problems can never ship silently.
    reasons = [str(r) for r in enriched.get("review_reasons") or []]
    if enriched.get("needs_review") and not reasons:
        reasons.append("Flagged for review by the enrichment engine")
    if not validation["invoice_char_pass"]:
        reasons.append(f"INVOICE_DESC exceeds 40 characters ({validation['invoice_len']} chars)")
    if not validation["invoice_caps"]:
        reasons.append("INVOICE_DESC is not uppercase")
    if not validation["mobile_target_pass"]:
        reasons.append(
            f"MOBILE_DESC length ({validation['mobile_len']} chars) outside target 60-80 window"
        )
    if validation["attribute_count"] == 0:
        reasons.append("No technical attributes could be extracted from description")
    if validation["generic_classpath"]:
        reasons.append("Uncertain category / generic classpath fallback")

    deduped: List[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)

    # Review policy: a row is queued for human review if and only if it carries
    # at least one review reason. This keeps queue membership, the reasons
    # column and the category filters mutually consistent — a row with a
    # documented quality problem can never silently ship as a clean success.
    needs_review = bool(deduped)
    confidence = float(enriched.get("confidence_score") or 0.0)
    result.update(
        {
            "status": "review" if needs_review else "success",
            "brand_name": str(enriched.get("brand_name") or ""),
            "product_name": str(enriched.get("product_name") or ""),
            "classpath": str(enriched.get("classpath") or ""),
            "confidence_score": confidence,
            "confidence": confidence,
            "enriched": enriched,
            "delivery_row": delivery_row,
            "validation": validation,
            "review": {
                "needs_review": needs_review,
                "reasons": deduped,
                "categories": _categories(enriched, validation),
                "decision": None,
            },
        }
    )
    return result


#: Contract alias used by the API layer and the plan's frozen interface.
validate_input_columns = missing_input_columns
