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

# ---------------------------------------------------------------------------
# Anti-fabrication safety net.  These superlatives / filler phrases must NEVER
# be injected by any description builder function unless the source data
# actually contains the claim.  The guard is applied as a final pass on
# every generated text field.
# ---------------------------------------------------------------------------
BANNED_FILLERS = {
    "Heavy Duty",
    "Premium",
    "High Performance",
    "Superior",
    "Universal",
    "Durable",
    "Professional Grade",
    "Industrial Strength",
    "Top Quality",
    "Best In Class",
}


def _strip_fillers(text: str) -> str:
    """Removes banned filler phrases from generated text.

    Case-insensitive removal so that 'heavy duty', 'HEAVY DUTY' and
    'Heavy Duty' are all caught.  Collapses resulting double-spaces.
    """
    import re
    result = text
    for filler in BANNED_FILLERS:
        result = re.sub(
            r",?\s*" + re.escape(filler) + r"\s*,?",
            " ",
            result,
            flags=re.IGNORECASE,
        )
    # Collapse whitespace artifacts left by removal.
    result = re.sub(r"\s{2,}", " ", result).strip()
    result = re.sub(r"\s+([,.])", r"\1", result)  # fix orphaned punctuation
    return result


def abbreviate_text(text: str) -> str:
    """Replaces words with standard invoice abbreviations."""
    words = text.split()
    abbrev_words = [ABBREVIATIONS.get(w.upper(), w) for w in words]
    return " ".join(abbrev_words)

#: Invoice spec order, derived from the ground-truth row
#: "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN":
#:   item type -> mounting -> cycles -> material -> volts -> amps -> dimension.
#: The till receipt needs identifying specs, not the brand, so specs outrank
#: brand once the 40-character budget runs out.
_INVOICE_SPEC_ORDER = (
    "Mounting Type",
    "Number of Wash Cycles",
    "Grit Grade",
    "Material",
    "Body Material",
    "Color / Finish",
    "Voltage Rating",
    "Amperage Rating",
    "Wattage Rating",
    "Diameter",
    "Diameter / Size",
    "Diameter / Length",
    "Thickness",
    "Width",
    "Length",
    "Depth With Door Open",
    "Sound Level",
)

#: Compact invoice forms. Materials collapse to trade shorthand ("SST" not
#: "STAINLESS STEEL") to buy characters inside the 40-char limit.
_INVOICE_VALUE_ABBREV = {
    "STAINLESS STEEL": "SST",
    "BRUSHED NICKEL": "BN",
    "OIL RUBBED BRONZE": "ORB",
    "CHAMPAGNE BRONZE": "CPZ",
    "GALVANIZED STEEL": "GALV",
    "CARBON STEEL": "CS",
    "ALUMINUM": "ALUM",
    "COMPOSITE": "COMP",
    "BUILT-IN": "BLTIN",
}


def _invoice_token(label: str, value: str, uom: str) -> str:
    """Renders one attribute as a compact ALL-CAPS invoice token.

    Invoice style closes the space between number and unit ("120V", "50-1/4IN")
    -- this is the one field where the "always space" rule does not apply,
    matching the ground-truth string.
    """
    value = (value or "").strip()
    if not value:
        return ""
    upper = value.upper()
    upper = _INVOICE_VALUE_ABBREV.get(upper, upper)
    if uom:
        return f"{upper}{uom.upper()}"
    return upper


