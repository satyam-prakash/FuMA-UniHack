"""
CLI Runner for Industrial Product Catalog Normalization & Benchmarking Engine.
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
"""

import os
import sys
import csv

# Ensure UTF-8 output encoding on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fuma_rules import MasterDataPipelineStage, GroundTruthBenchmark


def run_benchmark():
    input_csv = os.path.join("Probelm_statement", "Unihack_ Sample Dataset - Input.csv")
    gt_csv = os.path.join("Probelm_statement", "Unihack_ Expected Output - Delivery Format.csv")

    print("=" * 70)
    print("UNIHACK CATALOG ENRICHMENT ENGINE - MEMBER 1 BENCHMARK")
    print("=" * 70)

    # 1. Initialize Stage 1 Master Data Pipeline
    stage1 = MasterDataPipelineStage()

    # 2. Ingest Sample Input Items
    print(f"\n[+] Ingesting sample input dataset: {input_csv}")
    raw_items = []
    if os.path.exists(input_csv):
        with open(input_csv, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_items.append(row)
    print(f"    Loaded {len(raw_items)} raw catalog items.")

    # 3. Execute Normalization Pipeline on sample items
    print("\n[+] Processing Master Data Normalization (Sanitization, Brand/Mfg, UOM)...")
    normalized_records = stage1.process_batch(raw_items[:20])

    print("\n[+] Sample Normalized Records (First 5):")
    for i, item in enumerate(normalized_records[:5], 1):
        print(f"\n  [{i}] MPN: {item.get('MANUFACTURER_PART_NUMBER')}")
        print(f"      Raw Desc : {item.get('Part_Desc')}")
        print(f"      Cleaned  : {item.get('CLEAN_DESC')}")
        print(f"      Mfg      : {item.get('MANUFACTURER_NAME')}")
        print(f"      Brand    : {item.get('BRAND_NAME')}")

    # 4. Evaluate against Ground Truth Benchmark
    if os.path.exists(gt_csv):
        print(f"\n[+] Evaluating against Ground Truth Benchmark: {gt_csv}")
        benchmark = GroundTruthBenchmark(ground_truth_path=gt_csv)
        
        # Test evaluation with ground truth rows
        gt_sample_predictions = stage1.process_batch(benchmark.ground_truth_records)
        results = benchmark.evaluate_batch(gt_sample_predictions)
        
        print("\n[+] BENCHMARK RESULTS:")
        print(f"    * Total Evaluated Items       : {results['total_evaluated']}")
        print(f"    * Manufacturer Match Accuracy : {results['mfg_accuracy_pct']}%")
        print(f"    * Brand Match Accuracy (®, ™)  : {results['brand_accuracy_pct']}%")
        print(f"    * Avg Row Confidence Score     : {results['avg_confidence_score_pct']}%")
        print(f"    * Review Queue Trigger Rate   : {results['review_rate_pct']}%")

    print("\n" + "=" * 70)
    print(">>> Member 1 Normalization & Benchmark Engine Ready!")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
