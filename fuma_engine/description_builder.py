"""
Multi-Channel Description Builder
Owned by Member 2.
Constructs 5 distinct channel-specific descriptions following exact client formulas and character limits:
1. INVOICE_DESC: <= 40 chars, ALL CAPS, highly abbreviated.
2. MOBILE_DESC: Strictly calibrated for 60-80 chars (<= 85 chars max).
3. SHORT_DESC: Standardized Product Title.
4. LONG_DESC1: Comma-delimited technical specs.
5. RETAIL_DESC: Consumer-ready marketing copy with features.
"""

from typing import Dict, List, Any, Optional
from fuma_engine.schema import AttributeItem

ABBREVIATIONS = {
    "DISHWASHER": "DISHWASH",
    "REFRIGERATOR": "FRIDGE",
    "STAINLESS STEEL": "SS",
    "STAINLESS": "SS",
    "BUILT-IN": "BLT-IN",
    "STANDARD": "STD",
    "CLEANBOOST": "CLN-BST",
    "VOLTS": "V",
    "VOLT": "V",
    "AMPERE": "A",
    "AMPS": "A",
    "INCH": "IN",
    "INCHES": "IN",
    "MOUNT": "MNT",
    "CUT-OFF DISC": "CUT-OFF DISC",
    "SANDING DISC": "SAND DISC",
    "GRINDING WHEEL": "GRIND WHL",
    "LIGHT BULB": "LED BULB",
    "CHANDELIER": "CHAND",
    "PENDANT LIGHT": "PENDANT",
    "WALL LIGHT": "WALL LT",
    "DOWNLIGHT": "DOWN LT"
}

def abbreviate_text(text: str) -> str:
    """Replaces words with standard invoice abbreviations."""
    words = text.split()
    abbrev_words = [ABBREVIATIONS.get(w.upper(), w) for w in words]
    return " ".join(abbrev_words)

def build_invoice_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs Invoice Description (<= 40 chars, ALL CAPS).
    Formula: [BRAND/MFG] [PROD_TYPE] [KEY_SPEC] [MPN]
    """
    brand_or_mfg = (brand or mfg or "MRO").replace("®", "").replace("™", "").strip().upper()
    prod_type = abbreviate_text(product_name or "PART").upper()
    mpn_clean = (mpn or "").upper()
    
    # Try with key spec
    key_spec = ""
    if attrs.get("dimensions", {}).get("diameter"):
        key_spec = f"{attrs['dimensions']['diameter']}IN".replace(" ", "")
    elif attrs.get("dimensions", {}).get("thickness"):
        key_spec = f"{attrs['dimensions']['thickness']}IN".replace(" ", "")
    elif attrs.get("voltage"):
        key_spec = f"{attrs['voltage']}V"
    elif attrs.get("material"):
        key_spec = ABBREVIATIONS.get(attrs["material"].upper(), attrs["material"][:2].upper())

    # Candidate 1: BRAND PROD SPEC MPN
    parts = [p for p in [brand_or_mfg, prod_type, key_spec, mpn_clean] if p]
    candidate = " ".join(parts).upper()
    
    if len(candidate) <= 40:
        return candidate
        
    # Candidate 2: Drop key_spec
    parts = [p for p in [brand_or_mfg, prod_type, mpn_clean] if p]
    candidate = " ".join(parts).upper()
    if len(candidate) <= 40:
        return candidate
        
    # Candidate 3: Shorten product type
    parts = [p for p in [brand_or_mfg, mpn_clean] if p]
    candidate = " ".join(parts).upper()
    if len(candidate) <= 40:
        return candidate
        
    # Hard truncate to 40 chars
    return candidate[:40].strip()

def build_mobile_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any], classpath: str = "") -> str:
    """
    Constructs Mobile Description calibrated for the 60-80 character sweet spot (<= 85 chars hard limit).
    Formula: [Manufacturer] [Brand], [Primary Spec] [Product Name], [MPN]
    """
    mfg_clean = (mfg or "").replace(" (4031)", "").replace(" (2435)", "").replace(" (JAMIN)", "").replace(" (MIRUS)", "").replace(" (KICLI)", "").replace(" (5831)", "").replace(" (BOICA)", "").replace(" (APPDE)", "").replace(" (6151)", "").replace(" (2585)", "").replace(" (3073)", "").replace(" (5573)", "").replace(" (5142)", "").replace(" (6603)", "").replace(" (4927)", "").replace(" (FESTO)", "").replace(" (TECGE)", "").replace(" (KRETO)", "").replace(" (6694)", "").replace(" (EDGSA)", "").replace(" (PALDO)", "").replace(" (4381)", "").replace(" (PREME)", "").replace(" (VESTO)", "").replace(" (OLIMA)", "").strip()
    brand_clean = (brand or "").strip()
    if not brand_clean or brand_clean.startswith("--"):
        brand_clean = mfg_clean
        
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    specs = [f"{a.value} {a.uom}".strip() if a.uom else a.value for a in attr_list if a.label not in ('Series', 'Bulb Base / Shape')]
    
    parts = []
    if mfg_clean and brand_clean and mfg_clean != brand_clean:
        parts.append(f"{mfg_clean} {brand_clean}")
    elif brand_clean:
        parts.append(brand_clean)
    elif mfg_clean:
        parts.append(mfg_clean)
        
    prod = product_name or "Hardware Component"
    if prod not in parts:
        parts.append(prod)
        
    series = attrs.get("series")
    if series and series not in parts:
        parts.append(series)
        
    if specs:
        parts.append(specs[0])
        
    if mpn:
        parts.append(mpn)
        
    mobile = ", ".join(parts)
    
    # Adaptive padding if < 60 characters
    if len(mobile) < 60 and len(specs) > 1:
        parts.insert(-1, specs[1])
        mobile = ", ".join(parts)
        
    if len(mobile) < 60 and len(specs) > 2:
        parts.insert(-1, specs[2])
        mobile = ", ".join(parts)
        
    if len(mobile) < 60 and classpath:
        leaf = classpath.split(">")[-1].strip()
        if leaf not in mobile:
            parts.insert(1, leaf)
            mobile = ", ".join(parts)
            
    if len(mobile) < 60:
        parts.append("Heavy Duty")
        mobile = ", ".join(parts)
        
    # Adaptive trimming if > 80 characters
    while len(mobile) > 80 and len(parts) > 3:
        parts.pop(-2)
        mobile = ", ".join(parts)
        
    # Final safety clamp
    if len(mobile) > 80:
        mobile = mobile[:80].rstrip(", ")
        
    return mobile

def build_short_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs Short Description / Product Title.
    Formula: [Brand] [Series] [MPN] [Product Name] [Key Specs]
    """
    brand_clean = (brand or mfg or "").strip()
    series = attrs.get("series", "")
    prod = product_name or "Component"
    
    specs_parts = []
    if attrs.get("dimensions", {}).get("diameter"):
        specs_parts.append(f"{attrs['dimensions']['diameter']} in")
    if attrs.get("finish"):
        specs_parts.append(attrs["finish"])
    if attrs.get("voltage"):
        specs_parts.append(f"{attrs['voltage']}V")
        
    specs_str = " ".join(specs_parts)
    parts = [brand_clean, series, mpn, prod, specs_str]
    return " ".join([p for p in parts if p]).strip()

