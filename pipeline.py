"""
FuMA Master Unified Pipeline
Ties together:
- Member 1: fuma_rules (Master Data, Sanitization, Brand Matching, UOMs)
- Member 2: fuma_engine (Taxonomy Classification, LOV Attribute Extraction, Description Formulas)
- Member 3: member3 (252-Column Delivery Mapping, Validation, CSV/XLSX Export)
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from typing import Dict, Any, List, Optional
import pandas as pd

from member3.backend.services.pipeline_service import enrich_raw_row, default_pipeline
from member3.delivery.csv_exporter import rows_to_csv_bytes
from member3.delivery.xlsx_exporter import rows_to_xlsx_bytes
from member3.backend.services.metrics_service import compute_metrics, compute_benchmark

def process_single_item(raw_dict: Dict[str, Any], row_id: int = 1) -> Dict[str, Any]:
    """
    Runs a single raw item through Member 1 -> Member 2 -> Member 3.
    """
    return enrich_raw_row(raw_dict, row_id=row_id)

def process_batch(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Runs a list of raw items through the full pipeline.
    """
    return [enrich_raw_row(item, row_id=i) for i, item in enumerate(items, start=1)]

def process_csv_file(input_csv_path: str, output_csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Reads a raw CSV file, enriches all items, and optionally exports to 252-column delivery CSV.
    """
    df = pd.read_csv(input_csv_path, encoding="utf-8-sig")
    results = process_batch(df.to_dict(orient="records"))
    
    if output_csv_path:
        delivery_rows = [r["delivery_row"] for r in results if r.get("delivery_row")]
        csv_bytes = rows_to_csv_bytes(delivery_rows)
        with open(output_csv_path, "wb") as f:
            f.write(csv_bytes)
            
    return results

if __name__ == "__main__":
    print("=" * 70)
    print("FUMA INTEGRATED 3-MEMBER PIPELINE TEST")
    print("=" * 70)
    
    sample = {
        "Mfg_Part_Num": "PDSH4816AF",
        "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only 120V 15A 50-1/4IN Leg Mounting With CleanBoost 5-Wash Cycle 47 dBA",
        "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
        "E1_Brand": "-- Unbranded --"
    }
    
    result = process_single_item(sample)
    print(f"Status:         {result['status']}")
    print(f"Brand:          {result['brand_name']}")
    print(f"Classpath:      {result['classpath']}")
    print(f"INVOICE_DESC:   {result['enriched']['invoice_desc']}")
    print(f"MOBILE_DESC:    {result['enriched']['mobile_desc']}")
    print(f"SHORT_DESC:     {result['enriched']['short_desc']}")
    print(f"Delivery Cols:  {len(result['delivery_row'])} columns mapped")
    print("=" * 70)
