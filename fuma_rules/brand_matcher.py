"""
Manufacturer & Canonical Brand Resolution Module with Legal Trademarks (®, ™).
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
Package: fuma_rules
"""

import re
import difflib
from typing import Tuple, Optional, Dict, Any, List
from .sanitizer import clean_supplier_name, clean_placeholder, clean_part_description

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


# Canonical Master Brand & Manufacturer Catalog Database
CANONICAL_BRAND_CATALOG: List[Dict[str, str]] = [
    {
        "MANUFACTURER_NAME": "Rheem Manufacturing",
        "BRAND_NAME": "FRIGIDAIRE®",
        "MANUFACTURER_CODE": "RHEEM",
        "BRAND_CODE": "FRIG",
        "KEYWORDS": ["frigidaire", "pdsh", "ffcd", "fgid"],
    },
    {
        "MANUFACTURER_NAME": "Whirlpool Corporation",
        "BRAND_NAME": "Whirlpool®",
        "MANUFACTURER_CODE": "WHIRL",
        "BRAND_CODE": "WHRL",
        "KEYWORDS": ["whirlpool", "wdts", "wdf", "wdt"],
    },
    {
        "MANUFACTURER_NAME": "Freud America, Inc.",
        "BRAND_NAME": "Diablo®",
        "MANUFACTURER_CODE": "FREUD",
        "BRAND_CODE": "DIAB",
        "KEYWORDS": ["diablo", "freud", "dcb", "dbd", "dbds", "dfb"],
    },
    {
        "MANUFACTURER_NAME": "Milwaukee Electric Tool Corporation",
        "BRAND_NAME": "Milwaukee®",
        "MANUFACTURER_CODE": "MILW",
        "BRAND_CODE": "MLWK",
        "KEYWORDS": ["milwaukee", "milw", "49-94-", "48-22-", "2804-", "2730-"],
    },
    {
        "MANUFACTURER_NAME": "3M",
        "BRAND_NAME": "3M™",
        "MANUFACTURER_CODE": "3M",
        "BRAND_CODE": "3M",
        "KEYWORDS": ["3m", "cubitron", "stikit", "scotch", "3mabr"],
    },
    {
        "MANUFACTURER_NAME": "Mirka Abrasives, Inc.",
        "BRAND_NAME": "Mirka®",
        "MANUFACTURER_CODE": "MIRKA",
        "BRAND_CODE": "MRKA",
        "KEYWORDS": ["mirka", "hiolit", "abranet", "5b-332", "9a-570"],
    },
    {
        "MANUFACTURER_NAME": "Stanley Black & Decker",
        "BRAND_NAME": "DEWALT®",
        "MANUFACTURER_CODE": "DEWALT",
        "BRAND_CODE": "DWLT",
        "KEYWORDS": ["dewalt", "dewlt", "dwa", "dwe", "dcf", "dcd", "black & decker/dewlt"],
    },
    {
        "MANUFACTURER_NAME": "Stanley Black & Decker",
        "BRAND_NAME": "STANLEY®",
        "MANUFACTURER_CODE": "STANLEY",
        "BRAND_CODE": "STNL",
        "KEYWORDS": ["stanley", "fatmax"],
    },
    {
        "MANUFACTURER_NAME": "Stanley Black & Decker",
        "BRAND_NAME": "IRWIN®",
        "MANUFACTURER_CODE": "IRWIN",
        "BRAND_CODE": "IRWN",
        "KEYWORDS": ["irwin"],
    },
    {
        "MANUFACTURER_NAME": "Philips Lighting Holding B.V.",
        "BRAND_NAME": "Philips®",
        "MANUFACTURER_CODE": "PHILIPS",
        "BRAND_CODE": "PHLP",
        "KEYWORDS": ["phillips", "philips"],
    },
    {
        "MANUFACTURER_NAME": "Kichler Lighting LLC",
        "BRAND_NAME": "Kichler®",
        "MANUFACTURER_CODE": "KICHLER",
        "BRAND_CODE": "KCHL",
        "KEYWORDS": ["kichler"],
    },
    {
        "MANUFACTURER_NAME": "Satco Products, Inc.",
        "BRAND_NAME": "Satco®",
        "MANUFACTURER_CODE": "SATCO",
        "BRAND_CODE": "STCO",
        "KEYWORDS": ["satco"],
    },
    {
        "MANUFACTURER_NAME": "Makita U.S.A., Inc.",
        "BRAND_NAME": "Makita®",
        "MANUFACTURER_CODE": "MAKITA",
        "BRAND_CODE": "MAKT",
        "KEYWORDS": ["makita"],
    },
    {
        "MANUFACTURER_NAME": "Southwire Company, LLC",
        "BRAND_NAME": "Southwire®",
        "MANUFACTURER_CODE": "SOUTHWIRE",
        "BRAND_CODE": "STHW",
        "KEYWORDS": ["southwire", "g turner"],
    },
    {
        "MANUFACTURER_NAME": "Leviton Manufacturing Co., Inc.",
        "BRAND_NAME": "Leviton®",
        "MANUFACTURER_CODE": "LEVITON",
        "BRAND_CODE": "LVTN",
        "KEYWORDS": ["leviton"],
    },
    {
        "MANUFACTURER_NAME": "Festool USA",
        "BRAND_NAME": "Festool®",
        "MANUFACTURER_CODE": "FESTOOL",
        "BRAND_CODE": "FSTL",
        "KEYWORDS": ["festool"],
    },
    {
        "MANUFACTURER_NAME": "Kreg Tool Company",
        "BRAND_NAME": "Kreg®",
        "MANUFACTURER_CODE": "KREG",
        "BRAND_CODE": "KREG",
        "KEYWORDS": ["kreg"],
    },
    {
        "MANUFACTURER_NAME": "Hunter Fan Company",
        "BRAND_NAME": "Hunter®",
        "MANUFACTURER_CODE": "HUNTER",
        "BRAND_CODE": "HNTR",
        "KEYWORDS": ["hunter"],
    },
    {
        "MANUFACTURER_NAME": "Robert Bosch Tool Corporation",
        "BRAND_NAME": "Bosch®",
        "MANUFACTURER_CODE": "BOSCH",
        "BRAND_CODE": "BSCH",
        "KEYWORDS": ["bosch", "11255", "gdr", "gsr", "robt bosch"],
    },
    {
        "MANUFACTURER_NAME": "Schneider Electric",
        "BRAND_NAME": "Square D®",
        "MANUFACTURER_CODE": "SCHNEIDER",
        "BRAND_CODE": "SQD",
        "KEYWORDS": ["square d"],
    },
    {
        "MANUFACTURER_NAME": "Cooper Lighting Solutions",
        "BRAND_NAME": "Cooper Lighting®",
        "MANUFACTURER_CODE": "COOPER",
        "BRAND_CODE": "COOP",
        "KEYWORDS": ["cooper lighting"],
    },
    {
        "MANUFACTURER_NAME": "Feit Electric Company",
        "BRAND_NAME": "Feit Electric®",
        "MANUFACTURER_CODE": "FEIT",
        "BRAND_CODE": "FEIT",
        "KEYWORDS": ["feit electric"],
    },
    {
        "MANUFACTURER_NAME": "KYOCERA SENCO Industrial Tools, Inc.",
        "BRAND_NAME": "SENCO®",
        "MANUFACTURER_CODE": "SENCO",
        "BRAND_CODE": "SNCO",
        "KEYWORDS": ["senco"],
    },
    {
        "MANUFACTURER_NAME": "First Alert",
        "BRAND_NAME": "First Alert®",
        "MANUFACTURER_CODE": "FIRSTALERT",
        "BRAND_CODE": "FALT",
        "KEYWORDS": ["first alert", "b r k"],
    },
    {
        "MANUFACTURER_NAME": "Acuity Brands Lighting, Inc.",
        "BRAND_NAME": "Lithonia Lighting®",
        "MANUFACTURER_CODE": "ACUITY",
        "BRAND_CODE": "LITH",
        "KEYWORDS": ["lithonia"],
    },
    {
        "MANUFACTURER_NAME": "Streamlight, Inc.",
        "BRAND_NAME": "Streamlight®",
        "MANUFACTURER_CODE": "STREAMLIGHT",
        "BRAND_CODE": "STRM",
        "KEYWORDS": ["streamlight"],
    },
    {
        "MANUFACTURER_NAME": "Wera Tools Inc.",
        "BRAND_NAME": "Wera®",
        "MANUFACTURER_CODE": "WERA",
        "BRAND_CODE": "WERA",
        "KEYWORDS": ["wera"],
    },
    {
        "MANUFACTURER_NAME": "SawStop, LLC",
        "BRAND_NAME": "SawStop®",
        "MANUFACTURER_CODE": "SAWSTOP",
        "BRAND_CODE": "SWST",
        "KEYWORDS": ["sawstop", "saw stop"],
    },
    {
        "MANUFACTURER_NAME": "Klein Tools, Inc.",
        "BRAND_NAME": "Klein Tools®",
        "MANUFACTURER_CODE": "KLEIN",
        "BRAND_CODE": "KLN",
        "KEYWORDS": ["klein", "klein tools", "d213", "11055"],
    },
]

