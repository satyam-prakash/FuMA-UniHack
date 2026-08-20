"""
Data Sanitization & Cleaning Module for Industrial Product Catalog Enrichment.
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
Package: fuma_rules
"""

import re
from typing import Optional, Any

# Standard placeholder values to strip out
PLACEHOLDER_TOKENS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "-- no brand --",
    "-- none --",
    "-- unassigned --",
    "unbranded",
    "no brand",
    "n/a",
    "na",
    "null",
    "none",
    "-",
    "--",
    "nan",
    "",
}

# Regex to detect and strip supplier account/vendor codes in parentheses
# e.g., 'Freud Inc (2435)' -> 'Freud Inc', '3 M Co (5293)' -> '3 M Co', 'Appliance Dealers Cooperative (APPDE)' -> 'Appliance Dealers Cooperative'
SUPPLIER_CODE_REGEX = re.compile(r"\s*\([A-Za-z0-9_\-]+\)\s*$", re.IGNORECASE)

# Regex to detect noisy catalog suffixes in part descriptions
NOISY_SUFFIX_REGEX = re.compile(
    r"\s*-\s*(Display Only|Discontinued|Sample Only|Refurbished|Promo)\s*$",
    re.IGNORECASE,
)


def clean_placeholder(val: Any) -> Optional[str]:
    """
    Returns None if the value is a placeholder, blank, or NaN; otherwise returns trimmed string.
    
    Examples:
        clean_placeholder("-- Unbranded --") -> None
        clean_placeholder("-- No Unilog Brand --") -> None
        clean_placeholder("Freud Inc") -> "Freud Inc"
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in PLACEHOLDER_TOKENS:
        return None
    return val_str


def clean_supplier_name(raw_mfg: Any) -> Optional[str]:
    """
    Cleans supplier/manufacturer strings by removing internal account/vendor codes.
    
    Examples:
        clean_supplier_name("Freud Inc (2435)") -> "Freud Inc"
        clean_supplier_name("Jam Industrial Supply LLC (JAMIN)") -> "Jam Industrial Supply LLC"
        clean_supplier_name("Milwaukee Accessory (4031)") -> "Milwaukee Accessory"
        clean_supplier_name("-- Unbranded --") -> None
    """
    val = clean_placeholder(raw_mfg)
    if not val:
        return None
    
    # Strip supplier code in trailing parentheses
    cleaned = SUPPLIER_CODE_REGEX.sub("", val).strip()
    return cleaned if cleaned else None


def clean_part_description(raw_desc: Any) -> str:
    """
    Cleans part description strings:
    - Normalizes double quotes and smart quotes
    - Strips noisy suffixes like '- Display Only'
    - Normalizes multiple spaces
    
    Examples:
        clean_part_description('PDSH4816AF Dishwasher SS - Display Only')
            -> 'PDSH4816AF Dishwasher SS'
        clean_part_description('49-94-0013 Milw 5""x.045""x7/8"" Metal Cut Off Disc')
            -> '49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc'
    """
    if raw_desc is None:
        return ""
    
    desc = str(raw_desc).strip()
    if not desc or desc.lower() in PLACEHOLDER_TOKENS:
        return ""
    
    # Normalize smart quotes and escaped double quotes
    desc = desc.replace('""', '"').replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    
    # Remove noisy catalog suffixes like '- Display Only'
    desc = NOISY_SUFFIX_REGEX.sub("", desc).strip()
    
    # Normalize multiple whitespace into single space
    desc = re.sub(r"[ \t]+", " ", desc)
    
    return desc
