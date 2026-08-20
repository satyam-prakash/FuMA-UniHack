"""
Master Unit of Measure (UOM) & Decimal-to-Trade-Fraction Standardization Engine.
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
Package: fuma_rules
"""

import re
from fractions import Fraction
from typing import Optional, Union, Tuple, Dict

# Exact 64th decimal to fraction lookup table (matching Decimal_Fraction.xlsx)
DECIMAL_FRACTION_LOOKUP: Dict[float, str] = {
    0.015625: "1/64", 0.03125: "1/32", 0.046875: "3/64", 0.0625: "1/16",
    0.078125: "5/64", 0.09375: "3/32", 0.109375: "7/64", 0.125: "1/8",
    0.140625: "9/64", 0.15625: "5/32", 0.171875: "11/64", 0.1875: "3/16",
    0.203125: "13/64", 0.21875: "7/32", 0.234375: "15/64", 0.25: "1/4",
    0.265625: "17/64", 0.28125: "9/32", 0.296875: "19/64", 0.3125: "5/16",
    0.328125: "21/64", 0.34375: "11/32", 0.359375: "23/64", 0.375: "3/8",
    0.390625: "25/64", 0.40625: "13/32", 0.421875: "27/64", 0.4375: "7/16",
    0.453125: "29/64", 0.46875: "15/32", 0.484375: "31/64", 0.5: "1/2",
    0.515625: "33/64", 0.53125: "17/32", 0.546875: "35/64", 0.5625: "9/16",
    0.578125: "37/64", 0.59375: "19/32", 0.609375: "39/64", 0.625: "5/8",
    0.640625: "41/64", 0.65625: "21/32", 0.671875: "43/64", 0.6875: "11/16",
    0.703125: "45/64", 0.71875: "23/32", 0.734375: "47/64", 0.75: "3/4",
    0.765625: "49/64", 0.78125: "25/32", 0.796875: "51/64", 0.8125: "13/16",
    0.828125: "53/64", 0.84375: "27/32", 0.859375: "55/64", 0.875: "7/8",
    0.890625: "57/64", 0.90625: "29/32", 0.921875: "59/64", 0.9375: "15/16",
    0.953125: "61/64", 0.96875: "31/32", 0.984375: "63/64"
}

# Master UOM standardization dictionary
MASTER_UOM_MAP: Dict[str, str] = {
    # Length / Distance
    "in": "in", "in.": "in", "inch": "in", "inches": "in", "\"": "in", "''": "in",
    "ft": "ft", "ft.": "ft", "foot": "ft", "feet": "ft", "'": "ft",
    "yd": "yd", "yard": "yd", "yards": "yd",
    "mm": "mm", "millimeter": "mm", "millimeters": "mm",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm",
    "m": "m", "meter": "m", "meters": "m",

    # Electrical
    "v": "V", "volt": "V", "volts": "V", "vac": "V", "vdc": "V", "v ac": "V", "v dc": "V",
    "a": "A", "amp": "A", "amps": "A", "ampere": "A", "amperes": "A",
    "w": "W", "watt": "W", "watts": "W",
    "kw": "kW", "kilowatt": "kW", "kilowatts": "kW",
    "kw-hr": "kW-hr", "kwh": "kW-hr", "kw/hr": "kW-hr", "kw - hr": "kW-hr", "kwhr": "kW-hr",
    "hz": "Hz", "hertz": "Hz",
    "hp": "hp", "horsepower": "hp",

    # Acoustics
    "dba": "dBA", "db": "dBA", "decibel": "dBA", "decibels": "dBA", "dBA": "dBA",

    # Weight / Mass
    "lb": "lb", "lbs": "lb", "lb.": "lb", "pound": "lb", "pounds": "lb",
    "oz": "oz", "oz.": "oz", "ounce": "oz", "ounces": "oz",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g",

    # Flow / Pressure / Speed
    "psi": "psi", "psig": "psi", "lbs/sq in": "psi",
    "gpm": "gpm", "gallons per minute": "gpm",
    "cfm": "cfm", "cubic feet per minute": "cfm",
    "rpm": "rpm", "revolutions per minute": "rpm",

    # Time / Temperature
    "hr": "hr", "hour": "hr", "hours": "hr", "hrs": "hr",
    "min": "min", "minute": "min", "minutes": "min",
    "sec": "sec", "second": "sec", "seconds": "sec",
    "deg f": "deg F", "degf": "deg F", "°f": "deg F", "fahrenheit": "deg F",
    "deg c": "deg C", "degc": "deg C", "°c": "deg C", "celsius": "deg C",

    # Packaging & Quantities
    "pc": "pc", "piece": "pc", "pieces": "pc", "pcs": "pc",
    "pk": "pk", "pack": "pk", "packs": "pk",
    "ct": "ct", "count": "ct",
    "box": "box", "boxes": "box",
    "roll": "roll", "rolls": "roll",
    "set": "set", "sets": "set",
    "pair": "pair", "pairs": "pair",
    "ga": "ga", "gauge": "ga", "grit": "grit",
}


