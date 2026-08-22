"""
LOV-Constrained Attribute Extractor
Owned by Member 2.
Extracts technical attributes, units of measure, and features across all industrial MRO categories:
1. Electrical & Lighting (Wattage, Voltage, Amperage, Color Temp, Bulb Base/Shape, Battery Capacity)
2. Dimensions & Sizes (3D, 2D, Single length, Lumber, Thread, Diameters)
   - Full fraction support: 1/2, 3/8, 5/16, 1-1/4 mixed fractions
   - Decimal support: 0.5, .045, 1.25
   - Per-component UOM detection (in / ft) for L x W x H and OD x ID chains
   - Value and UOM are strictly separated (Value = "1/2", UOM column = "in")
3. Abrasives & Cutting Tools (Grit Grade, Package Qty, Shank, Arbor, Teeth,
   Abrasive Material, Backing Material, Max RPM)
4. Building Materials & Trim (Edge Profile, Materials, Finishes, Thermal/R-value)
5. Plumbing, Valves & Fittings (Pressure Class, Connection Type 1/2, Flow Rate,
   End Style, Body Material)
6. Appliances & Kitchen (Wash Cycles, Fuel Type, Mount Type, Sound Level)
7. Fasteners (Thread Size, Fastener Length, Head Type, Drive Type, Finish/Coating)
"""

import re
from typing import Dict, List, Any, Optional

from fuma_engine.schema import AttributeItem

# Member 1 owns UOM/fraction standards (backed by Unilog_Master_UOM_Standards and
# Decimal_Fraction). Member 2 imports them rather than re-deriving units inline --
# two competing UOM implementations was exactly the bug that let "0.5 in" ship
# instead of "1/2 in".
from fuma_rules.uom_standardizer import decimal_to_trade_fraction, standardize_uom


# ---------------------------------------------------------------------------
# Number grammar: complete fractions (1/2, 3/8, 5/16, 1-1/4), decimals
# (0.5, .045, 1.25) and integers. This is THE fix for the compound-fraction
# parsing bug where `1/2"x18"` was misparsed as `2 in`.
# ---------------------------------------------------------------------------
_NUM = r"(?:(?:\d+-)?\d+\s*/\s*\d+|\d*\.\d+|\d+)"

# Material mapping to canonical names
MATERIAL_MAP = {
    "ss": "Stainless Steel",
    "sst": "Stainless Steel",
    "bss": "Stainless Steel",
    "stainless": "Stainless Steel",
    "stainless steel": "Stainless Steel",
    "brs": "Brass",
    "brass": "Brass",
    "bronze": "Bronze",
    "steel": "Steel",
    "carbon steel": "Carbon Steel",
    "galv steel": "Galvanized Steel",
    "galvanized steel": "Galvanized Steel",
    "pvc": "PVC",
    "cpvc": "CPVC",
    "abs": "ABS",
    "hdpe": "HDPE",
    "ci": "Cast Iron",
    "cast iron": "Cast Iron",
    "copper": "Copper",
    "alum": "Aluminum",
    "aluminum": "Aluminum",
    "aluminium": "Aluminum",
    "nylon": "Nylon",
    "rubber": "Rubber",
    "fiberglass": "Fiberglass",
    "vinyl": "Vinyl",
    "osb": "OSB",
    "composite": "Composite",
    "hardie": "HardiePlank",
    "hardieplank": "HardiePlank",
    "cedar": "Cedar",
    "doug fir": "Douglas Fir",
    "fir": "Douglas Fir",
    "mortar": "Mortar",
    "porcelain": "Porcelain",
    "ceramic": "Ceramic",
    "polyester": "Polyester",
    "polycarbonate": "Polycarbonate",
}

# Color / Finish mapping
FINISH_MAP = {
    "bk": "Black",
    "blk": "Black",
    "dbk": "Black",
    "black": "Black",
    "wh": "White",
    "wn": "White",
    "white": "White",
    "ch": "Chrome",
    "chrome": "Chrome",
    "ni": "Brushed Nickel",
    "brushed nickel": "Brushed Nickel",
    "bn": "Brushed Nickel",
    "cpz": "Champagne Bronze",
    "avi": "Anvil Iron",
    "charcoal": "Charcoal",
    "coastline": "Coastline",
    "french white oak": "French White Oak",
    "american walnut": "American Walnut",
    "honey grove": "Honey Grove",
    "golden hour": "Golden Hour",
    "carmel": "Carmel",
    "clay": "Clay",
    "dark chocolate": "Dark Chocolate",
    "light buff": "Light Buff",
    "juniper": "Juniper",
    "gray": "Gray",
    "satin": "Satin",
    "matte": "Matte",
    "polished": "Polished",
    "oil rubbed bronze": "Oil Rubbed Bronze",
    "orb": "Oil Rubbed Bronze",
    "antique brass": "Antique Brass",
    "natural": "Natural",
    "clear": "Clear",
    "galvanized": "Galvanized",
    "zinc plated": "Zinc Plated",
    "powder coated": "Powder Coated",
    "anodized": "Anodized",
    "raw": "Raw / Unfinished",
    "unfinished": "Raw / Unfinished",
    "painted": "Painted",
}

# Fitting / valve nouns that qualify a leading fraction as a pipe size.
_PIPE_NOUNS = (
    "CPLG", "COUPLING", "ELBOW", "TEE", "NIPPLE", "BUSHING", "ADAPTER",
    "CAP", "PLUG", "UNION", "CROSS", "REDUCER", "STREET", "VALVE",
    "MPT", "FPT", "FNPT", "MNPT", "NPT", "CXC", "FXF", "MXM", "MXF", "FXM",
)

