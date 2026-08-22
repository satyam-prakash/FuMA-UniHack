"""
FuMA Pipeline Interface
Owned by Member 2.
Provides clean batch and single-item processing functions for Member 3 (API/UI) and Member 1 (Evaluator).

Beyond orchestration this module now computes the two metrics the brief asks for
but which could not previously be produced:

* **LOV compliance** -- share of emitted attribute values found in the approved
  List of Values. Reported as ``None`` when no LOV file is loaded, because
  scoring our own seed vocabulary against itself would be meaningless.
* **Attribute provenance** -- every attribute is tagged ``evidence`` (parsed from
  the supplier's own text) or ``inferred`` (derived from the taxonomy we just
  assigned). "100% attribute coverage" was previously a tautology: the pipeline
  guarantees at least one attribute exists, so coverage could not be anything
  else. Splitting the tiers keeps the headline honest.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from fuma_engine.attribute_extractor import extract_attributes
from fuma_engine.confidence_evaluator import evaluate_record
from fuma_engine.description_builder import build_all_descriptions, synthesize_features
from fuma_engine.schema import ProductRecord
from fuma_engine.sourcing_engine import build_digital_assets, build_provenance_urls
from fuma_engine.taxonomy_classifier import classify_taxonomy

#: Hard cap matching Member 3's ITEM_FEATURES_1..20 delivery slots.
MAX_FEATURES = 20

#: Labels produced by taxonomy inference rather than parsed from supplier text.
#: Kept in the output (they are useful for faceted search) but never counted as
#: evidence-backed extraction.
INFERRED_LABELS = frozenset({"Product Type", "Application"})


def _lov_compliance(attributes: List[Any], classpath: str) -> Optional[float]:
    """Fraction of emitted values present in the approved LOV, or None.

    None means "no LOV file loaded" and is reported as such rather than as 0%,
    so a missing reference file never looks like a quality failure.
    """
    try:
        from fuma_rules.reference_data import is_lov_value, load_reference_bundle

        if not load_reference_bundle().lov_available:
            return None
    except Exception:  # noqa: BLE001 - reference layer must never break enrichment
        return None

    checkable = [a for a in attributes if a.label not in INFERRED_LABELS and a.value]
    if not checkable:
        return None
    hits = sum(1 for a in checkable if is_lov_value(a.value))
    return round(hits / len(checkable), 4)


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
    raw_brand_val = str(raw_dict.get("E1_Brand") or raw_dict.get("raw_brand") or "").strip()

    # Brand resolution. Member 1 sets BRAND_NAME and deliberately leaves it BLANK
    # for distributors/co-ops (a co-op is not a brand). A blank must therefore
    # stay blank -- falling back to the raw supplier field would resurrect the
    # very placeholders the brief says are not data ("-- Unbranded --").
    if "BRAND_NAME" in raw_dict:
        brand = str(raw_dict.get("BRAND_NAME") or "").strip()
    else:
        brand = str(raw_dict.get("brand_name") or raw_brand_val).strip()
    if brand.startswith("--"):  # placeholder, never a real brand
        brand = ""


    # Brand evidence tier from Member 1 (blank when M1 has not run yet).
    brand_tier = str(raw_dict.get("BRAND_MATCH_TIER") or "").strip()

    # 1. Step: Taxonomy Classification
    classpath, unspsc, product_name = classify_taxonomy(raw_desc, mpn, mfg)
    
    # 2. Step: Attribute Extraction
    extracted = extract_attributes(
        raw_desc, mpn, category=product_name, manufacturer_name=mfg, classpath=classpath
    )

    # 2a. Tag provenance so "coverage" can be reported honestly.
    for attr in extracted["attributes"]:
        attr.evidence = "inferred" if attr.label in INFERRED_LABELS else "evidence"

    # 2b. Step: Grounded feature synthesis (fills ITEM_FEATURES_1..5+ when
    # external marketing copy is sparse). Detected features come first,
    # synthesized grounded bullets fill up to the delivery slot cap.
    brand_for_ctx = brand if brand and not brand.startswith("--") else mfg
    synthesized = synthesize_features(
        mfg, brand_for_ctx, mpn, product_name, extracted, classpath
    )
    merged_features: List[str] = list(extracted.get("features") or [])
    for feat in synthesized:
        if len(merged_features) >= MAX_FEATURES:
            break
        if feat not in merged_features:
            merged_features.append(feat)
    extracted["features"] = merged_features
    
    # Clean item dict for descriptions
    item_ctx = {
        "mfg_part_num": mpn,
        "part_desc_raw": raw_desc,
        "manufacturer_name": mfg,
        "brand_name": brand_for_ctx,
        "product_name": product_name,
        "classpath": classpath,
        "unspsc": unspsc
    }
    
    # 3. Step: Multi-Channel Description Generation
    descs = build_all_descriptions(item_ctx, extracted)

    # 4. Step: LOV compliance, then quality & confidence scoring.
    lov = _lov_compliance(extracted["attributes"], classpath)
    score, needs_review, reasons = evaluate_record(
        descs,
        extracted,
        classpath,
        raw_brand=raw_brand_val,
        raw_desc=raw_desc,
        brand_tier=brand_tier,
        brand_name=brand,
        lov_compliance=-1.0 if lov is None else lov,
    )

    # 4b. Duplicate flag from Member 1's de-duplication stage.
    if raw_dict.get("is_duplicate"):
        dup_of = raw_dict.get("duplicate_of")
        reasons.append(
            f"Possible duplicate of row {dup_of} ({raw_dict.get('duplicate_reason', 'match')})"
        )

    # 5. Step: Manufacturer Provenance & Reference URLs (blank when unverified)
    urls = build_provenance_urls(mfg, mpn, brand_name=item_ctx["brand_name"], product_name=product_name)

    # 5b. Digital assets, only where a verified naming convention exists.
    assets = build_digital_assets(item_ctx["brand_name"], mpn)

    # 6. Build Final Standard Record
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
        marketing_description=descs.get("marketing_description", ""),
        mfr_url=str(urls["mfr_url"]),
        ref_urls=[str(u) for u in urls["ref_urls"]],
        product_image=assets.get("product_image", ""),
        confidence_score=score,
        needs_review=needs_review,
        review_reasons=reasons,
        brand_match_tier=brand_tier,
        lov_compliance=lov,
        is_duplicate=bool(raw_dict.get("is_duplicate")),
        duplicate_of=raw_dict.get("duplicate_of"),
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
