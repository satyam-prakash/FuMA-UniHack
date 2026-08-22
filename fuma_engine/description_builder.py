"""
Multi-Channel Description Builder
Owned by Member 2.
Constructs 6 distinct channel-specific descriptions following exact client formulas and character limits:
1. INVOICE_DESC: <= 40 chars, ALL CAPS, highly abbreviated.
2. MOBILE_DESC: Strictly calibrated for 60-80 chars (<= 85 chars max).
3. SHORT_DESC: Standardized Product Title.
4. LONG_DESC1: Comma-delimited technical specs.
5. RETAIL_DESC: Consumer-ready marketing copy with features.
6. MARKETING_DESCRIPTION: Grounded 2-sentence B2B professional summary.

Also synthesizes structured ITEM_FEATURES bullets (3-6 per row) grounded strictly
in brand, MPN, classpath taxonomy and extracted attributes when external marketing
copy is sparse.
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
    
    # Adaptive padding using only verified specs / taxonomy leaf if < 60 characters
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
    Constructs Consumer / Retail Marketing Description grounded in verified attributes.
    """
    brand_clean = (brand or mfg or "").replace("®", "").replace("™", "").strip()
    prod = product_name or "Industrial Product"
    series = attrs.get("series", "")
    
    parts = [brand_clean]
    if series:
        parts.append(series)
    parts.append(prod)
    if mpn:
        parts.append(f"(MPN: {mpn})")
        
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    specs = [f"{a.label}: {a.value} {a.uom}".strip() if a.uom else f"{a.label}: {a.value}".strip() for a in attr_list if a.label not in ('Product Type', 'Application', 'Series')]
    
    desc = " ".join(parts)
    if specs:
        desc += " featuring " + ", ".join(specs[:4]) + "."
    else:
        desc += "."
    return desc

def _spec_phrase(attrs: Dict[str, Any], skip_labels: tuple = ()) -> str:
    """Returns a compact 'Label: Value uom' phrase from the first usable attribute."""
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    for a in attr_list:
        if a.label in skip_labels or not a.value:
            continue
        return f"{a.value} {a.uom}".strip() if a.uom else a.value
    return ""


def build_marketing_description(
    mfg: str,
    brand: str,
    mpn: str,
    product_name: str,
    attrs: Dict[str, Any],
    classpath: str = "",
) -> str:
    """
    Constructs MARKETING_DESCRIPTION: a grounded professional B2B summary
    built strictly from verified facts ([BRAND_NAME], [MANUFACTURER_PART_NUMBER],
    [Classpath] leaf category, and extracted specifications).
    No invented claims, filler or subjective superlatives.
    """
    brand_clean = (brand or mfg or "").replace("®", "").replace("™", "").strip()
    prod = (product_name or "component").strip()
    leaf = classpath.split(">")[-1].strip() if classpath else prod
    series = attrs.get("series", "")

    # Sentence 1: identity + series + application context
    if series:
        s1 = f"{brand_clean} {mpn} {prod.lower()} from the {series} series for {leaf.lower()} applications."
    else:
        s1 = f"{brand_clean} {mpn} {prod.lower()} designed for {leaf.lower()} applications."

    # Sentence 2: verified specification highlights
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    spec_bullets = []
    for a in attr_list:
        if a.label in ("Product Type", "Application", "Series"):
            continue
        if a.uom:
            spec_bullets.append(f"{a.value} {a.uom} {a.label.lower()}")
        else:
            spec_bullets.append(f"{a.value} {a.label.lower()}")

    if spec_bullets:
        s2 = f"Features {' and '.join(spec_bullets[:3])}."
        marketing = f"{s1} {s2}"
    else:
        marketing = s1

    return " ".join(marketing.split())