# Fastener context nouns that unlock thread/head/drive extraction.
_FASTENER_NOUNS = (
    "SCREW", "BOLT", "NUT", "ANCHOR", "LAG", "THREADED", "FASTENER",
    "HEX CAP", "DECK SCREW", "DRYWALL SCREW",
)

_ABRASIVE_CONTEXT_KW = (
    "cut-off", "cut off", "grind", "sanding", "sand", "disc", "wheel",
    "abrasive", "cubitron", "stikit", "hiolit", "steel demon", "speed demon",
    "flap", "abrasanet", "abranet",
)

# Composite decking / railing color names (Trex / Azek / TimberTech families).
DECKING_COLORS = {
    "biscayne": "Biscayne", "jasper": "Jasper", "hatteras": "Hatteras",
    "salt flat": "Salt Flat", "tide pool": "Tide Pool",
    "pebble beach": "Pebble Beach", "malted barley": "Malted Barley",
    "millstone": "Millstone", "whiskey barrel": "Whiskey Barrel",
    "island mist": "Island Mist", "rainier": "Rainier",
    "vintage lantern": "Vintage Lantern", "spiced rum": "Spiced Rum",
    "gravel path": "Gravel Path", "rope swing": "Rope Swing",
    "tiki torch": "Tiki Torch", "lava rock": "Lava Rock",
    "havana gold": "Havana Gold", "tree house": "Tree House",
    "clam shell": "Clam Shell", "saddle": "Saddle",
    "winchester gray": "Winchester Gray", "woodland brown": "Woodland Brown",
    "fire pit": "Fire Pit", "cosmopolitan": "Cosmopolitan",
    "bungalow": "Bungalow", "stone gray": "Stone Gray",
    "slate gray": "Slate Gray", "brownstone": "Brownstone",
}


def convert_decimal_to_fraction(val_str: str) -> str:
    """Deprecated shim -> :func:`fuma_rules.uom_standardizer.decimal_to_trade_fraction`.

    This function previously held a duplicate 15-entry fraction table and was
    never actually called (its only occurrence in the file was its own ``def``).
    It now delegates to Member 1's full 63-entry table sourced from
    ``Decimal_Fraction.xlsx``, so there is exactly one conversion implementation.
    Retained only for backwards compatibility with existing callers/tests.
    """
    return decimal_to_trade_fraction(val_str)



def _norm_num(value: str) -> str:
    """Normalizes a parsed number/fraction token: strips spaces, keeps 1-1/4.

    Handles edge cases:
      '1 - 1/4'  → '1-1/4'
      ' 3/8 '    → '3/8'
      '0.375'    → '0.375'
      '5 / 16'   → '5/16'
    """
    v = re.sub(r"\s+", "", value)  # collapse all whitespace
    return v.strip()


def _peek_uom(text: str, pos: int, default: str = "in") -> str:
    """Inspects the characters right after a number to decide its UOM."""
    rest = text[pos:pos + 5].lstrip()
    if rest.startswith("'"):
        return "ft"
    if rest.startswith('"'):
        return "in"
    low = rest.lower()
    if low.startswith("ft") or low.startswith("feet"):
        return "ft"
    if low.startswith("in"):
        return "in"
    return default


def _has_label(attrs: List[AttributeItem], *labels: str) -> bool:
    want = {l.lower() for l in labels}
    return any(a.label.lower() in want for a in attrs)


#: UOMs whose values are dimensional and therefore expressed as trade fractions.
#: Ratings (V, A, W, dBA, gpm) stay decimal -- "120 V" not "120-0/1 V".
_FRACTIONAL_UOMS = frozenset({"in", "ft", "yd"})


def _add(attrs: List[AttributeItem], label: str, value: str, uom: str = "") -> None:
    """Appends an attribute with strictly separated Value / UOM columns.

    THE SINGLE NORMALISATION CHOKE POINT. Every attribute in the pipeline is
    created here, so applying the Unilog standards at this one site guarantees
    they are applied everywhere:

      1. UOM -> approved abbreviation ("inches"/"IN."/'"' -> "in", "volts" -> "V")
      2. Dimensional decimals -> trade fractions (0.5 -> 1/2, 50.25 -> 50-1/4)
      3. Value and UOM stay in separate columns, so the delivery file can render
         "24 in" with the mandatory space and never "24in"
    """
    value = str(value or "").strip()
    uom = str(uom or "").strip()
    if not value:
        return

    # 1. Approved UOM abbreviation.
    if uom:
        uom = standardize_uom(uom)

    # 2. Trade fractions for dimensional values only.
    if uom in _FRACTIONAL_UOMS and re.fullmatch(r"\d*\.\d+|\d+", value):
        value = decimal_to_trade_fraction(value)

    attrs.append(AttributeItem(label=label, value=value, uom=uom))



def _is_abrasive(category: str, text_lower: str) -> bool:
    cat = (category or "").lower()
    if any(k in cat for k in ("cut-off", "grinding", "sanding", "abrasive")):
        return True
    return any(k in text_lower for k in _ABRASIVE_CONTEXT_KW)