# Brand alias mapping to canonical trademarked names
BRAND_ALIAS_MAP: Dict[str, str] = {
    "frigidaire": "FRIGIDAIRE®",
    "whirlpool": "Whirlpool®",
    "diablo": "Diablo®",
    "freud": "Diablo®",
    "milwaukee": "Milwaukee®",
    "milw": "Milwaukee®",
    "3m": "3M™",
    "3 m": "3M™",
    "mirka": "Mirka®",
    "dewalt": "DEWALT®",
    "dewlt": "DEWALT®",
    "stanley": "STANLEY®",
    "irwin": "IRWIN®",
    "bosch": "Bosch®",
    "makita": "Makita®",
    "philips": "Philips®",
    "phillips": "Philips®",
    "kichler": "Kichler®",
    "satco": "Satco®",
    "southwire": "Southwire®",
    "leviton": "Leviton®",
    "festool": "Festool®",
    "kreg": "Kreg®",
    "hunter": "Hunter®",
    "square d": "Square D®",
    "senco": "SENCO®",
    "first alert": "First Alert®",
    "lithonia": "Lithonia Lighting®",
    "streamlight": "Streamlight®",
    "wera": "Wera®",
    "sawstop": "SawStop®",
    "saw stop": "SawStop®",
    "klein": "Klein Tools®",
    "klein tools": "Klein Tools®",
}