def build_invoice_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs Invoice Description (<= 40 chars, ALL CAPS, no ®/™).

    Formula (per content guidelines / ground truth):
        [ITEM TYPE] [KEY SPECS in fixed order]
    e.g. ``DISHWASHER LEG 5 SST 120V 15A 50-1/4IN``

    Specs are appended in priority order while they fit. Brand and MPN are only
    included when spare budget remains, because a 40-character receipt line is
    worth more as identifying specs than as a brand name.
    """
    prod_type = abbreviate_text(product_name or "PART").upper()
    attr_list: List[AttributeItem] = attrs.get("attributes", [])
    by_label = {a.label: a for a in attr_list}

    tokens: List[str] = []
    for label in _INVOICE_SPEC_ORDER:
        a = by_label.get(label)
        if not a:
            continue
        token = _invoice_token(a.label, a.value, a.uom)
        if token and token not in tokens:
            tokens.append(token)

    # Grow the line spec-by-spec, stopping before the 40-char limit.
    candidate = prod_type
    for token in tokens:
        trial = f"{candidate} {token}".strip()
        if len(trial) > 40:
            break
        candidate = trial

    # Spare budget: add the brand, then the MPN, only if they genuinely fit.
    brand_or_mfg = (brand or mfg or "").replace("®", "").replace("™", "").strip().upper()
    if brand_or_mfg and len(f"{brand_or_mfg} {candidate}") <= 40:
        candidate = f"{brand_or_mfg} {candidate}"

    mpn_clean = (mpn or "").upper()
    if mpn_clean and len(f"{candidate} {mpn_clean}") <= 40:
        candidate = f"{candidate} {mpn_clean}"

    # Never emit an empty invoice line: fall back to identity fields.
    if not candidate.strip():
        candidate = (f"{brand_or_mfg} {mpn_clean}".strip() or "PART")[:40]

    return candidate.strip()[:40].strip()


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

    # Anti-fabrication: strip any banned filler that may have leaked in
    mobile = _strip_fillers(mobile)

    return mobile

#: Labels that are taxonomy restatements, not product specs. Excluded from
#: descriptive copy: "Application: Built-In Dishwashers" adds nothing a shopper
#: cannot already see from the breadcrumb.
_TAXONOMY_LABELS = ("Product Type", "Application")

#: Labels rendered as a bare value in descriptive copy ("Stainless Steel", not
#: "Material: Stainless Steel"), matching the ground-truth phrasing.
_BARE_VALUE_LABELS = frozenset(
    {
        "Material",
        "Body Material",
        "Color / Finish",
        "Series",
        "Edge Profile",
        "Board Type",
        "Glass Type",
        "Installation Type",
        "Tool Configuration",
        "Motor Type",
    }
)

#: Labels rendered "<value> <uom> <label>" ("47 dBA Sound Level"), which is how
#: the ground-truth long description reads.
_VALUE_THEN_LABEL = frozenset(
    {
        "Sound Level",
        "Depth With Door Open",
        "Number of Wash Cycles",
        "Max RPM",
        "Grit Grade",
        "Pressure Class",
        "Flow Rate",
        "Battery Capacity",
        "Horsepower Rating",
    }
)


def _spec_clause(a: AttributeItem) -> str:
    """Renders one attribute as a ground-truth-style clause.

    Three shapes, matching the delivery file:
      * bare value        -> "Stainless Steel"
      * value + uom       -> "120 V"
      * value + uom + lbl -> "47 dBA Sound Level"
    The space between number and unit is always preserved (Unilog UOM rule).
    """
    value = (a.value or "").strip()
    if not value:
        return ""
    uom = (a.uom or "").strip()
    measure = f"{value} {uom}".strip() if uom else value

    if a.label in _BARE_VALUE_LABELS:
        return measure
    if a.label in _VALUE_THEN_LABEL:
        return f"{measure} {a.label}"
    if a.label == "Mounting Type":
        return f"{value} Mounting"
    if uom:
        return measure
    return f"{measure} {a.label}"


def _descriptive_attrs(attrs: Dict[str, Any]) -> List[AttributeItem]:
    """Attributes worth putting in copy: real specs, taxonomy filler removed."""
    return [
        a
        for a in attrs.get("attributes", [])
        if a.label not in _TAXONOMY_LABELS and (a.value or "").strip()
    ]


def build_short_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs SHORT_DESC / Product Title.

    Formula from the content guidelines:
        [Brand®] [Series] [MPN] [Item Type] [Key Attributes]
    Ground truth:
        FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™,
        Leg Mounting, 5-Wash Cycle, Stainless Steel

    Brand keeps its ®/™ (this is a web-facing title). Detected feature phrases
    ("With CleanBoost™") follow the item type, then comma-delimited key specs.
    """
    brand_clean = (brand or mfg or "").strip()
    series = attrs.get("series", "")
    prod = product_name or "Component"

    head_parts = [p for p in (brand_clean, series, mpn, prod) if p]
    head = " ".join(head_parts)

    # Verified feature phrases sit directly after the item type.
    feature_phrases = [f for f in (attrs.get("features") or []) if f.startswith("With ")]
    if feature_phrases:
        head = f"{head} {feature_phrases[0]}"

    # Key specs, capped so the title stays scannable in a results list.
    clauses: List[str] = []
    for a in _descriptive_attrs(attrs):
        if a.label == "Series":
            continue  # already in the head
        clause = _spec_clause(a)
        if clause and clause not in clauses:
            clauses.append(clause)

    title = f"{head}, " + ", ".join(clauses[:5]) if clauses else head
    return _strip_fillers(title.strip())


def build_long_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs LONG_DESC1: the full comma-delimited specification chain.

    Ground truth:
        FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, 5 Wash Cycles,
        120 V, 15 A, Leg Mounting, 24 in W x 24-1/4 in D, 50-1/4 in Depth With Door
        Open, 47 dBA Sound Level, Stainless Steel

    Formula: [Brand®] [Item Type] [Features], [Series], [every verified spec].
    Replaces the previous "Label: Value" debug-style dump, which scored 0%
    against the delivery file.
    """
    brand_clean = (brand or mfg or "").strip()
    prod = product_name or "Component"

    head = f"{brand_clean} {prod}".strip()
    feature_phrases = [f for f in (attrs.get("features") or []) if f.startswith("With ")]
    if feature_phrases:
        head = f"{head} {feature_phrases[0]}"

    clauses: List[str] = []
    series = attrs.get("series", "")
    if series:
        clauses.append(series)
    for a in _descriptive_attrs(attrs):
        if a.label == "Series":
            continue
        clause = _spec_clause(a)
        if clause and clause not in clauses:
            clauses.append(clause)

    if not clauses:
        return _strip_fillers(f"{head} (MPN: {mpn})".strip())

    return _strip_fillers(f"{head}, " + ", ".join(clauses))


def build_retail_desc(mfg: str, brand: str, mpn: str, product_name: str, attrs: Dict[str, Any]) -> str:
    """
    Constructs RETAIL_DESC: the customer-facing summary line.

    Ground truth:
        Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel

    Formula: [Series] [Item Type], [top key attributes]. Note it carries NO brand
    and NO MPN -- it sits beside the brand on a product page, so repeating them
    wastes the line. Trailing full stop is omitted to match the delivery file.
    """
    prod = product_name or "Industrial Product"
    series = attrs.get("series", "")

    head = f"{series} {prod}".strip() if series else prod

    clauses: List[str] = []
    for a in _descriptive_attrs(attrs):
        if a.label == "Series":
            continue
        clause = _spec_clause(a)
        if clause and clause not in clauses:
            clauses.append(clause)

    desc = f"{head}, " + ", ".join(clauses[:4]) if clauses else head
    # Anti-fabrication: strip any banned filler that may have leaked in
    return _strip_fillers(desc)


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

    # Anti-fabrication: strip any banned filler that may have leaked in
    return _strip_fillers(" ".join(marketing.split()))


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
        cleaned = _strip_fillers(f)
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
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
