"""
FuMA accuracy and compliance scorecard.

Runs the full Member 1 -> Member 2 -> Member 3 pipeline over the sample dataset
and prints the benchmark report used in the pitch deck.

REPORTING POLICY
----------------
This report is deliberately written to be falsifiable. Anyone can run it and get
the same numbers, so it must not overstate anything:

* Reference-data provenance is printed FIRST. If a vocabulary fell back to the
  built-in seed list instead of the supplied master file, that is stated plainly
  rather than left implied.
* LOV compliance prints "not measurable" when no LOV file is loaded, never 0%.
* Attribute coverage is split three ways (structured / evidence-backed /
  inferred) because "100% coverage" is a tautology on its own -- the pipeline
  guarantees at least one attribute per classified row.
* Ground-truth row count is printed, so a 100% match on n=2 cannot be mistaken
  for a 100% match on n=200.

Usage::

    python -m member3.scripts.run_benchmark
    python -m member3.scripts.run_benchmark --limit 200
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from fuma_rules.deduplication import detect_duplicates, duplicate_summary
from fuma_rules.reference_data import provenance_report
from member3.backend.services.metrics_service import compute_benchmark, compute_metrics
from member3.backend.services.pipeline_service import enrich_raw_row
from member3.delivery.columns import DELIVERY_COLUMNS
from member3.delivery.mapper import map_record_to_delivery
from member3.delivery.validators import check_delivery

if sys.platform == "win32":  # keep ®/™ intact in the console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA = Path(__file__).resolve().parents[1] / "data"
LINE = "=" * 62
THIN = "-" * 62


def _verdict(value: float, target: float) -> str:
    return "[PASS]" if value >= target else "[CHECK]"


def main() -> None:
    parser = argparse.ArgumentParser(description="FuMA accuracy benchmark")
    parser.add_argument("--limit", type=int, default=0, help="only process the first N rows")
    args = parser.parse_args()

    with (DATA / "sample_input_1000.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if args.limit:
        rows = rows[: args.limit]

    # Stage 0: de-duplication. Flags only -- rows are never dropped, so the
    # delivery file still reconciles with the client's input.
    rows = detect_duplicates(rows)
    dupes = duplicate_summary(rows)

    started = time.time()
    results = [enrich_raw_row(row, row_id=i) for i, row in enumerate(rows, start=1)]
    elapsed = time.time() - started

    metrics = compute_metrics(results)

    with (DATA / "expected_delivery_format.csv").open(newline="", encoding="utf-8-sig") as handle:
        ground_truth = list(csv.DictReader(handle))
    benchmark = compute_benchmark(results, ground_truth)

    delivery_rows = [
        map_record_to_delivery(r["enriched"], r.get("raw") or {})[0]
        for r in results
        if r.get("enriched")
    ]
    export_valid, export_errors = check_delivery(delivery_rows)

    print(LINE)
    print("            FuMA ACCURACY BENCHMARK REPORT")
    print(LINE)

    # ---- Reference data provenance, printed first and without spin ----
    prov = provenance_report()
    print("REFERENCE DATA PROVENANCE")
    print(f"  Directory:                        {prov['reference_dir']}")
    print(f"  Master files present:             {len(prov['files_present'])} of 7")
    for source in prov["sources"]:
        print(f"    {source['name']:<28} {source['status']:<14} {source['rows']:>7} rows")
    if prov["files_missing"]:
        print("  NOTE: vocabularies marked SEED FALLBACK use a curated built-in list,")
        print("        not the supplied master file. Drop the pack into reference_data/")
        print("        to activate full master-data coverage.")
    print(THIN)

    print(f"Rows processed:                     {metrics['total']}")
    print(f"Elapsed:                            {elapsed:.2f}s ({metrics['total'] / max(elapsed, 1e-9):.0f} rows/s)")
    print(THIN)
    print("FORMAT COMPLIANCE")
    print(f"1. Invoice Desc (<=40 chars):       {metrics['invoice_char_pass']:.1f}%  {_verdict(metrics['invoice_char_pass'], 100)}")
    print(f"2. Invoice Desc (ALL CAPS):         {metrics['invoice_caps_pass']:.1f}%  {_verdict(metrics['invoice_caps_pass'], 100)}")
    print(f"3. Mobile Desc (schema <=85):       {metrics['schema_mobile_pass']:.1f}%  {_verdict(metrics['schema_mobile_pass'], 90)}")
    print(f"4. Mobile Desc (target 60-80):      {metrics['mobile_target_60_80_pass']:.1f}%  {_verdict(metrics['mobile_target_60_80_pass'], 90)}")
    print(f"5. Pydantic schema validation:      {metrics['schema_pass_rate']:.1f}%  {_verdict(metrics['schema_pass_rate'], 100)}")
    print(f"6. Specific classpath:              {metrics['classpath_specific_rate']:.1f}%  {_verdict(metrics['classpath_specific_rate'], 95)}")
    print(THIN)
    print("ATTRIBUTE COVERAGE (three tiers, deliberately)")
    print(f"  Structured (>=1 attribute):       {metrics['attribute_structured_rate']:.1f}%  <- tautological on its own")
    print(f"  Evidence-backed (>=1 parsed):     {metrics['attribute_evidence_rate']:.1f}%  <- the honest number")
    print(f"  Values total:                     {metrics['attribute_values_total']}")
    print(f"    evidence-backed:                {metrics['attribute_evidence_values']} ({metrics['attribute_evidence_value_rate']:.1f}%)")
    print(f"    inferred from taxonomy:         {metrics['attribute_inferred_values']}")
    print(f"  Avg evidence attributes/row:      {metrics['avg_evidence_attributes']:.2f}")
    print(THIN)
    print("ENTITY RESOLUTION")
    print(f"  Brand resolved:                   {metrics['brand_resolved_rate']:.1f}%")
    print(f"  Brand on STRONG evidence:         {metrics['brand_strong_evidence_rate']:.1f}%")
    print("  (weak-evidence brands are capped below the review threshold so they")
    print("   land in the human queue instead of shipping as a clean success)")
    print(THIN)
    print("LOV COMPLIANCE (constrained vocabulary)")
    if metrics["lov_measurable"]:
        rate = metrics["lov_compliance_rate"]
        print(f"  Values found in approved LOV:     {rate:.1f}%  {_verdict(rate, 90)}")
        print(f"  Rows measured:                    {metrics['lov_rows_measured']}")
    else:
        print("  NOT MEASURABLE - no LOV file loaded.")
        print("  Reported as unmeasurable rather than 0%: scoring our own seed")
        print("  vocabulary against itself would prove nothing.")
    print(THIN)
    print("DE-DUPLICATION (flag, never delete)")
    print(f"  Duplicate rows flagged:           {dupes['duplicate_rows']}")
    print(f"    exact MPN matches:              {dupes['exact_mpn_duplicates']}")
    print(f"    same description+manufacturer:  {dupes['similar_description_duplicates']}")
    print(f"  Unique rows:                      {dupes['unique_rows']}")
    print(THIN)
    print(f"Success rows:                       {metrics['success']}")
    print(f"Needs human review:                 {metrics['review']}")
    print(f"Processing errors:                  {metrics['errors']}")
    print(f"Average confidence:                 {metrics['avg_confidence']:.2f}")
    print(THIN)
    print(f"Delivery columns:                   {len(DELIVERY_COLUMNS)}  {_verdict(len(DELIVERY_COLUMNS), 252)}")
    print(f"Delivery rows validated:            {len(delivery_rows)}")
    print(f"Delivery schema valid:              {export_valid}")
    print(THIN)
    gt_rows = benchmark["ground_truth_rows"] if benchmark else 0
    print(f"Ground-truth rows available:        {gt_rows}")
    print(f"Ground-truth rows matched:          {benchmark['matched_rows'] if benchmark else 0}")
    if gt_rows and gt_rows < 20:
        print(f"  CAVEAT: n={gt_rows} is too small to generalise. The challenge pack")
        print("  supplies 200 labelled rows; only these are present in the repo, so")
        print("  every field rate below is a small-sample indication, not an accuracy")
        print("  claim. Add the full file to reference_data/ to score properly.")
    if benchmark and benchmark["matched_rows"]:
        print(f"{'FIELD':<30}{'EXACT':>10}{'NORMALIZED':>14}")
        for field in benchmark["fields"]:
            if not field["compared"]:
                continue
            print(f"{field['field']:<30}{field['exact_match_rate']:>9.1f}%{field['normalized_match_rate']:>13.1f}%")
        print(f"Overall normalized match rate:      {benchmark['overall_normalized_match_rate']:.1f}%")
    else:
        print("No ground-truth row matched; benchmark withheld (not a zero scorecard).")
    print(THIN)
    if metrics["review_reasons"]:
        print("Top review reasons:")
        for reason in metrics["review_reasons"][:6]:
            print(f"  {reason['count']:>5}  {reason['reason']}")
    print(LINE)


if __name__ == "__main__":
    main()