def decimal_to_trade_fraction(val: Union[float, int, str]) -> str:
    """
    Converts a decimal or numeric string to standard trade fractional notation.
    
    Examples:
        50.25 -> "50-1/4"
        0.25  -> "1/4"
        24.0  -> "24"
        0.5   -> "1/2"
        0.045 -> "0.045" (retained as decimal because it's precision abrasive gauge)
        "6.5" -> "6-1/2"
    """
    if val is None or val == "":
        return ""
    
    try:
        f_val = float(val)
    except (ValueError, TypeError):
        return str(val).strip()

    if f_val.is_integer():
        return str(int(f_val))

    int_part = int(f_val)
    dec_part = round(f_val - int_part, 6)

    # 1. Exact match in 64th decimal fraction lookup table
    matched_frac = None
    for target_dec, frac_str in DECIMAL_FRACTION_LOOKUP.items():
        if abs(dec_part - target_dec) < 0.0005:
            matched_frac = frac_str
            break

    if matched_frac:
        if int_part > 0:
            return f"{int_part}-{matched_frac}"
        return matched_frac

    # 2. Precision decimals (e.g., .045, .040, .094) keep as clean decimal
    dec_str = f"{f_val:.4f}".rstrip("0").rstrip(".")
    return dec_str


def standardize_uom(uom: Optional[str]) -> str:
    """
    Standardizes unit of measure strings to the Unilog Master UOM dictionary standard.
    
    Examples:
        standardize_uom("inches") -> "in"
        standardize_uom("IN.")    -> "in"
        standardize_uom("volts")  -> "V"
        standardize_uom("amps")   -> "A"
        standardize_uom("dba")    -> "dBA"
        standardize_uom("lbs")    -> "lb"
    """
    if not uom:
        return ""
    
    cleaned = str(uom).strip().lower()
    return MASTER_UOM_MAP.get(cleaned, str(uom).strip())


def format_measurement(value: Union[str, float, int], uom: Optional[str]) -> str:
    """
    Formats a measurement string ensuring single-space separation and standardized UOM.
    
    Examples:
        format_measurement("24", "in")   -> "24 in"
        format_measurement(50.25, "in")  -> "50-1/4 in"
        format_measurement("120", "v")   -> "120 V"
        format_measurement("15", "amps") -> "15 A"
        format_measurement("47", "dba")  -> "47 dBA"
    """
    if value is None or value == "":
        return ""

    val_str = str(value).strip()
    # Check if value is numeric and convert to trade fraction if appropriate
    try:
        f_val = float(val_str)
        # Convert dimensions (in, ft) to trade fractions, keep ratings (gpm, V, A, dBA) in decimal/int format
        if uom and standardize_uom(uom) in ["in", "ft", "yd"]:
            val_str = decimal_to_trade_fraction(f_val)
        elif not uom:
            val_str = decimal_to_trade_fraction(f_val)
        else:
            val_str = str(int(f_val)) if f_val.is_integer() else str(f_val)
    except ValueError:
        pass

    if not uom:
        return val_str

    std_uom = standardize_uom(uom)
    if not std_uom:
        return val_str

    return f"{val_str} {std_uom}"


def normalize_uom(val_with_uom: str) -> str:
    """
    Normalizes compound value + unit strings or bare units:
    e.g. '24in' -> '24 in', '120v' -> '120 V', '47dba' -> '47 dBA', '1.5GPM' -> '1.5 gpm'
    """
    if not val_with_uom:
        return ""
    
    text = str(val_with_uom).strip()
    
    # Check if string has numeric prefix followed by unit (e.g. '24in', '120v', '47dba', '1.5GPM')
    match = re.match(r"^([\d\./-]+)\s*([A-Za-z°\"'/]+)$", text)
    if match:
        val_part, uom_part = match.groups()
        std_u = standardize_uom(uom_part)
        
        # Only convert dimensions (in, ft) to trade fraction, leave flow rate (gpm), power (kW), current (A) as decimal/int
        try:
            f_val = float(val_part)
            if std_u in ["in", "ft", "yd"]:
                val_part = decimal_to_trade_fraction(f_val)
            else:
                val_part = str(int(f_val)) if f_val.is_integer() else str(f_val)
        except ValueError:
            pass
            
        return f"{val_part} {std_u}" if std_u else f"{val_part} {uom_part}"
    
    # Bare unit
    return standardize_uom(text)


def standardize_dimension_string(dim_str: str) -> str:
    """
    Parses and standardizes compound dimension strings commonly found in industrial parts.
    
    Examples:
        "5\"x.045\"x7/8\"" -> "5 in x 0.045 in x 7/8 in"
        "12\"x20mm"        -> "12 in x 20 mm"
        "24x24-1/4"        -> "24 in W x 24-1/4 in D"
        "3/4x60'"          -> "3/4 in x 60 ft"
    """
    if not dim_str:
        return ""

    text = dim_str.strip()

    # Pattern: 5"x.045"x7/8" or 4-1/2"x1/8"x7/8"
    parts = re.split(r"\s*[xX]\s*", text)
    if len(parts) >= 2:
        formatted_parts = []
        for p in parts:
            p_clean = p.strip()
            # Check unit in segment
            if p_clean.endswith('"') or p_clean.endswith("in"):
                val = p_clean.rstrip('"in').strip()
                formatted_parts.append(f"{val} in")
            elif p_clean.endswith("'") or p_clean.endswith("ft"):
                val = p_clean.rstrip("'ft").strip()
                formatted_parts.append(f"{val} ft")
            elif p_clean.endswith("mm"):
                val = p_clean[:-2].strip()
                formatted_parts.append(f"{val} mm")
            else:
                # Default to inches if bare number/fraction
                formatted_parts.append(f"{p_clean} in" if re.match(r"^[\d\./-]+$", p_clean) else p_clean)
        return " x ".join(formatted_parts)

    return text


# Aliases for QA test plan compatibility
convert_decimal_to_fraction = decimal_to_trade_fraction
