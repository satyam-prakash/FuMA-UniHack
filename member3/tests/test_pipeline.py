"""Tests for the M1 -> M2 row pipeline."""

import csv
from pathlib import Path

from member3.backend.services import pipeline_service
from member3.backend.services.pipeline_service import (
    REQUIRED_INPUT_COLUMNS,
    enrich_raw_row,
    validate_input_columns,
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
    assert result["status"] in {"success", "review"}
    assert result["normalized"]["BRAND_NAME"] == "FRIGIDAIRE®"
    assert result["enriched"]["manufacturer_name"] == "Rheem Manufacturing"
    assert result["validation"]["invoice_len"] <= 40
    assert result["validation"]["invoice_caps"] is True
    assert result["validation"]["schema_valid"] is True


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

    monkeypatch.setattr(pipeline_service._M1_STAGE, "process_item", explode)

    result = enrich_raw_row(DISHWASHER, row_id=2)

    assert result["status"] == "error"
    assert result["enriched"] == {}
    assert result["normalized"] == {}
    assert "m1 down" in " | ".join(result["review"]["reasons"])


def test_validate_input_columns():
    assert validate_input_columns(list(REQUIRED_INPUT_COLUMNS)) == []

    partial = [c for c in REQUIRED_INPUT_COLUMNS if c not in ("Part_Desc", "DIB_Brand")]
    assert validate_input_columns(partial) == ["Part_Desc", "DIB_Brand"]

    assert validate_input_columns([c.lower() for c in REQUIRED_INPUT_COLUMNS]) == []


def test_all_result_keys_present():
    result = enrich_raw_row(DISHWASHER, row_id=3)

    assert set(result) == {
        "row_id",
        "status",
        "raw",
        "normalized",
        "enriched",
        "validation",
        "review",
        "confidence",
    }
    assert set(result["validation"]) == {
        "schema_valid",
        "errors",
        "invoice_len",
        "invoice_caps",
        "mobile_len",
        "schema_mobile_pass",
        "mobile_target_pass",
        "attribute_count",
    }
    assert set(result["review"]) == {"needs_review", "reasons", "decision", "comment"}


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
