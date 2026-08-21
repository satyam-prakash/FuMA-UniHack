"""
Row-level orchestration: Member 1 normalization -> Member 2 enrichment.

``enrich_raw_row`` is the only entry point the API and batch runner use. It
never raises: a blown-up stage becomes ``status="error"`` on the returned
RowResult so one bad row can never abort a batch.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fuma_engine.pipeline_interface import enrich_single_item
from fuma_engine.schema import ProductRecord
from fuma_rules.stage1_master_data import MasterDataPipelineStage

#: Columns an uploaded file must contain before we accept it.
REQUIRED_INPUT_COLUMNS = [
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
]

# ponytail: one shared stage; constructing it loads the brand catalog, and it
# holds no per-row state. Swap to a pool only if it ever becomes stateful.
_M1_STAGE = MasterDataPipelineStage()

_INVOICE_MAX = 40
_MOBILE_SCHEMA_MAX = 85
_MOBILE_TARGET = (60, 80)


def validate_input_columns(fieldnames: List[str]) -> List[str]:
    """Returns the required columns missing from ``fieldnames`` (case-insensitive)."""
    present = {str(name).strip().lower() for name in fieldnames or []}
    return [column for column in REQUIRED_INPUT_COLUMNS if column.lower() not in present]


def enrich_raw_row(raw_row: dict, row_id: int = 0) -> dict:
    """Runs one raw upload row through M1 then M2 and grades the result.

    Always returns a RowResult dict; every failure mode is reported in
    ``status``/``review["reasons"]`` instead of raised.
    """
    raw = {key: "" if value is None else str(value) for key, value in (raw_row or {}).items()}
    reasons: List[str] = []
    errors: List[str] = []
    normalized: Dict[str, Any] = {}
    enriched: Dict[str, Any] = {}
    stage_failed = False

    try:
        normalized = _json_safe(_M1_STAGE.process_item(dict(raw_row or {})))
    except Exception as exc:
        stage_failed = True
        reasons.append(f"M1 normalization failed: {exc}")

    if not stage_failed:
        try:
            enriched = enrich_single_item(normalized)
        except Exception as exc:
            stage_failed = True
            enriched = {}
            reasons.append(f"M2 enrichment failed: {exc}")

    schema_valid = False
    if not stage_failed:
        reasons.extend(str(reason) for reason in enriched.get("review_reasons") or [])
        try:
            ProductRecord(**enriched)
            schema_valid = True
        except Exception as exc:
            errors.extend(str(exc).splitlines())
            reasons.append(f"Schema validation failed: {exc}")

    invoice = str(enriched.get("invoice_desc", "") or "")
    mobile = str(enriched.get("mobile_desc", "") or "")
    invoice_len = len(invoice)
    mobile_len = len(mobile)
    invoice_caps = bool(invoice) and invoice.isupper()
    attribute_count = len(enriched.get("attributes") or [])
    classpath = str(enriched.get("classpath", "") or "")

    if not stage_failed:
        # ponytail: M2 words the same defects differently, so match on a keyword
        # rather than the full string, or the dashboard counts each defect twice.
        if invoice_len > _INVOICE_MAX and not _flagged(reasons, "invoice_desc exceeds"):
            reasons.append(f"INVOICE_DESC exceeds {_INVOICE_MAX} characters ({invoice_len})")
        if not invoice_caps and not _flagged(reasons, "not uppercase"):
            reasons.append("INVOICE_DESC is not uppercase")
        if not _MOBILE_TARGET[0] <= mobile_len <= _MOBILE_TARGET[1] and not _flagged(
            reasons, "mobile_desc"
        ):
            reasons.append(
                f"MOBILE_DESC outside {_MOBILE_TARGET[0]}-{_MOBILE_TARGET[1]} target ({mobile_len})"
            )
        if attribute_count == 0 and not _flagged(reasons, "attributes"):
            reasons.append("No technical attributes extracted")
        if "General Hardware" in classpath and not _flagged(reasons, "classpath"):
            reasons.append("Generic classpath fallback: General Hardware")

    if stage_failed:
        status = "error"
        confidence = 0.0
        needs_review = True
    else:
        confidence = float(enriched.get("confidence_score") or 0.0)
        needs_review = bool(
            enriched.get("needs_review")
            or not schema_valid
            or invoice_len > _INVOICE_MAX
            or not invoice_caps
            or attribute_count == 0
        )
        status = "review" if needs_review else "success"

    return {
        "row_id": row_id,
        "status": status,
        "raw": raw,
        "normalized": normalized,
        "enriched": enriched,
        "validation": {
            "schema_valid": schema_valid,
            "errors": errors,
            "invoice_len": invoice_len,
            "invoice_caps": invoice_caps,
            "mobile_len": mobile_len,
            "schema_mobile_pass": mobile_len <= _MOBILE_SCHEMA_MAX,
            "mobile_target_pass": _MOBILE_TARGET[0] <= mobile_len <= _MOBILE_TARGET[1],
            "attribute_count": attribute_count,
        },
        "review": {
            "needs_review": needs_review,
            "reasons": _dedupe(reasons),
            "decision": None,
            "comment": "",
        },
        "confidence": confidence,
    }


def _json_safe(record: Dict[str, Any]) -> Dict[str, Any]:
    """M1 output with non-primitive values stringified, so it survives JSON."""
    return {
        key: value if isinstance(value, (str, int, float, bool)) or value is None else str(value)
        for key, value in record.items()
    }


def _flagged(reasons: List[str], keyword: str) -> bool:
    """True when a reason already covers this defect (M2 phrases differ from ours)."""
    return any(keyword in reason.lower() for reason in reasons)


def _dedupe(values: List[str]) -> List[str]:
    return list(dict.fromkeys(values))