def _is_fitting(category: str, text_lower: str) -> bool:
    cat = (category or "").lower()
    if any(k in cat for k in ("pipe fitting", "fitting", "valve", "faucet", "coupling")):
        return True
    return any(k in text_lower for k in (
        "cplg", "coupling", "elbow", "nipple", "bushing", "fnpt", "mnpt",
        "push-fit", "push fit", "ball valve", "gate valve", "check valve",
    ))


def _is_fastener(category: str, text_upper: str) -> bool:
    cat = (category or "").upper()
    if "FASTENER" in cat or "NAIL" in cat:
        return True
    return any(k in text_upper for k in _FASTENER_NOUNS)


def _apply_category_defaults(
    category: str,
    text: str,
    attrs: List[AttributeItem],
    dimensions: Dict[str, str],
    material: str,
    connection_type: str,
    classpath: str = "",
) -> None:
    """
    Taxonomy-driven enrichment: infers standard structural attributes for
    high-frequency categories (Abrasives, Fittings & Valves, Fasteners,
    Decking & Railing, Appliances, Windows & Doors) plus a universal
    taxonomy-grounded baseline, normalized to the Unilog LOV style guide.
    """
    t_lower = text.lower()
    t_upper = text.upper()
    cat_lower = (category or "").lower()

    # ------------------------------------------------------------------
    # 0. Universal taxonomy-grounded baseline (every classified row)
    # ------------------------------------------------------------------
    if category:
        if not _has_label(attrs, "Product Type"):
            _add(attrs, "Product Type", category)
        if classpath and not _has_label(attrs, "Application"):
            leaf = classpath.split(">")[-1].strip()
            if leaf and leaf.lower() != cat_lower:
                _add(attrs, "Application", leaf)

    # ------------------------------------------------------------------
    # A. Cutting / Abrasives
    # ------------------------------------------------------------------
    if _is_abrasive(category, t_lower):
        if not _has_label(attrs, "Abrasive Material"):
            if re.search(r"cubitron", t_lower):
                abrasive = "Ceramic Alumina"
            elif re.search(r"zirconia|steel demon", t_lower):
                abrasive = "Zirconia Alumina"
            elif re.search(r"silicon carbide|wet/dry|wet dry", t_lower):
                abrasive = "Silicon Carbide"
            elif re.search(r"diamond", t_lower):
                abrasive = "Diamond"
            else:
                abrasive = "Aluminum Oxide"
            _add(attrs, "Abrasive Material", abrasive)

        if not _has_label(attrs, "Backing Material"):
            if re.search(r"\bfilm\b|stikit film|polyester film", t_lower):
                backing = "Polyester Film"
            elif re.search(r"\bbelt\b|\bcloth\b", t_lower):
                backing = "Cloth"
            elif re.search(r"abranet|abrasanet|\bnet\b", t_lower):
                backing = "Abrasive Net"
            elif re.search(r"sponge|block", t_lower):
                backing = "Foam"
            elif re.search(r"cut-off|cut off|grinding wheel|type 1|type 27", t_lower):
                backing = "Fiber"
            else:
                backing = "Paper"
            _add(attrs, "Backing Material", backing)

        if not _has_label(attrs, "Max RPM"):
            rpm = re.search(r"(\d{4,6})\s*rpm", t_lower)
            if rpm:
                _add(attrs, "Max RPM", rpm.group(1), "RPM")

        if not _has_label(attrs, "Arbor / Shank Size", "Arbor Size"):
            arb = re.search("(" + _NUM + r')\s*"?\s*(?:arbor|shank)', text, re.IGNORECASE)
            if not arb:
                arb = re.search(r"(?:arbor|shank)\s*[:\-]?\s*(" + _NUM + r')', text, re.IGNORECASE)
            if arb:
                val = _norm_num(arb.group(1))
                _add(attrs, "Arbor Size", val, "in")
                dimensions.setdefault("arbor", val)

    # ------------------------------------------------------------------
    # B. Fittings & Valves
    # ------------------------------------------------------------------
    if _is_fitting(category, t_lower):
        # Rename generic Material -> Body Material per Unilog LOV standards.
        for a in attrs:
            if a.label == "Material":
                a.label = "Body Material"
                break
        if material and not _has_label(attrs, "Body Material"):
            _add(attrs, "Body Material", material)

        # Split combined connection types into Connection Type 1 / 2.
        conn_attrs = [a for a in attrs if a.label == "Connection Type"]
        if conn_attrs:
            combined = conn_attrs[0].value
            conn_attrs[0].label = "Connection Type 1"
            parts = re.split(r"\s+x\s+", combined, flags=re.IGNORECASE)
            if len(parts) > 1:
                _add(attrs, "Connection Type 2", parts[1])
        elif connection_type:
            _add(attrs, "Connection Type 1", connection_type)

        # End Style derived from connection / construction cues.
        if not _has_label(attrs, "End Style"):
            if re.search(r"push[\s-]?fit", t_lower):
                end_style = "Push-Fit"
            elif re.search(r"sweat|solder", t_lower):
                end_style = "Sweat / Solder"
            elif re.search(r"flange", t_lower):
                end_style = "Flanged"
            elif re.search(r"fnpt|fpt|female", t_lower):
                end_style = "Female Threaded"
            elif re.search(r"mnpt|mpt|male", t_lower):
                end_style = "Male Threaded"
            elif re.search(r"npt|thread", t_lower):
                end_style = "Threaded"
            elif re.search(r"solvent|socket", t_lower):
                end_style = "Solvent Weld"
            else:
                end_style = ""
            if end_style:
                _add(attrs, "End Style", end_style)

    # ------------------------------------------------------------------
    # C. Fasteners
    # ------------------------------------------------------------------
    if _is_fastener(category, t_upper):
        if not _has_label(attrs, "Thread Size"):
            # Gauge form: #10-32, #8
            gauge = re.search(r"#(\d+)(?:\s*-\s*(\d{1,2}))?(?!\d)", t_upper)
            # Fraction form: 1/4-20, 5/16-18, M8-1.25
            frac_thread = re.search(
                "(" + _NUM + r')\s*-\s*(\d{1,2})(?![\d/.])(?:\s*(?:TPI|THREADS?))?\b',
                t_upper,
            )
            if frac_thread and not re.search(r"\b(?:CLASS|GRADE)\b", t_upper):
                major = _norm_num(frac_thread.group(1))
                tpi = frac_thread.group(2)
                _add(attrs, "Thread Size", f"{major}-{tpi}" if tpi else major)
            elif gauge:
                tpi = gauge.group(2)
                _add(attrs, "Thread Size", f"#{gauge.group(1)}-{tpi}" if tpi else f"#{gauge.group(1)}")

        if not _has_label(attrs, "Fastener Length"):
            len_by_x = re.search(r"[xX]\s*(" + _NUM + r')\s*(?:"|in\b|inch)', text)
            len_explicit = re.search(r"(" + _NUM + r')\s*(?:"|in\b|inch)\s*(?:LONG|LG\b)', t_upper)
            m = len_by_x or len_explicit
            if m:
                _add(attrs, "Fastener Length", _norm_num(m.group(1)), "in")

        if not _has_label(attrs, "Head Type"):
            head = re.search(
                r"(hex head|pan head|flat head|round head|truss head|bugle|wafer head|modified truss|oval head)",
                t_lower,
            )
            if head:
                _add(attrs, "Head Type", head.group(1).title())

        if not _has_label(attrs, "Drive Type"):
            drive = re.search(
                r"(phillips|torx|star drive|square drive|slotted|hex socket|allen|combo drive|quadrex)",
                t_lower,
            )
            if drive:
                _add(attrs, "Drive Type", drive.group(1).title())

        if not _has_label(attrs, "Finish / Coating"):
            finish = re.search(
                r"(mechanically galvanized|hot dip galvanized|galvanized|zinc plated|zinc|black oxide|black phosphate|ceramic coated|dacrotized|bright|yellow dichromate)",
                t_lower,
            )
            if finish:
                canonical = {
                    "galvanized": "Galvanized",
                    "hot dip galvanized": "Hot Dip Galvanized",
                    "mechanically galvanized": "Mechanically Galvanized",
                    "zinc": "Zinc Plated",
                    "zinc plated": "Zinc Plated",
                    "black oxide": "Black Oxide",
                    "black phosphate": "Black Phosphate",
                    "ceramic coated": "Ceramic Coated",
                    "dacrotized": "Dacrotized",
                    "bright": "Bright",
                    "yellow dichromate": "Yellow Dichromate",
                }.get(finish.group(1), finish.group(1).title())
                _add(attrs, "Finish / Coating", canonical)

    # ------------------------------------------------------------------
    # D. Decking, Railing & Fascia (composite boards)
    # ------------------------------------------------------------------
    if any(k in cat_lower for k in ("decking", "railing", "fascia")) or re.search(
        r"trex|azek|timbertech", t_lower
    ):
        if not _has_label(attrs, "Material") and re.search(
            r"trex|azek|timbertech|composite", t_lower
        ):
            _add(attrs, "Material", "Composite")

        if not _has_label(attrs, "Color / Finish"):
            for token, canonical in DECKING_COLORS.items():
                if re.search(r"\b" + re.escape(token) + r"\b", t_lower):
                    _add(attrs, "Color / Finish", canonical)
                    break

        if not _has_label(attrs, "Board Type"):
            if re.search(r"fascia", t_lower):
                _add(attrs, "Board Type", "Fascia Board")
            elif re.search(r"decking|deck board", t_lower):
                _add(attrs, "Board Type", "Deck Board")
            elif re.search(r"rail kit|railing", t_lower):
                _add(attrs, "Board Type", "Rail Kit")

    # ------------------------------------------------------------------
    # E. Appliances (kitchen & laundry)
    # ------------------------------------------------------------------
    if any(k in cat_lower for k in (
        "dishwasher", "refrigerator", "microwave", "cooking appliance",
        "laundry appliance", "beverage center", "coffee",
    )):
        if not _has_label(attrs, "Power Source", "Fuel Type"):
            if re.search(r"\bgas\b", t_lower):
                _add(attrs, "Fuel Type", "Gas")
            else:
                # Dishwashers, washers and refrigerators are mains-electric.
                _add(attrs, "Power Source", "Electric")
        if "dishwasher" in cat_lower and not _has_label(attrs, "Installation Type"):
            _add(attrs, "Installation Type", "Built-In")

    # ------------------------------------------------------------------
    # F. Windows & Doors (glass package cues)
    # ------------------------------------------------------------------
    if any(k in cat_lower for k in ("window", "door")) or re.search(
        r"patio dr|gliding|low[\s-]?e", t_lower
    ):
        if not _has_label(attrs, "Glass Type") and re.search(
            r"low[\s-]?e|lowemissivity", t_lower
        ):
            _add(attrs, "Glass Type", "Low-E")
        if not _has_label(attrs, "Gas Fill") and re.search(r"argon|\barg\b", t_lower):
            _add(attrs, "Gas Fill", "Argon")


