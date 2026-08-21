"""Tests for the M1 -> M2 row pipeline."""

import csv
from pathlib import Path

import pytest

from member3.backend.services import pipeline_service
from member3.backend.services.batch_service import JobStore
from member3.backend.services.pipeline_service import (
    REQUIRED_INPUT_COLUMNS,
    REQUIRED_ROW_FIELDS,
    enrich_raw_row,
    validate_input_columns,
    validation_flags,
)

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "sample_input_1000.csv"

DISHWASHER = {
    "Mfg_Part_Num": "PDSH4816AF",
    "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
    "E1_Brand": "-- Unbranded --",
    "Unilog_Brand": "-- No Unilog Brand --",
    "DIB_Brand": "-- No DIB Brand --",
    "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
}


def test_happy_path_dishwasher():
    result = enrich_raw_row(DISHWASHER, row_id=7)

    assert result["row_id"] == 7
    assert result["status"] == "success"
    assert result["normalized"]["BRAND_NAME"] == "FRIGIDAIRE®"
    assert result["enriched"]["manufacturer_name"] == "Rheem Manufacturing"
    assert result["validation"]["invoice_len"] <= 40
    assert result["validation"]["invoice_caps"] is True
    assert result["validation"]["schema_valid"] is True
    assert result["review"]["needs_review"] is False
    assert result["review"]["reasons"] == []
    assert result["confidence"] == 100.0


def test_m2_failure_is_isolated(monkeypatch):
    def explode(_normalized):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_service, "enrich_single_item", explode)

    result = enrich_raw_row(DISHWASHER, row_id=1)

    assert result["status"] == "error"
    assert result["enriched"] == {}
    assert "boom" in " | ".join(result["review"]["reasons"])
    assert result["review"]["needs_review"] is True
    assert result["confidence"] == 0.0


def test_m1_failure_is_isolated(monkeypatch):
    def explode(_raw):
        raise ValueError("m1 down")

    monkeypatch.setattr(
        pipeline_service.default_pipeline().master_data, "process_item", explode
    )

    result = enrich_raw_row(DISHWASHER, row_id=2)

    assert result["status"] == "error"
    assert result["enriched"] == {}
    assert result["normalized"] == {}
    assert "m1 down" in " | ".join(result["review"]["reasons"])


def test_schema_failure_is_isolated(monkeypatch):
    real_enrich = pipeline_service.enrich_single_item

    def invalid(_normalized):
        record = real_enrich(_normalized)
        record["invoice_desc"] = "X" * 41  # breaks ProductRecord.max_length=40
        return record

    monkeypatch.setattr(pipeline_service, "enrich_single_item", invalid)

    result = enrich_raw_row(DISHWASHER, row_id=3)

    assert result["status"] == "error"
    assert result["error"]["stage"] == "schema"
    assert result["confidence"] == 0.0
    assert result["enriched"]["invoice_desc"]  # the offending record is kept for inspection


def test_mapper_failure_is_isolated(monkeypatch):
    def explode(_enriched, _raw):
        raise TypeError("mapper down")

    monkeypatch.setattr(pipeline_service, "map_record_to_delivery", explode)

    result = enrich_raw_row(DISHWASHER, row_id=4)

    assert result["status"] == "error"
    assert result["error"]["stage"] == "delivery"
    assert result["confidence"] == 0.0


def test_validate_input_columns():
    assert validate_input_columns(list(REQUIRED_INPUT_COLUMNS)) == []

    partial = [c for c in REQUIRED_INPUT_COLUMNS if c not in ("Part_Desc", "DIB_Brand")]
    assert validate_input_columns(partial) == ["Part_Desc", "DIB_Brand"]

    assert validate_input_columns([c.lower() for c in REQUIRED_INPUT_COLUMNS]) == []


def test_all_result_keys_present():
    result = enrich_raw_row(DISHWASHER, row_id=3)

    assert {
        "row_id",
        "status",
        "raw",
        "normalized",
        "enriched",
        "validation",
        "review",
        "confidence",
    } <= set(result)
    assert {
        "schema_valid",
        "invoice_len",
        "invoice_caps",
        "invoice_char_pass",
        "mobile_len",
        "schema_mobile_pass",
        "mobile_target_pass",
        "attribute_count",
    } <= set(result["validation"])
    assert {"needs_review", "reasons", "decision"} <= set(result["review"])


def test_batch_of_real_rows():
    with SAMPLE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for _, row in zip(range(25), csv.DictReader(handle))]
    assert len(rows) == 25

    results = [enrich_raw_row(row, row_id=i) for i, row in enumerate(rows, start=1)]

    assert len(results) == 25
    for result in results:
        assert result["status"] in {"success", "review", "error"}
        if result["status"] != "error":
            assert result["enriched"]["invoice_desc"]


