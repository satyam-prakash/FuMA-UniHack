"""Full 1,000-row metrics scorecard."""
import csv, sys
sys.stdout.reconfigure(encoding="utf-8")
from member3.backend.services.pipeline_service import enrich_raw_row
from member3.backend.services.metrics_service import compute_metrics

rows = list(csv.DictReader(open("member3/data/sample_input_1000.csv", encoding="utf-8-sig")))
results = [enrich_raw_row(r, row_id=i) for i, r in enumerate(rows, 1)]
m = compute_metrics(results)

print("=" * 70)
print("FULL 1,000-ROW METRICS SCORECARD")
print("=" * 70)
for key in [
    "total", "success", "review", "errors", "success_rate",
    "avg_confidence", "invoice_char_pass", "invoice_caps_pass",
    "schema_mobile_pass", "mobile_target_60_80_pass",
    "schema_pass_rate", "classpath_specific_rate",
    "attribute_coverage", "avg_attributes",
]:
    val = m[key]
    suffix = "%" if "rate" in key or "pass" in key or "coverage" in key else ""
    print(f"  {key:30s}: {val}{suffix}")
print("=" * 70)
print()
print("CONFIDENCE HISTOGRAM:")
for b in m["confidence_histogram"]:
    bar = "#" * (b["count"] // 5)
    print(f"  {b['bucket']:>6s}: {b['count']:>4d} {bar}")
print()
print("REVIEW REASONS (top 10):")
for r in m["review_reasons"][:10]:
    print(f"  {r['count']:>4d} x {r['reason']}")

# Check 252-column delivery output
print()
print("DELIVERY COLUMN CHECK:")
dr = results[0].get("delivery_row") or {}
print(f"  Columns in delivery row: {len(dr)}")
assert len(dr) == 252, f"Expected 252 columns, got {len(dr)}"
print("  252-column contract: PASS")
