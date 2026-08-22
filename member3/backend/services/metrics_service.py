"""
Metrics and ground-truth benchmark for FuMA Member 3.

Reports two separate mobile KPIs on purpose:

``schema_mobile_pass``
    Passes the current ``ProductRecord`` limit of 85 characters.
``mobile_target_60_80_pass``
    Passes the stricter client target of 60-80 characters.

Conflating the two would let the dashboard claim 60-80 compliance it has not
earned, so both are surfaced.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

#: Delivery fields compared against ground truth, mapped to ProductRecord keys.
BENCHMARK_FIELDS = {
    "MANUFACTURER_NAME": "manufacturer_name",
    "BRAND_NAME": "brand_name",
    "MANUFACTURER_PART_NUMBER": "mfg_part_num",
    "Classpath": "classpath",
    "UNSPSC": "unspsc",
    "Product Name": "product_name",
    "INVOICE_DESC": "invoice_desc",
    "MOBILE_DESC": "mobile_desc",
    "SHORT_DESC": "short_desc",
    "LONG_DESC1": "long_desc1",
    "RETAIL_DESC": "retail_desc",
}


#: Brand tiers strong enough to publish (mirrors fuma_rules.brand_matcher).
_STRONG_BRAND_TIERS = frozenset(
    {"EXPLICIT_BRAND_MASTER", "MANUFACTURER_EXACT", "DISTRIBUTOR_OVERRIDE", "MANUFACTURER_ALIAS"}
)


def _pct(count: int, total: int) -> float:
    return round(count / total * 100, 2) if total else 0.0


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """KPI block for the dashboard. Never raises on partial data."""
    total = len(results)
    if total == 0:
        return {
            "total": 0,
            "success": 0,
            "review": 0,
            "errors": 0,
            "success_rate": 0.0,
            "avg_confidence": 0.0,
            "invoice_char_pass": 0.0,
            "invoice_caps_pass": 0.0,
            "schema_mobile_pass": 0.0,
            "mobile_target_60_80_pass": 0.0,
            "schema_pass_rate": 0.0,
            "classpath_specific_rate": 0.0,
            "attribute_coverage": 0.0,
            "attribute_structured_rate": 0.0,
            "attribute_evidence_rate": 0.0,
            "attribute_values_total": 0,
            "attribute_evidence_values": 0,
            "attribute_inferred_values": 0,
            "attribute_evidence_value_rate": 0.0,
            "avg_attributes": 0.0,
            "avg_evidence_attributes": 0.0,
            "brand_resolved_rate": 0.0,
            "brand_strong_evidence_rate": 0.0,
            "lov_measurable": False,
            "lov_compliance_rate": None,
            "lov_rows_measured": 0,
            "duplicate_rows": 0,
            "duplicate_rate": 0.0,
            "confidence_histogram": [],
            "review_reasons": [],
            "status_distribution": [],
        }

    success = sum(1 for r in results if r.get("status") == "success")
    errors = sum(1 for r in results if r.get("status") == "error")
    review = total - success - errors

    invoice_char = invoice_caps = schema_mobile = mobile_target = 0
    schema_ok = specific_classpath = with_attributes = 0
    confidence_sum = 0.0
    attribute_sum = 0
    # Three-tier attribute accounting. "Coverage 100%" is a tautology because the
    # pipeline guarantees >= 1 attribute per classified row, so evidence-backed
    # and inferred values are counted separately and reported side by side.
    evidence_values = inferred_values = 0
    rows_with_evidence = 0
    # Brand evidence + LOV compliance, both gated on being measurable at all.
    strong_brand = resolved_brand = 0
    lov_sum = 0.0
    lov_rows = 0
    duplicates = 0

    # Contract buckets: 0-59, 60-79, 80-89, 90-99, 100.
    bucket_ranges = [(0, 59), (60, 79), (80, 89), (90, 99), (100, 100)]
    buckets = [0] * len(bucket_ranges)
    reason_counts: Dict[str, int] = {}

    for result in results:
        validation = result.get("validation") or {}
        enriched = result.get("enriched") or {}

        if validation.get("invoice_char_pass"):
            invoice_char += 1
        if validation.get("invoice_caps"):
            invoice_caps += 1
        if validation.get("schema_mobile_pass"):
            schema_mobile += 1
        if validation.get("mobile_target_pass"):
            mobile_target += 1
        if validation.get("schema_valid"):
            schema_ok += 1

        classpath = str(enriched.get("classpath", ""))
        if classpath and "General Hardware" not in classpath:
            specific_classpath += 1

        attribute_count = validation.get("attribute_count", 0)
        attribute_sum += attribute_count
        if attribute_count > 0:
            with_attributes += 1

        # Split attribute values by provenance so the dashboard can show
        # "structured / evidence-backed / inferred" instead of one flat number.
        row_evidence = 0
        for attribute in enriched.get("attributes") or []:
            if str(attribute.get("evidence", "evidence")) == "inferred":
                inferred_values += 1
            else:
                evidence_values += 1
                row_evidence += 1
        if row_evidence:
            rows_with_evidence += 1

        tier = str(enriched.get("brand_match_tier") or "")
        brand = str(enriched.get("brand_name") or "")
        if brand:
            resolved_brand += 1
            if tier in _STRONG_BRAND_TIERS:
                strong_brand += 1

        lov = enriched.get("lov_compliance")
        if lov is not None:
            lov_sum += float(lov)
            lov_rows += 1

        if enriched.get("is_duplicate"):
            duplicates += 1


        confidence = float(result.get("confidence") or 0.0)
        confidence_sum += confidence
        for index, (low, high) in enumerate(bucket_ranges):
            if low <= confidence <= high:
                buckets[index] += 1
                break

        for reason in (result.get("review") or {}).get("reasons", []):
            key = _reason_bucket(reason)
            reason_counts[key] = reason_counts.get(key, 0) + 1

    histogram = [
        {"bucket": f"{low}-{high}" if low != high else f"{low}", "count": count}
        for (low, high), count in zip(bucket_ranges, buckets)
    ]
    reasons = sorted(
        ({"reason": k, "count": v} for k, v in reason_counts.items()),
        key=lambda item: item["count"],
        reverse=True,
    )

    return {
        "total": total,
        "success": success,
        "review": review,
        "errors": errors,
        "success_rate": _pct(success, total),
        "avg_confidence": round(confidence_sum / total, 2),
        "invoice_char_pass": _pct(invoice_char, total),
        "invoice_caps_pass": _pct(invoice_caps, total),
        "schema_mobile_pass": _pct(schema_mobile, total),
        "mobile_target_60_80_pass": _pct(mobile_target, total),
        "schema_pass_rate": _pct(schema_ok, total),
        "classpath_specific_rate": _pct(specific_classpath, total),
        # ---- attribute honesty: three tiers, not one flat number ----
        # structured = rows with >= 1 attribute (guaranteed, hence a tautology)
        # evidence   = rows with >= 1 attribute parsed from the supplier's text
        # inferred   = share of VALUES derived from our own taxonomy
        "attribute_coverage": _pct(with_attributes, total),
        "attribute_structured_rate": _pct(with_attributes, total),
        "attribute_evidence_rate": _pct(rows_with_evidence, total),
        "attribute_values_total": evidence_values + inferred_values,
        "attribute_evidence_values": evidence_values,
        "attribute_inferred_values": inferred_values,
        "attribute_evidence_value_rate": _pct(
            evidence_values, evidence_values + inferred_values
        ),
        "avg_attributes": round(attribute_sum / total, 2),
        "avg_evidence_attributes": round(evidence_values / total, 2),
        # ---- brand evidence strength ----
        "brand_resolved_rate": _pct(resolved_brand, total),
        "brand_strong_evidence_rate": _pct(strong_brand, total),
        # ---- LOV compliance: None when no LOV file is loaded, never a fake 0% ----
        "lov_measurable": lov_rows > 0,
        "lov_compliance_rate": round(lov_sum / lov_rows * 100, 2) if lov_rows else None,
        "lov_rows_measured": lov_rows,
        # ---- de-duplication ----
        "duplicate_rows": duplicates,
        "duplicate_rate": _pct(duplicates, total),
        "confidence_histogram": histogram,
        "review_reasons": reasons,
        "status_distribution": [
            {"status": "success", "count": success},
            {"status": "review", "count": review},
            {"status": "error", "count": errors},
        ],
    }


def _reason_bucket(reason: str) -> str:
    """Collapses parameterised reasons so counts group sensibly."""
    text = str(reason)
    if "INVOICE_DESC exceeds" in text:
        return "Invoice description over 40 characters"
    if "not uppercase" in text:
        return "Invoice description not uppercase"
    if "MOBILE_DESC" in text:
        return "Mobile description outside target window"
    if "No technical attributes" in text or "no attributes" in text.lower():
        return "No technical attributes extracted"
    if "classpath" in text.lower():
        return "Generic taxonomy fallback"
    if "failed" in text.lower():
        return "Processing error"
    if "schema" in text.lower():
        return "Schema validation failure"
    return text


def _normalize(value: Any) -> str:
    """Case/space/punctuation-insensitive form for forgiving field comparison."""
    text = str(value or "").lower().replace("®", "").replace("™", "")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def compute_benchmark(
    results: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Field-level comparison of generated rows against labelled delivery rows."""
    truth_by_mpn = {
        str(row.get("Mfg_Part_Num", "")).strip().upper(): row
        for row in ground_truth
        if str(row.get("Mfg_Part_Num", "")).strip()
    }

    matched: List[tuple[Dict[str, Any], Dict[str, Any]]] = []
    for result in results:
        mpn = str((result.get("enriched") or {}).get("mfg_part_num", "")).strip().upper()
        if mpn in truth_by_mpn:
            matched.append((result, truth_by_mpn[mpn]))

    fields = []
    for column, record_key in BENCHMARK_FIELDS.items():
        exact = normalized = comparable = 0
        for result, truth in matched:
            expected = str(truth.get(column, "") or "")
            actual = str((result.get("enriched") or {}).get(record_key, "") or "")
            if not expected:
                continue
            comparable += 1
            if expected == actual:
                exact += 1
                normalized += 1
            elif _normalize(expected) == _normalize(actual):
                normalized += 1
        fields.append(
            {
                "field": column,
                "compared": comparable,
                "exact_match_rate": _pct(exact, comparable),
                "normalized_match_rate": _pct(normalized, comparable),
            }
        )

    scored = [f for f in fields if f["compared"]]
    overall = round(sum(f["normalized_match_rate"] for f in scored) / len(scored), 2) if scored else 0.0

    # No ground-truth row matched: return None (contract) so the dashboard hides
    # the panel instead of rendering a fabricated scorecard of zeros.
    if not matched:
        return None

    return {
        "ground_truth_rows": len(truth_by_mpn),
        "matched_rows": len(matched),
        "fields": fields,
        "overall_normalized_match_rate": overall,
    }
