"""
Local test runner for Member 2 (FuMA Engine)
Tests taxonomy classification, attribute extraction, 5 description formulas, and scoring against Ground Truth.
"""

import sys
# Set UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fuma_engine.taxonomy_classifier import classify_taxonomy
from fuma_engine.attribute_extractor import extract_attributes
from fuma_engine.description_builder import build_all_descriptions
from fuma_engine.confidence_evaluator import evaluate_record
from fuma_engine.schema import ProductRecord

def test_ground_truth_row_1():
    print("=" * 70)
    print("TESTING GROUND TRUTH ROW 1: FRIGIDAIRE DISHWASHER")
    print("=" * 70)
    
    # Input data (as provided by Raw CSV & Member 1 brand resolution)
    raw_item = {
        "mfg_part_num": "PDSH4816AF",
        "part_desc_raw": "PDSH4816AF Dishwasher SS - Display Only 120V 15A 50-1/4IN Leg Mounting With CleanBoost 5-Wash Cycle 47 dBA",
        "manufacturer_name": "Rheem Manufacturing",
        "brand_name": "FRIGIDAIRE®"
    }
    
    # Step 1: Classify Taxonomy
    classpath, unspsc, product_name = classify_taxonomy(raw_item["part_desc_raw"], raw_item["mfg_part_num"])
    raw_item["classpath"] = classpath
    raw_item["unspsc"] = unspsc
    raw_item["product_name"] = product_name
    
    print(f"Classpath:    {classpath}")
    print(f"Product Name: {product_name}")
    
    # Step 2: Extract Attributes & Features
    extracted = extract_attributes(raw_item["part_desc_raw"], raw_item["mfg_part_num"])
    print(f"Extracted Attributes ({len(extracted['attributes'])} found):")
    for attr in extracted["attributes"]:
        print(f"   * {attr.label}: {attr.value} {attr.uom}".rstrip())
        
    # Step 3: Build 5 Multichannel Descriptions
    descs = build_all_descriptions(raw_item, extracted)
    
    print("\nGenerated Descriptions:")
    print(f"   [INVOICE_DESC] ({len(descs['invoice_desc'])} chars, limit <=40): {descs['invoice_desc']}")
    print(f"   [MOBILE_DESC]  ({len(descs['mobile_desc'])} chars, target 60-80): {descs['mobile_desc']}")
    print(f"   [SHORT_DESC]   : {descs['short_desc']}")
    print(f"   [LONG_DESC1]   : {descs['long_desc1']}")
    print(f"   [RETAIL_DESC]  : {descs['retail_desc']}")
    
    # Step 4: Quality & Confidence Evaluation
    score, needs_review, reasons = evaluate_record(descs, extracted, classpath)
    print(f"\nQuality Score: {score}/100.0 (Needs Human Review: {needs_review})")
    
    # Step 5: Validate with Pydantic Schema
    record = ProductRecord(
        mfg_part_num=raw_item["mfg_part_num"],
        part_desc_raw=raw_item["part_desc_raw"],
        manufacturer_name=raw_item["manufacturer_name"],
        brand_name=raw_item["brand_name"],
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
    
    # Assertions for Member 2 Pass Criteria
    assert len(record.invoice_desc) <= 40, "Invoice description exceeded 40 chars!"
    assert record.invoice_desc.isupper(), "Invoice description must be ALL CAPS!"
    assert "FRIGIDAIRE®" in record.short_desc, "Short description missing Brand®!"
    print("\n>>> ALL MEMBER 2 ASSERTIONS PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_ground_truth_row_1()