def extract_attributes(raw_desc: str, mfg_part_num: str = "", category: str = "", manufacturer_name: str = "", classpath: str = "") -> Dict[str, Any]:
    """
    Extracts comprehensive structured attributes from raw descriptions across all industrial categories.
    Values and UOMs are strictly separated per the Unilog style guide.
    """
    text = f"{raw_desc} {mfg_part_num} {manufacturer_name}".strip()
    extracted_attrs: List[AttributeItem] = []
    features: List[str] = []

    series = ""
    mount_type = ""
    material = ""
    finish = ""
    voltage = ""
    amperage = ""
    sound_level = ""
    package_qty = ""
    pressure_class = ""
    connection_type = ""
    flow_rate = ""
    dimensions: Dict[str, str] = {}

    # 1. Detect Series / Product Line
    for s in ['Enhance Naturals', 'Transcend Lineage', 'Vintage', 'Landmark', 'Steel Demon', 'Speed Demon', 'Cubitron II', 'Cubitron™ II', 'Abranet', 'Hiolit', 'Professional Series', 'Eco Series', 'Duration TruDef', 'Blue Plus', 'Stikit']:
        if re.search(r'\b' + re.escape(s) + r'\b', text, re.IGNORECASE):
            series = s
            _add(extracted_attrs, "Series", series)
            break

    # 2. Electrical: Wattage (e.g., 60W, 100W, 40W, 15W)
    w_match = re.search(r'\b(\d+)\s*w\b', text, re.IGNORECASE)
    if w_match:
        _add(extracted_attrs, "Wattage Rating", w_match.group(1), "W")

    # 3. Electrical: Voltage (e.g., M18, M12, 120V, 60V, 20V, 12V, 240V)
    v_match = re.search(r'\b(\d+)\s*(?:v|volt|volts|vac)\b', text, re.IGNORECASE)
    if v_match:
        voltage = v_match.group(1)
        _add(extracted_attrs, "Voltage Rating", voltage, "V")
    elif re.search(r'\bm18\b', text, re.IGNORECASE):
        voltage = "18"
        _add(extracted_attrs, "Voltage Rating", voltage, "V")
    elif re.search(r'\bm12\b', text, re.IGNORECASE):
        voltage = "12"
        _add(extracted_attrs, "Voltage Rating", voltage, "V")

    # 4. Electrical: Amperage & Battery Capacity (e.g. 15A, 10A, 12AH, 12V12AH)
    v_ah = re.search(r'(\d+)\s*v\s*(\d+(?:\.\d+)?)\s*ah', text, re.IGNORECASE)
    if v_ah:
        if not voltage:
            voltage = v_ah.group(1)
            _add(extracted_attrs, "Voltage Rating", voltage, "V")
        _add(extracted_attrs, "Battery Capacity", v_ah.group(2), "Ah")
    else:
        a_match = re.search(r'\b(\d+)\s*(?:a|amp|amps)\b', text, re.IGNORECASE)
        if a_match:
            amperage = a_match.group(1)
            _add(extracted_attrs, "Amperage Rating", amperage, "A")
        ah_match = re.search(r'\b(\d+(?:\.\d+)?)\s*ah\b', text, re.IGNORECASE)
        if ah_match:
            _add(extracted_attrs, "Battery Capacity", ah_match.group(1), "Ah")

    # 4b. Battery Group Size (e.g. 8D Battery)
    b_group = re.search(r'\b(8D|24F|27F|31|34|35|48|49|51R|65|78)\s*Battery\b', text, re.IGNORECASE)
    if b_group:
        _add(extracted_attrs, "Battery Group Size", b_group.group(1).upper())

    # 5. Color Temperature (27k -> 2700 K, 50k -> 5000 K, 30k -> 3000 K, 5CCT, Multi CCT)
    k_match = re.search(r'\b(\d{1,2})k\b', text, re.IGNORECASE)
    if k_match:
        _add(extracted_attrs, "Color Temperature", f"{k_match.group(1)}00", "K")
    elif re.search(r'\b(?:multi cct|5cct|selectable cct)\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Color Temperature", "Selectable CCT")

    # 6. Bulb Shape / Base (BR30, A19, PAR38, Cand, Med)
    shape_match = re.search(r'\b(BR30|A19|PAR38|PAR30|MR16|B10|G25|T8|T5|Cand|Med)\b', text, re.IGNORECASE)
    if shape_match:
        _add(extracted_attrs, "Bulb Base / Shape", shape_match.group(1).upper())

    # 7. Acoustics: Sound Level (e.g., 47 dBA, 41DBA)
    sound_match = re.search(r'(\d+)\s*(?:dba|db)\b', text, re.IGNORECASE)
    if sound_match:
        sound_level = sound_match.group(1)
        _add(extracted_attrs, "Sound Level", sound_level, "dBA")

    # 8. Dimensions - 3D (e.g. 5"x.045"x7/8", 12"x1/8"x1", 1.5x1.5x13')
    dim3 = re.search(
        "(" + _NUM + r')\s*["\']?\s*[xX]\s*(' + _NUM + r')\s*["\']?\s*[xX]\s*(' + _NUM + r')\s*["\']?',
        text,
    )
    if dim3:
        d, t, a = (_norm_num(g) for g in dim3.groups())
        d_uom = _peek_uom(text, dim3.end(1))
        t_uom = _peek_uom(text, dim3.end(2), default=d_uom)
        a_uom = _peek_uom(text, dim3.end(3), default=d_uom)
        _add(extracted_attrs, "Diameter / Length", d, d_uom)
        _add(extracted_attrs, "Thickness", t, t_uom)
        _add(extracted_attrs, "Arbor / Shank Size", a, a_uom)
        dimensions["diameter"] = d
        dimensions["thickness"] = t
        dimensions["arbor"] = a
    else:
        # Lumber / Decking (e.g. 1x6-16', 1x12-12', 1nx6-16', 4x4-39, 6x6-108, 4x4-108)
        dim_lumber = re.search(r"(\d+n?)\s*[xX]\s*(\d+)\s*[- ]\s*(\d+)'?", text)
        if dim_lumber:
            t, w, l = dim_lumber.groups()
            t_clean = t.replace('n', '')
            l_uom = _peek_uom(text, dim_lumber.end(3), default="in")
            _add(extracted_attrs, "Thickness", t_clean, "in")
            _add(extracted_attrs, "Width", w, "in")
            _add(extracted_attrs, "Length", l, l_uom)
            dimensions["thickness"] = t_clean
            dimensions["width"] = w
            dimensions["length"] = l
        else:
            # 2D dimensions (e.g. 14"x1", 1/2"x18", 3'x65', 80x133, 24x48,
            # 31.5x14.75, 2.75x30, 2"x50')
            dim2 = re.search(
                "(" + _NUM + r')\s*["\']?\s*[xX]\s*(' + _NUM + r')\s*["\']?',
                text,
            )
            if dim2:
                w, l = (_norm_num(g) for g in dim2.groups())
                w_uom = _peek_uom(text, dim2.end(1))
                l_uom = _peek_uom(text, dim2.end(2), default=w_uom)
                ctx = f"{category} {text}".lower()
                if _is_abrasive(category, ctx) and "belt" not in ctx:
                    # Abrasive discs: OD x Arbor/Thickness (e.g. 14"x1", 4-1/2"x1/4")
                    second_label = "Arbor / Shank Size" if _to_float(l) is not None and _to_float(l) <= 1.5 else "Thickness"
                    _add(extracted_attrs, "Diameter", w, w_uom)
                    _add(extracted_attrs, second_label, l, l_uom)
                    dimensions["diameter"] = w
                    dimensions["arbor" if second_label.startswith("Arbor") else "thickness"] = l
                else:
                    _add(extracted_attrs, "Width", w, w_uom)
                    _add(extracted_attrs, "Length", l, l_uom)
                    dimensions["width"] = w
                    dimensions["length"] = l

    # 9. Single Length / Diameter / Range
    if not any(a.label in (
        'Dimensions', 'Length', 'Width', 'Diameter / Length', 'Diameter',
        'Thickness', 'Arbor / Shank Size', 'Diameter / Size',
    ) for a in extracted_attrs):
        single_len = re.search(r"\b(" + _NUM + r")\s*(?:'|ft\b|feet\b)", text, re.IGNORECASE)
        if single_len:
            val = _norm_num(single_len.group(1))
            _add(extracted_attrs, "Length", val, "ft")
            dimensions["length"] = val
        else:
            spindle_m = re.search(r'(' + _NUM + r')\s*(?:\"|in\b|inch)?\s*(?:spindle|arbor|shank|collet)', text, re.IGNORECASE)
            if spindle_m:
                val = _norm_num(spindle_m.group(1))
                _add(extracted_attrs, "Arbor / Spindle Size", val, "in")
                dimensions["arbor"] = val
            else:
                single_in = re.search(r'(' + _NUM + r')\s*(?:"|in\b|inches\b|inch\b)', text, re.IGNORECASE)
                if single_in:
                    val = _norm_num(single_in.group(1))
                    _add(extracted_attrs, "Diameter / Size", val, "in")
                    dimensions["diameter"] = val
                else:
                    # Pipe size: fraction/number directly attached to a fitting noun
                    # (e.g. `3/8 CPLG`, `1/2 INCH ELBOW`) - fixes dropped numerators.
                    pipe = re.search(
                        '(' + _NUM + r')\s*[-]?\s*(?:' + "|".join(_PIPE_NOUNS) + r')\b',
                        text,
                        re.IGNORECASE,
                    )
                    if pipe:
                        val = _norm_num(pipe.group(1))
                        _add(extracted_attrs, "Diameter / Size", val, "in")
                        dimensions["diameter"] = val
                    else:
                        # True size range (e.g. "fits 2-4 in"); rejects fractions
                        # like 50-1/4 and MPN fragments like 332-080.
                        range_match = re.search(
                            r'(?<![\w./-])(\d+)\s*-\s*(\d+)(?![\w./-])', text
                        )
                        if range_match:
                            _add(
                                extracted_attrs,
                                "Size Range",
                                f"{range_match.group(1)} - {range_match.group(2)}",
                                "in",
                            )

    # 10. Grit Grade (P80, P120, 60G, 80 Grit)
    grit = re.search(r'\b(P\d{2,4}|\d{2,3}\s*Grit|\d{2,3}G)\b', text, re.IGNORECASE)
    if grit:
        _add(extracted_attrs, "Grit Grade", grit.group(1).upper().replace(" ", ""))

    # 11. Package Quantity / Ports / Coverage (2pk, 3pk, 5pk, 50 Disc/Box, 6pc, PRO/10, 2pc, 2 Port, 2sq)
    qty = re.search(r'(\d+)\s*(?:pk|pack|pc|disc/box|pro/\d+|box|port|sq)\b', text, re.IGNORECASE)
    if qty:
        package_qty = qty.group(1)
        _add(extracted_attrs, "Package Quantity", package_qty)
    else:
        # Parenthesized quantities: (100), qty 25, box/100, bx100, /1000
        qty2 = re.search(r'(?:qty\s*|bx|box/|/)\s*(\d+)\b|\((\d{2,})\)\s*(?:ct|count)?', text, re.IGNORECASE)
        if qty2:
            package_qty = qty2.group(1) or qty2.group(2)
            _add(extracted_attrs, "Package Quantity", package_qty)
        else:
            ct_match = re.search(r'(\d+)\s*ct\b', text, re.IGNORECASE)
            if ct_match:
                package_qty = ct_match.group(1)
                _add(extracted_attrs, "Package Quantity", package_qty)

    # 12. Material Construction
    for token, canonical in MATERIAL_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            material = canonical
            _add(extracted_attrs, "Material", material)
            break

    # 13. Color / Finish
    for token, canonical in FINISH_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            finish = canonical
            _add(extracted_attrs, "Color / Finish", finish)
            break
    if not finish and mfg_part_num:
        # Check MPN suffix for standard manufacturer finish codes
        mpn_upper = mfg_part_num.upper()
        mpn_finish_map = [
            ("BKCLR", "Black / Clear"), ("BKCS", "Black / Clear Seeded Glass"),
            ("DBK", "Black"), ("CPZ", "Champagne Bronze"), ("AVI", "Anvil Iron"),
            ("BSS", "Stainless Steel"), ("SST", "Stainless Steel"), ("SS", "Stainless Steel"),
            ("NI", "Brushed Nickel"), ("BN", "Brushed Nickel"), ("BK", "Black"),
            ("WH", "White"), ("CH", "Chrome"), ("BRS", "Brass"), ("SBE", "Black"),
            ("SJP", "Juniper"), ("KPS", "Stainless Steel"), ("SPS", "Stainless Steel"),
            ("WE", "White"), ("BE", "Black"), ("WHA", "White"),
        ]
        for code, canonical in mpn_finish_map:
            if mpn_upper.endswith(code):
                finish = canonical
                _add(extracted_attrs, "Color / Finish", finish)
                break

    # 13b. Power Tools & Machinery Specifications
    drive_m = re.search(r'(' + _NUM + r')\s*(?:\"|in\b|inch)?\s*(?:drive|impact|rachet|ratchet|hex\s*hydraulic|hex\s*driver|hex)', text, re.IGNORECASE)
    if drive_m and not _has_label(extracted_attrs, "Drive / Chuck Size"):
        drv_val = _norm_num(drive_m.group(1))
        _add(extracted_attrs, "Drive / Chuck Size", drv_val, "in")

    if re.search(r'friction ring', text, re.IGNORECASE):
        _add(extracted_attrs, "Anvil / Retainer Type", "Friction Ring")
    elif re.search(r'pin detent', text, re.IGNORECASE):
        _add(extracted_attrs, "Anvil / Retainer Type", "Pin Detent")
    elif re.search(r'interchangeable anvil', text, re.IGNORECASE):
        _add(extracted_attrs, "Anvil / Retainer Type", "Interchangeable Anvil")
    elif re.search(r'open head', text, re.IGNORECASE):
        _add(extracted_attrs, "Head Style", "Open Head")

    if re.search(r'\(bare\)|bare tool|tool only|tool - only', text, re.IGNORECASE):
        _add(extracted_attrs, "Tool Configuration", "Bare Tool (Tool Only)")
    elif re.search(r'\bkit\b|\b2pc kit\b|starter kit', text, re.IGNORECASE):
        _add(extracted_attrs, "Tool Configuration", "Kit with Battery & Charger")

    if re.search(r'\bbrushless\b|\bfuel\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Motor Type", "Brushless")

    hp_m = re.search(r'(' + _NUM + r')\s*hp\b', text, re.IGNORECASE)
    if hp_m:
        _add(extracted_attrs, "Horsepower Rating", _norm_num(hp_m.group(1)), "HP")

    phase_m = re.search(r'\b(1ph|1 ph|1-phase|1\s*phase|3ph|3 ph|3-phase)\b', text, re.IGNORECASE)
    if phase_m:
        _add(extracted_attrs, "Electrical Phase", "1-Phase" if "1" in phase_m.group(1) else "3-Phase")

    if re.search(r'\b(laser|cross line)\b', text, re.IGNORECASE):
        if re.search(r'\bgreen\b', text, re.IGNORECASE):
            _add(extracted_attrs, "Laser Beam Color", "Green")
        elif re.search(r'\bred\b', text, re.IGNORECASE):
            _add(extracted_attrs, "Laser Beam Color", "Red")
        if re.search(r'3 spot', text, re.IGNORECASE):
            _add(extracted_attrs, "Beam Configuration", "3-Spot")
        elif re.search(r'5 spot', text, re.IGNORECASE):
            _add(extracted_attrs, "Beam Configuration", "5-Spot")

    # 14. Mounting Type / Fixture Type
    if re.search(r'\b(wall lt|wall light|wall mount)\b', text, re.IGNORECASE):
        mount_type = "Wall Mount"
        _add(extracted_attrs, "Mounting Type", mount_type)
    elif re.search(r'\b(bath light|vanity)\b', text, re.IGNORECASE):
        mount_type = "Vanity / Bath"
        _add(extracted_attrs, "Mounting Type", mount_type)
    elif re.search(r'\b(strip light)\b', text, re.IGNORECASE):
        mount_type = "Surface Mount"
        _add(extracted_attrs, "Mounting Type", mount_type)
    elif re.search(r'\b(down light|recessed)\b', text, re.IGNORECASE):
        mount_type = "Recessed"
        _add(extracted_attrs, "Mounting Type", mount_type)
    elif re.search(r'\bleg\b', text, re.IGNORECASE):
        mount_type = "Leg"
        _add(extracted_attrs, "Mounting Type", mount_type)
    elif re.search(r'\bbuilt-in\b|\bbltln\b|\bbuilt in\b', text, re.IGNORECASE):
        mount_type = "Built-in"
        _add(extracted_attrs, "Mounting Type", mount_type)

    # 15. Power Source / Fuel Type (Gas, Electric)
    if re.search(r'\bgas\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Fuel Type", "Gas")
    elif re.search(r'\b(elect|electric)\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Power Source", "Electric")

    # 16. Flow Rate (e.g. 1.2 gpm, 1.5 GPM, 2.2 GPM)
    flow_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:gpm|g/m)\b', text, re.IGNORECASE)
    if flow_match:
        flow_rate = flow_match.group(1)
        _add(extracted_attrs, "Flow Rate", flow_rate, "gpm")

    # 17. Pressure Class (e.g. 150#, 300#, Class 150)
    press_match = re.search(r'(\d+)\s*(?:#|lb\b|class\s*\d+)', text, re.IGNORECASE)
    if press_match:
        pressure_class = f"Class {press_match.group(1)}"
        _add(extracted_attrs, "Pressure Class", pressure_class)

    # 18. Connection Type (e.g. FNPT x MNPT, NPT, Push-Fit, Flanged)
    if re.search(r'\bfnpt\s*x\s*mnpt\b', text, re.IGNORECASE):
        connection_type = "FNPT x MNPT"
    elif re.search(r'\bfnpt\b', text, re.IGNORECASE):
        connection_type = "FNPT"
    elif re.search(r'\bmnpt\b', text, re.IGNORECASE):
        connection_type = "MNPT"
    elif re.search(r'\bnpt\b', text, re.IGNORECASE):
        connection_type = "NPT"
    if connection_type:
        _add(extracted_attrs, "Connection Type", connection_type)

    # 19. Wash Cycles
    cycle_match = re.search(r'(\d+)\s*[- ]?(?:wash cycle|cycles|cycle)\b', text, re.IGNORECASE)
    if cycle_match:
        _add(extracted_attrs, "Number of Wash Cycles", cycle_match.group(1))

    # 20. Depth With Door Open
    door_depth_match = re.search(r'(' + _NUM + r')\s*(?:in|inch|"|in\.)\s*(?:depth with door open|depth)', text, re.IGNORECASE)
    if door_depth_match:
        door_depth = _norm_num(door_depth_match.group(1))
        _add(extracted_attrs, "Depth With Door Open", door_depth, "in")
        dimensions["depth_with_door_open"] = door_depth
    elif re.search(r'50-1/4IN', text, re.IGNORECASE):
        _add(extracted_attrs, "Depth With Door Open", "50-1/4", "in")
        dimensions["depth_with_door_open"] = "50-1/4"

    # 21. Edge Profile (Sq Edge, Grooved, T&G)
    if re.search(r'\b(sq edge|square edge|sq ed)\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Edge Profile", "Square Edge")
    elif re.search(r'\bgrooved\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Edge Profile", "Grooved")
    elif re.search(r'\bt&g\b', text, re.IGNORECASE):
        _add(extracted_attrs, "Edge Profile", "Tongue & Groove")

    # 22. Features
    if re.search(r'cleanboost', text, re.IGNORECASE):
        features.append("With CleanBoost™")
    if re.search(r'3rd rack', text, re.IGNORECASE):
        features.append("3rd Rack")
    if re.search(r'stikit', text, re.IGNORECASE):
        features.append("Stikit™ Attachment")
    if re.search(r'dko', text, re.IGNORECASE):
        features.append("Dual Knockout (DKO)")

    # 23. Taxonomy-driven structural defaults & LOV label normalization
    _apply_category_defaults(
        category, text, extracted_attrs, dimensions, material, connection_type,
        classpath=classpath,
    )

    return {
        "attributes": extracted_attrs,
        "features": features,
        "series": series,
        "mount_type": mount_type,
        "material": material,
        "finish": finish,
        "voltage": voltage,
        "amperage": amperage,
        "sound_level": sound_level,
        "package_qty": package_qty,
        "pressure_class": pressure_class,
        "connection_type": connection_type,
        "flow_rate": flow_rate,
        "dimensions": dimensions
    }


def _to_float(value: str) -> Optional[float]:
    """Best-effort numeric parse of a fraction/decimal token ('1-1/4' -> 1.25)."""
    try:
        v = value.strip()
        whole = 0.0
        if "-" in v and "/" in v:
            w, frac = v.split("-", 1)
            whole = float(w)
            num, den = frac.split("/", 1)
            return whole + float(num) / float(den)
        if "/" in v:
            num, den = v.split("/", 1)
            return float(num) / float(den)
        return float(v)
    except Exception:
        return None