# --- required field validation -----------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("Mfg_Part_Num", None),
        ("Mfg_Part_Num", ""),
        ("Mfg_Part_Num", "   "),
        ("Part_Desc", None),
        ("Part_Desc", ""),
        ("Part_Desc", "\t "),
        ("Part_Manuf", None),
        ("Part_Manuf", ""),
        ("Part_Manuf", "  "),
    ],
    ids=[
        "mpn-none",
        "mpn-empty",
        "mpn-whitespace",
        "desc-none",
        "desc-empty",
        "desc-whitespace",
        "manuf-none",
        "manuf-empty",
        "manuf-whitespace",
    ],
)
def test_blank_required_field_never_succeeds(field, value):
    raw = dict(DISHWASHER)
    raw[field] = value
    result = enrich_raw_row(raw, row_id=5)

    assert result["status"] == "review"
    assert result["review"]["needs_review"] is True
    assert result["confidence"] == 0.0
    assert "missing_required_field" in result["review"]["categories"]
    assert field in " | ".join(result["review"]["reasons"])
    assert result["enriched"] == {}
    assert result["delivery_row"] is None


def test_missing_required_key_never_succeeds():
    raw = dict(DISHWASHER)
    del raw["Mfg_Part_Num"]
    result = enrich_raw_row(raw, row_id=6)

    assert result["status"] == "review"
    assert result["review"]["needs_review"] is True
    assert result["confidence"] == 0.0
    assert "Mfg_Part_Num" in " | ".join(result["review"]["reasons"])


def test_blank_optional_brand_fields_still_pass():
    raw = dict(DISHWASHER)
    raw["E1_Brand"] = raw["Unilog_Brand"] = raw["DIB_Brand"] = ""
    result = enrich_raw_row(raw, row_id=7)
    assert result["status"] == "success"


def test_required_row_fields_constant():
    assert REQUIRED_ROW_FIELDS == ("Mfg_Part_Num", "Part_Desc", "Part_Manuf")


# --- review queue semantics --------------------------------------------------


def test_review_policy_needs_review_iff_reasons():
    """Queue membership is exactly ``bool(review.reasons)`` — a reason can never
    exist on a row that is not in the queue, and a queued row always explains."""
    with SAMPLE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for _, row in zip(range(40), csv.DictReader(handle))]

    results = [enrich_raw_row(row, row_id=i) for i, row in enumerate(rows, start=1)]
    for result in results:
        assert result["review"]["needs_review"] == bool(result["review"]["reasons"])
        if result["status"] == "success":
            assert result["review"]["needs_review"] is False
        if result["status"] == "review":
            assert result["review"]["needs_review"] is True


def test_review_queue_membership_matches_needs_review():
    with SAMPLE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for _, row in zip(range(40), csv.DictReader(handle))]

    store = JobStore()
    job = store.create_job("q.csv", rows)
    store.run_job(job["job_id"])
    job = store.get(job["job_id"])

    queue = store.review_rows(job["job_id"])
    queued_ids = {entry["row_id"] for entry in queue}
    expected = {
        r["row_id"] for r in job["results"] if r["review"]["needs_review"] or r["status"] == "error"
    }
    assert queued_ids == expected
    assert all(entry["decision"] is None for entry in queue)
    assert all(entry["status"] in {"review", "error"} for entry in queue)


def test_approved_row_leaves_queue_and_keeps_decision():
    with SAMPLE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for _, row in zip(range(10), csv.DictReader(handle))]

    store = JobStore()
    job = store.create_job("q2.csv", rows)
    store.run_job(job["job_id"])
    target = next(r for r in store.get(job["job_id"])["results"] if r["status"] == "review")

    updated = store.set_review(job["job_id"], target["row_id"], "approve", "looks good")
    assert updated["review"]["needs_review"] is False
    assert updated["review"]["decision"]["action"] == "approve"
    assert updated["review"]["decision"]["comment"] == "looks good"
    assert "at" in updated["review"]["decision"]

    queued_ids = {entry["row_id"] for entry in store.review_rows(job["job_id"])}
    assert target["row_id"] not in queued_ids


# --- mobile validation semantics ---------------------------------------------


@pytest.mark.parametrize(
    "length,schema_pass,target_pass",
    [
        (0, False, False),
        (39, True, False),
        (40, True, False),
        (59, True, False),
        (60, True, True),
        (80, True, True),
        (81, True, False),
        (85, True, False),
        (86, False, False),
    ],
)
def test_mobile_boundaries(length, schema_pass, target_pass):
    flags = validation_flags({"mobile_desc": "m" * length})
    assert flags["schema_mobile_pass"] is schema_pass, f"len={length} schema"
    assert flags["mobile_target_pass"] is target_pass, f"len={length} target"


def test_empty_mobile_does_not_count_as_schema_pass():
    flags = validation_flags({})
    assert flags["schema_mobile_pass"] is False
    assert flags["mobile_target_pass"] is False


def test_mobile_schema_and_target_stay_independent():
    flags = validation_flags({"mobile_desc": "m" * 70})
    assert flags["schema_mobile_pass"] is True
    assert flags["mobile_target_pass"] is True