def synthesize_features(
    mfg: str,
    brand: str,
    mpn: str,
    product_name: str,
    attrs: Dict[str, Any],
    classpath: str = "",
) -> List[str]:
    """
    Constructs structured ITEM_FEATURES bullet points grounded strictly in the
    extracted attribute set and verified product specifications:
      - Material / construction
      - Dimensions / sizing
      - Electrical / mechanical ratings
      - Finish / coating
      - Series & specific detected features
    Emits ONLY verified facts. If there are 3 verified features, emits 3 and leaves
    the remaining slots empty rather than inventing filler.
    """
    features: List[str] = []
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    by_label = {a.label.lower(): a for a in attr_list}

    # 1. Material / construction
    material = attrs.get("material") or (by_label.get("material").value if by_label.get("material") else "")
    if material:
        features.append(f"{material} construction")

    # 2. Dimensions & sizing
    dims = attrs.get("dimensions", {})
    if dims.get("diameter"):
        features.append(f"{dims['diameter']} in diameter")
    elif dims.get("width") and dims.get("length"):
        features.append(f"{dims['width']} x {dims['length']} in size")
    elif dims.get("thickness"):
        features.append(f"{dims['thickness']} in thickness")

    # 3. Electrical & mechanical ratings
    volt = by_label.get("voltage rating")
    if volt:
        features.append(f"{volt.value} V electrical rating")
    amp = by_label.get("amperage rating")
    if amp:
        features.append(f"{amp.value} A amperage rating")
    cap = by_label.get("battery capacity")
    if cap:
        features.append(f"{cap.value} Ah battery capacity")
    bgrp = by_label.get("battery group size")
    if bgrp:
        features.append(f"Group {bgrp.value} battery size")
    fuel = by_label.get("fuel type")
    if fuel:
        features.append(f"{fuel.value} fuel source")
    pwr = by_label.get("power source")
    if pwr:
        features.append(f"{pwr.value} powered operation")
    cct = by_label.get("color temperature")
    if cct:
        features.append(f"{cct.value} color temperature")
    cycles = by_label.get("number of wash cycles")
    if cycles:
        features.append(f"{cycles.value} wash cycles")
    press = by_label.get("pressure class")
    if press:
        features.append(f"{press.value} pressure rating")
    grit = by_label.get("grit grade")
    if grit:
        features.append(f"{grit.value} abrasive grit")
    conn = by_label.get("connection type 1") or by_label.get("connection type")
    if conn:
        features.append(f"{conn.value} connection")
    thread = by_label.get("thread size")
    if thread:
        features.append(f"{thread.value} thread size")
    hp = by_label.get("horsepower rating")
    if hp:
        features.append(f"{hp.value} HP motor rating")
    mot = by_label.get("motor type")
    if mot:
        features.append(f"{mot.value} motor")
    drv = by_label.get("drive / chuck size")
    if drv:
        features.append(f"{drv.value} in drive size")
    anv = by_label.get("anvil / retainer type")
    if anv:
        features.append(f"{anv.value} anvil")
    cfg = by_label.get("tool configuration")
    if cfg:
        features.append(f"{cfg.value}")
    lbeam = by_label.get("laser beam color")
    if lbeam:
        features.append(f"{lbeam.value} laser beam")
    bcfg = by_label.get("beam configuration")
    if bcfg:
        features.append(f"{bcfg.value} beam configuration")
    pkg = by_label.get("package quantity")
    if pkg:
        features.append(f"Pack of {pkg.value}")

    # 4. Finish / Mounting
    finish = attrs.get("finish") or (by_label.get("color / finish").value if by_label.get("color / finish") else "")
    if finish:
        features.append(f"{finish} finish")
    mount = attrs.get("mount_type") or (by_label.get("mounting type").value if by_label.get("mounting type") else "")
    if mount:
        features.append(f"{mount} mounting")

    # 5. Series
    series = attrs.get("series")
    if series:
        features.append(f"{series} Series")

    # 6. Category Application context
    app = by_label.get("application")
    if app:
        features.append(f"Engineered for {app.value} applications")

    # De-duplicate while preserving order; cap at available verified features
    deduped: List[str] = []
    for f in features:
        if f not in deduped:
            deduped.append(f)
    return deduped


def generate_all_descriptions(
    mfg: str,
    brand: str,
    mpn: str,
    product_name: str,
    attrs: Dict[str, Any],
    classpath: str = ""
) -> Dict[str, str]:
    """
    Generates all 6 required multichannel product descriptions.
    """
    return {
        "invoice_desc": build_invoice_desc(mfg, brand, mpn, product_name, attrs),
        "mobile_desc": build_mobile_desc(mfg, brand, mpn, product_name, attrs, classpath),
        "short_desc": build_short_desc(mfg, brand, mpn, product_name, attrs),
        "long_desc1": build_long_desc(mfg, brand, mpn, product_name, attrs),
        "retail_desc": build_retail_desc(mfg, brand, mpn, product_name, attrs),
        "marketing_description": build_marketing_description(
            mfg, brand, mpn, product_name, attrs, classpath
        ),
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