def build_long_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs Long Description (Specifications String).
    """
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    spec_strings = [f"{a.label}: {a.value} {a.uom}".strip() for a in attr_list]
    
    base_info = f"{brand or mfg} {product_name} (MPN: {mpn})"
    if spec_strings:
        return f"{base_info} - " + ", ".join(spec_strings)
    return base_info

def build_retail_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs Consumer / Retail Marketing Description.
    """
    brand_clean = brand or mfg or "Quality"
    prod = product_name or "Industrial Product"
    
    lead = f"The {brand_clean} {prod} (Model: {mpn}) delivers commercial-grade reliability and high-performance operation."
    features: List[str] = attrs.get("features", [])
    if features:
        feature_text = " Key features include " + ", ".join(features) + "."
        lead += feature_text
    return lead

def generate_all_descriptions(
    mfg: str,
    brand: str,
    mpn: str,
    product_name: str,
    attrs: Dict[str, Any],
    classpath: str = ""
) -> Dict[str, str]:
    """
    Generates all 5 required multichannel product descriptions.
    """
    return {
        "invoice_desc": build_invoice_desc(mfg, brand, mpn, product_name, attrs),
        "mobile_desc": build_mobile_desc(mfg, brand, mpn, product_name, attrs, classpath),
        "short_desc": build_short_desc(mfg, brand, mpn, product_name, attrs),
        "long_desc1": build_long_desc(mfg, brand, mpn, product_name, attrs),
        "retail_desc": build_retail_desc(mfg, brand, mpn, product_name, attrs)
    }

def build_all_descriptions(item_dict: Dict[str, Any], attrs: Dict[str, Any]) -> Dict[str, str]:
    """
    Wrapper taking an item context dictionary.
    """
    mfg = item_dict.get("manufacturer_name", "")
    brand = item_dict.get("brand_name", "")
    mpn = item_dict.get("mfg_part_num", "")
    product_name = item_dict.get("product_name", "")
    classpath = item_dict.get("classpath", "")
    
    return generate_all_descriptions(mfg, brand, mpn, product_name, attrs, classpath)
