"""Metrics and benchmark unit tests — denominators and contract buckets."""

from __future__ import annotations

from member3.backend.services.metrics_service import compute_benchmark, compute_metrics


def _result(status, confidence, *, invoice_char=True, invoice_caps=True, mobile_schema=True,
            mobile_target=True, schema_valid=True, attributes=1, classpath="A>B>C",
            reasons=(), categories=()):
    return {
        "status": status,
        "confidence": confidence,
        "enriched": {"classpath": classpath},
        "validation": {
            "invoice_char_pass": invoice_char,
            "invoice_caps": invoice_caps,
            "schema_mobile_pass": mobile_schema,
            "mobile_target_pass": mobile_target,
            "schema_valid": schema_valid,
            "attribute_count": attributes,
        },
        "review": {"reasons": list(reasons), "categories": list(categories)},
    }


def test_histogram_uses_contract_buckets():
    metrics = compute_metrics([
        _result("success", 0.0),
        _result("success", 59.0),
        _result("success", 60.0),
        _result("success", 79.0),
        _result("success", 80.0),
        _result("success", 89.0),
        _result("success", 90.0),
        _result("success", 99.0),
        _result("success", 100.0),
    ])
    buckets = {entry["bucket"]: entry["count"] for entry in metrics["confidence_histogram"]}
    assert list(buckets) == ["0-59", "60-79", "80-89", "90-99", "100"]
    assert buckets["0-59"] == 2
    assert buckets["60-79"] == 2
    assert buckets["80-89"] == 2
    assert buckets["90-99"] == 2
    assert buckets["100"] == 1


def test_confidence_100_lands_in_dedicated_bucket():
    metrics = compute_metrics([_result("success", 100.0)])
    buckets = {entry["bucket"]: entry["count"] for entry in metrics["confidence_histogram"]}
    assert buckets["100"] == 1
    assert buckets["90-99"] == 0


def test_mobile_schema_rate_uses_validation_flags_not_lengths():
    # A row whose mobile failed schema counts against schema_mobile_pass.
    metrics = compute_metrics([
        _result("success", 100.0, mobile_schema=True),
        _result("review", 50.0, mobile_schema=False),
    ])
    assert metrics["schema_mobile_pass"] == 50.0


def test_denominators_are_total_rows():
    results = [
        _result("success", 100.0),
        _result("review", 60.0, mobile_target=False),
        _result("error", 0.0, invoice_char=False, invoice_caps=False, mobile_schema=False,
                mobile_target=False, schema_valid=False, attributes=0, classpath=""),
    ]
    metrics = compute_metrics(results)
    assert metrics["total"] == 3
    assert metrics["success"] == 1
    assert metrics["review"] == 1
    assert metrics["errors"] == 1
    assert metrics["success_rate"] == round(1 / 3 * 100, 2)
    assert metrics["invoice_char_pass"] == round(2 / 3 * 100, 2)
    assert metrics["invoice_caps_pass"] == round(2 / 3 * 100, 2)
    assert metrics["schema_mobile_pass"] == round(2 / 3 * 100, 2)
    assert metrics["mobile_target_60_80_pass"] == round(1 / 3 * 100, 2)
    assert metrics["schema_pass_rate"] == round(2 / 3 * 100, 2)
    assert metrics["classpath_specific_rate"] == round(2 / 3 * 100, 2)
    assert metrics["attribute_coverage"] == round(2 / 3 * 100, 2)
    assert metrics["avg_confidence"] == round((100 + 60 + 0) / 3, 2)


def test_empty_input_metrics():
    metrics = compute_metrics([])
    assert metrics["total"] == 0
    assert metrics["success_rate"] == 0.0
    assert metrics["confidence_histogram"] == []
    assert metrics["status_distribution"] == []


def test_benchmark_none_when_no_match():
    results = [_result("success", 100.0)]
    assert compute_benchmark(results, []) is None
    assert compute_benchmark(results, [{"Mfg_Part_Num": "OTHER"}]) is None


def test_benchmark_matches_and_reports_fields():
    results = [{
        "status": "success",
        "confidence": 100.0,
        "enriched": {
            "mfg_part_num": "ABC1",
            "manufacturer_name": "Acme",
            "brand_name": "Acme®",
            "classpath": "A>B>C",
            "unspsc": "123",
            "product_name": "Widget",
            "invoice_desc": "WIDGET",
            "mobile_desc": "Acme Widget ABC1",
            "short_desc": "s",
            "long_desc1": "l",
            "retail_desc": "r",
        },
        "validation": {},
        "review": {"reasons": [], "categories": []},
    }]
    truth = [{
        "Mfg_Part_Num": "abc1",
        "MANUFACTURER_NAME": "ACME",
        "BRAND_NAME": "acme",
        "MANUFACTURER_PART_NUMBER": "ABC1",
        "Classpath": "A>B>C",
        "UNSPSC": "123",
        "Product Name": "Widget",
        "INVOICE_DESC": "widget",
        "MOBILE_DESC": "Acme Widget ABC1",
        "SHORT_DESC": "s",
        "LONG_DESC1": "l",
        "RETAIL_DESC": "r",
    }]
    benchmark = compute_benchmark(results, truth)
    assert benchmark is not None
    assert benchmark["ground_truth_rows"] == 1
    assert benchmark["matched_rows"] == 1
    by_field = {entry["field"]: entry for entry in benchmark["fields"]}
    # Manufacturer differs in case only -> exact 0, normalized 100.
    assert by_field["MANUFACTURER_NAME"]["exact_match_rate"] == 0.0
    assert by_field["MANUFACTURER_NAME"]["normalized_match_rate"] == 100.0
    assert by_field["BRAND_NAME"]["normalized_match_rate"] == 100.0
    assert by_field["Product Name"]["normalized_match_rate"] == 100.0