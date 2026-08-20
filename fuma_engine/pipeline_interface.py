"""
FuMA Pipeline Interface
Owned by Member 2.
Provides clean batch and single-item processing functions for Member 3 (API/UI) and Member 1 (Evaluator).
"""

from typing import Dict, List, Any
import pandas as pd
from fuma_engine.taxonomy_classifier import classify_taxonomy
from fuma_engine.attribute_extractor import extract_attributes
from fuma_engine.description_builder import build_all_descriptions
from fuma_engine.confidence_evaluator import evaluate_record
from fuma_engine.schema import ProductRecord

def enrich_single_item(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches a single raw product dictionary.
    
    Expected input keys (case-insensitive):
        - Mfg_Part_Num / mfg_part_num
        - Part_Desc / part_desc / part_desc_raw
        - Part_Manuf / manufacturer_name
        - E1_Brand / brand_name
    """
    mpn = str(raw_dict.get("Mfg_Part_Num") or raw_dict.get("mfg_part_num") or "").strip()
    raw_desc = str(raw_dict.get("Part_Desc") or raw_dict.get("part_desc") or raw_dict.get("part_desc_raw") or "").strip()
    mfg = str(raw_dict.get("MANUFACTURER_NAME") or raw_dict.get("Part_Manuf") or raw_dict.get("manufacturer_name") or "").strip()
    brand = str(raw_dict.get("BRAND_NAME") or raw_dict.get("E1_Brand") or raw_dict.get("brand_name") or "").strip()
    
    # 1. Step: Taxonomy Classification
    classpath, unspsc, product_name = classify_taxonomy(raw_desc, mpn)
    
    # 2. Step: Attribute Extraction
    extracted = extract_attributes(raw_desc, mpn, category=product_name)
    
    # Clean item dict for descriptions
    item_ctx = {
        "mfg_part_num": mpn,
        "part_desc_raw": raw_desc,
        "manufacturer_name": mfg,
        "brand_name": brand if brand and not brand.startswith("--") else mfg,
        "product_name": product_name,
        "classpath": classpath,
        "unspsc": unspsc
    }
    
    # 3. Step: Multi-Channel Description Generation
    descs = build_all_descriptions(item_ctx, extracted)
    
    # 4. Step: Quality & Confidence Scoring
    score, needs_review, reasons = evaluate_record(descs, extracted, classpath)
    
    # 5. Build Final Standard Record
    record = ProductRecord(
        mfg_part_num=mpn,
        part_desc_raw=raw_desc,
        manufacturer_name=mfg,
        brand_name=item_ctx["brand_name"],
        series=extracted.get("series", ""),
        classpath=classpath,
        unspsc=unspsc,
        product_name=product_name,
        attributes=extracted["attributes"],
        features=extracted["features"],
        invoice_desc=descs["invoice_desc"],
        mobile_desc=descs["mobile_desc"],
        short_desc=descs["short_desc"],
        long_desc1=descs["long_desc1"],
        retail_desc=descs["retail_desc"],
        confidence_score=score,
        needs_review=needs_review,
        review_reasons=reasons
    )
    
    return record.model_dump()

def enrich_batch(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enriches a batch of raw product records.
    """
    return [enrich_single_item(item) for item in items]

def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches an entire Pandas DataFrame of raw products.
    """
    records = df.to_dict(orient="records")
    enriched_records = enrich_batch(records)
    return pd.DataFrame(enriched_records)