# Known co-op / distributor to true manufacturer mappings
DISTRIBUTOR_OVERRIDE_MAP: Dict[str, Dict[str, str]] = {
    "appliance dealers cooperative": {
        "PDSH": "Rheem Manufacturing",
        "WDTS": "Whirlpool Corporation",
        "FFCD": "Rheem Manufacturing",
        "WDF": "Whirlpool Corporation",
    },
    "jam industrial supply llc": {
        "3M": "3M",
        "CUBITRON": "3M",
    }
}


class BrandManufacturerResolver:
    """
    Resolves messy supplier strings to canonical MANUFACTURER_NAME and BRAND_NAME with legal trademarks (®, ™).
    """

    def __init__(self, custom_catalog: Optional[List[Dict[str, str]]] = None):
        self.catalog = custom_catalog or CANONICAL_BRAND_CATALOG
        self.mfg_list = list({item["MANUFACTURER_NAME"] for item in self.catalog})
        self.brand_list = list({item["BRAND_NAME"] for item in self.catalog})

    def _token_similarity(self, s1: str, s2: str) -> float:
        """Calculates string similarity using rapidfuzz or difflib fallback (0.0 to 1.0)."""
        if HAS_RAPIDFUZZ:
            return fuzz.token_sort_ratio(s1, s2) / 100.0
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def resolve(
        self,
        raw_mfg: Optional[str] = None,
        raw_desc: Optional[str] = None,
        mfg_part_num: Optional[str] = None,
        raw_brand: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Resolves (MANUFACTURER_NAME, BRAND_NAME) for a given catalog item.
        
        Returns:
            Tuple[str, str]: (Canonical MANUFACTURER_NAME, Canonical BRAND_NAME with ®/™)
        """
        cleaned_mfg = clean_supplier_name(raw_mfg)
        cleaned_brand = clean_placeholder(raw_brand)
        cleaned_desc = clean_part_description(raw_desc)
        mpn = str(mfg_part_num or "").strip().upper()
        desc_lower = cleaned_desc.lower()

        # Step 1: Check if input has explicit brand that matches known aliases
        if cleaned_brand:
            brand_key = cleaned_brand.lower().replace("®", "").replace("™", "").strip()
            if brand_key in BRAND_ALIAS_MAP:
                canonical_brand = BRAND_ALIAS_MAP[brand_key]
                for item in self.catalog:
                    if item["BRAND_NAME"] == canonical_brand:
                        return item["MANUFACTURER_NAME"], canonical_brand

        # Step 2: Check for distributor / co-op overrides (e.g. Appliance Dealers Cooperative)
        if cleaned_mfg:
            mfg_clean_lower = cleaned_mfg.lower()
            for dist_name, prefix_map in DISTRIBUTOR_OVERRIDE_MAP.items():
                if dist_name in mfg_clean_lower:
                    for prefix, target_mfg in prefix_map.items():
                        if mpn.startswith(prefix) or prefix.lower() in desc_lower:
                            for item in self.catalog:
                                if item["MANUFACTURER_NAME"] == target_mfg:
                                    return item["MANUFACTURER_NAME"], item["BRAND_NAME"]

        # Step 3: Match against catalog keywords in MPN or Description
        for item in self.catalog:
            for kw in item.get("KEYWORDS", []):
                if kw in desc_lower or kw.upper() in mpn:
                    return item["MANUFACTURER_NAME"], item["BRAND_NAME"]

        # Step 4: Direct exact or fuzzy match on cleaned_mfg
        if cleaned_mfg:
            # Check exact match in catalog
            for item in self.catalog:
                if item["MANUFACTURER_NAME"].lower() == cleaned_mfg.lower():
                    return item["MANUFACTURER_NAME"], item["BRAND_NAME"]

            # Fuzzy match across catalog manufacturers
            best_score = 0.0
            best_match = None
            for item in self.catalog:
                sim = self._token_similarity(cleaned_mfg, item["MANUFACTURER_NAME"])
                if sim > best_score:
                    best_score = sim
                    best_match = item
            
            if best_score >= 0.70 and best_match:
                return best_match["MANUFACTURER_NAME"], best_match["BRAND_NAME"]

            # If no good catalog match, return cleaned manufacturer and fallback brand
            return cleaned_mfg, cleaned_mfg

        return "Unknown Manufacturer", "Unknown Brand"


# Global instance and helper function for QA plan compatibility
_default_resolver = BrandManufacturerResolver()

def resolve_brand_and_manufacturer(supplier_name: Optional[str] = None, desc_or_brand: Optional[str] = None) -> Dict[str, str]:
    """
    Helper function matching FuMA QA plan signature.
    Returns: {"manufacturer_name": ..., "brand_name": ...}
    """
    mfg, brand = _default_resolver.resolve(
        raw_mfg=supplier_name,
        raw_desc=desc_or_brand,
        raw_brand=desc_or_brand,
    )
    return {
        "manufacturer_name": mfg,
        "brand_name": brand,
    }
