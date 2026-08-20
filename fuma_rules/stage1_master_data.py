"""
Master Data & Normalization Pipeline Stage (Stage 1).
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
Package: fuma_rules
"""

from typing import Dict, Any, List, Optional
from .sanitizer import (
    clean_placeholder,
    clean_supplier_name,
    clean_part_description,
)
from .brand_matcher import BrandManufacturerResolver
from .uom_standardizer import (
    decimal_to_trade_fraction,
    standardize_uom,
    format_measurement,
    standardize_dimension_string,
)


class MasterDataPipelineStage:
    """
    Stage 1 Pipeline: Ingests raw supplier records and executes:
    - Data sanitization and placeholder stripping
    - Manufacturer and Brand canonical entity resolution with legal trademarks (®, ™)
    - UOM and decimal-to-fraction standardization
    """

    def __init__(self, brand_resolver: Optional[BrandManufacturerResolver] = None):
        self.brand_resolver = brand_resolver or BrandManufacturerResolver()

    def process_item(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single raw item dictionary.
        
        Expected raw_item keys:
            - Mfg_Part_Num
            - Part_Desc
            - Part_Manuf
            - E1_Brand / Unilog_Brand / DIB_Brand (optional)
        """
        mpn = str(raw_item.get("Mfg_Part_Num") or raw_item.get("MANUFACTURER_PART_NUMBER") or "").strip()
        raw_desc = raw_item.get("Part_Desc")
        raw_mfg = raw_item.get("Part_Manuf")
        raw_brand = raw_item.get("Unilog_Brand") or raw_item.get("E1_Brand") or raw_item.get("DIB_Brand")

        # 1. Clean and sanitize input
        clean_desc = clean_part_description(raw_desc)
        cleaned_mfg = clean_supplier_name(raw_mfg)
        cleaned_brand = clean_placeholder(raw_brand)

        # 2. Resolve canonical Manufacturer & Brand with trademarks
        canonical_mfg, canonical_brand = self.brand_resolver.resolve(
            raw_mfg=cleaned_mfg,
            raw_desc=clean_desc,
            mfg_part_num=mpn,
            raw_brand=cleaned_brand,
        )

        # 3. Extract and standardize dimensions if present in description
        std_dimension = standardize_dimension_string(clean_desc)

        # 4. Construct normalized record structure
        enriched_record = dict(raw_item)
        enriched_record.update({
            "CLEAN_DESC": clean_desc,
            "MANUFACTURER_NAME": canonical_mfg,
            "BRAND_NAME": canonical_brand,
            "MANUFACTURER_PART_NUMBER": mpn,
            "STANDARDIZED_DIMENSIONS": std_dimension,
            "STAGE1_STATUS": "NORMALIZED",
        })

        return enriched_record

    def process_batch(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes a list of raw item records in batch.
        """
        return [self.process_item(item) for item in raw_items]
