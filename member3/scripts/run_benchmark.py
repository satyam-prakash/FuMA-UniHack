"""
FuMA accuracy and compliance scorecard.

Runs the full Member 1 -> Member 2 -> Member 3 pipeline over the sample dataset
and prints the benchmark report used in the pitch deck.

Usage::

    .venv/bin/python -m member3.scripts.run_benchmark
    .venv/bin/python -m member3.scripts.run_benchmark --limit 200
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from member3.backend.services.metrics_service import compute_benchmark, compute_metrics
from member3.backend.services.pipeline_service import enrich_raw_row
from member3.delivery.columns import DELIVERY_COLUMNS
from member3.delivery.mapper import map_record_to_delivery
from member3.delivery.validators import check_delivery

DATA = Path(__file__).resolve().parents[1] / "data"
LINE = "=" * 58
THIN = "-" * 58


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
    print("           FuMA ACCURACY BENCHMARK REPORT")
    print(LINE)
    print(f"Rows processed:                     {metrics['total']}")
    print(f"Elapsed:                            {elapsed:.2f}s ({metrics['total'] / max(elapsed, 1e-9):.0f} rows/s)")
    print(THIN)
    print(f"1. Invoice Desc (<=40 chars):       {metrics['invoice_char_pass']:.1f}%  {_verdict(metrics['invoice_char_pass'], 100)}")
    print(f"2. Invoice Desc (ALL CAPS):         {metrics['invoice_caps_pass']:.1f}%  {_verdict(metrics['invoice_caps_pass'], 100)}")
    print(f"3. Mobile Desc (schema <=85):       {metrics['schema_mobile_pass']:.1f}%  {_verdict(metrics['schema_mobile_pass'], 90)}")
    print(f"4. Mobile Desc (target 60-80):      {metrics['mobile_target_60_80_pass']:.1f}%  {_verdict(metrics['mobile_target_60_80_pass'], 90)}")
    print(f"5. Pydantic schema validation:      {metrics['schema_pass_rate']:.1f}%  {_verdict(metrics['schema_pass_rate'], 100)}")
    print(f"6. Specific classpath (non-generic):{metrics['classpath_specific_rate']:6.1f}%  {_verdict(metrics['classpath_specific_rate'], 95)}")
    print(f"7. Attribute coverage:              {metrics['attribute_coverage']:.1f}%  {_verdict(metrics['attribute_coverage'], 90)}")
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
    print(f"Ground-truth rows available:        {benchmark['ground_truth_rows'] if benchmark else 0}")
    print(f"Ground-truth rows matched:          {benchmark['matched_rows'] if benchmark else 0}")
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
        for reason in metrics["review_reasons"][:5]:
            print(f"  {reason['count']:>5}  {reason['reason']}")
    print(LINE)


if __name__ == "__main__":
    main()
