# 📦 `fuma_rules` — Master Data, Normalization & Evaluation Package

> **Developed by Member 1 (Master Data, Normalization & Evaluation Lead)**  
> This package provides all data cleaning, brand/manufacturer resolution with legal trademarks (`®`, `™`), master UOM/fraction standards, and ground truth scoring for the FuMA pipeline.

---

## 🚀 Quick Usage for Teammates (Member 2 & Member 3)

### 1. Ingest & Normalize Master Data (Stage 1)
```python
from fuma_rules import MasterDataPipelineStage

stage1 = MasterDataPipelineStage()

raw_row = {
    "Mfg_Part_Num": "PDSH4816AF",
    "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
    "Part_Manuf": "Appliance Dealers Cooperative (APPDE)"
}

normalized = stage1.process_item(raw_row)
print(normalized["MANUFACTURER_NAME"]) # "Rheem Manufacturing"
print(normalized["BRAND_NAME"])        # "FRIGIDAIRE®"
print(normalized["CLEAN_DESC"])         # "PDSH4816AF Dishwasher SS"
```

### 2. Standalone Normalizers
```python
from fuma_rules import (
    clean_placeholder,
    clean_supplier_name,
    resolve_brand_and_manufacturer,
    convert_decimal_to_fraction,
    normalize_uom,
    format_measurement
)

# Brand Resolution
brand_info = resolve_brand_and_manufacturer("Freud Inc (2435)", "DCB518ASTS06G Sanding Belt")
# -> {'manufacturer_name': 'Freud America, Inc.', 'brand_name': 'Diablo®'}

# UOM & Fractions
fraction = convert_decimal_to_fraction(50.25) # "50-1/4"
uom_std  = normalize_uom("24in")              # "24 in"
meas     = format_measurement(120, "volts")   # "120 V"
```

### 3. Ground-Truth Benchmarking (For Member 3 Dashboard)
```python
from fuma_rules import GroundTruthBenchmark

benchmark = GroundTruthBenchmark("Probelm_statement/Unihack_ Expected Output - Delivery Format.csv")
results = benchmark.evaluate_batch(predicted_records)
print(results["mfg_accuracy_pct"])
print(results["brand_accuracy_pct"])
print(results["avg_confidence_score_pct"])
```
