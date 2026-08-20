"""
Multi-Channel Description Formula Generator
Owned by Member 2.
Generates the 5 mandatory description formats:
1. INVOICE_DESC (<= 40 chars, ALL CAPS)
2. MOBILE_DESC (60-80 chars)
3. SHORT_DESC (Product Title formula)
4. LONG_DESC1 (Comprehensive technical spec chain)
5. RETAIL_DESC (Consumer-friendly marketing copy)
"""

from typing import Dict, Any, List

def build_invoice_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds the INVOICE_DESC adhering to:
    - Maximum 40 characters
    - 100% ALL UPPERCASE
    - Concise industrial abbreviations
    """
    product_name = item.get("product_name", "PART").upper()
    mount = extracted.get("mount_type", "").upper()
    if mount == "BUILT-IN":
        mount = "BLTLN"
    
    mat = "SST" if "Stainless" in extracted.get("material", "") else ""
    volt = f"{extracted.get('voltage')}V" if extracted.get("voltage") else ""
    amp = f"{extracted.get('amperage')}A" if extracted.get("amperage") else ""
    sound = f"{extracted.get('sound_level')}DBA" if extracted.get("sound_level") else ""
    depth = extracted.get("dimensions", {}).get("depth_with_door_open", "")
    if depth:
        depth = f"{depth}IN".replace(" ", "")
        
    cycles = ""
    for attr in extracted.get("attributes", []):
        if attr.label == "Number of Wash Cycles":
            cycles = attr.value
            break

    # Build sequence of tokens
    tokens = [product_name]
    if mount: tokens.append(mount)
    if cycles: tokens.append(cycles)
    if mat: tokens.append(mat)
    if volt: tokens.append(volt)
    if amp: tokens.append(amp)
    if sound: tokens.append(sound)
    if depth: tokens.append(depth)
    
    invoice = " ".join([t for t in tokens if t]).upper()
    
    # Strict 40 character limit enforcement
    if len(invoice) > 40:
        invoice = invoice[:40].rstrip()
        
    return invoice

def build_mobile_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds the MOBILE_DESC targeting 60-80 characters in structured comma format:
    [Mfg] [Brand], [Type], [Series], [MPN], [Mounting]
    """
    mfg = item.get("manufacturer_name", "").strip()
    brand = item.get("brand_name", "").replace("®", "").replace("™", "").strip()
    prod_type = item.get("product_name", "Product").strip()
    series = extracted.get("series", "").strip()
    mpn = item.get("mfg_part_num", "").strip()
    mount = f"{extracted.get('mount_type')} Mounting" if extracted.get("mount_type") else ""
    
    parts = []
    if mfg and brand:
        parts.append(f"{mfg} {brand}")
    elif brand:
        parts.append(brand)
    elif mfg:
        parts.append(mfg)
        
    if prod_type: parts.append(prod_type)
    if series: parts.append(series)
    if mpn: parts.append(mpn)
    if mount: parts.append(mount)
    
    mobile = ", ".join([p for p in parts if p])
    
    # If over 80 chars, trim the last token
    if len(mobile) > 80 and len(parts) > 3:
        mobile = ", ".join(parts[:-1])
        
    return mobile

def build_short_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds the SHORT_DESC / Product Title using the standard Unilog Formula:
    [Brand®] + [Series] + [MPN] + [Item Type] + [With Feature], [Mounting], [Key Specs]
    """
    brand = item.get("brand_name", "").strip()
    series = extracted.get("series", "").strip()
    mpn = item.get("mfg_part_num", "").strip()
    prod_type = item.get("product_name", "").strip()
    
    features = extracted.get("features", [])
    feature_str = f" {features[0]}" if features else ""
    
    prefix = f"{brand} {series} {mpn} {prod_type}{feature_str}".replace("  ", " ").strip()
    
    spec_parts = []
    if extracted.get("mount_type"):
        spec_parts.append(f"{extracted['mount_type']} Mounting")
        
    for attr in extracted.get("attributes", []):
        if attr.label == "Number of Wash Cycles":
            spec_parts.append(f"{attr.value}-Wash Cycle")
            
    if extracted.get("material"):
        spec_parts.append(extracted["material"])
        
    specs_str = ", ".join(spec_parts)
    if specs_str:
        return f"{prefix}, {specs_str}"
    return prefix

def build_long_desc1(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds the LONG_DESC1 containing full technical specs listed in canonical sequence with UOMs.
    """
    brand = item.get("brand_name", "").strip()
    prod_type = item.get("product_name", "").strip()
    features = extracted.get("features", [])
    feature_str = f" {features[0]}" if features else ""
    
    intro = f"{brand} {prod_type}{feature_str}".strip()
    
    spec_list = []
    if extracted.get("series"):
        spec_list.append(extracted["series"])
        
    for attr in extracted.get("attributes", []):
        if attr.label == "Number of Wash Cycles":
            spec_list.append(f"{attr.value} Wash Cycles")
        elif attr.uom:
            spec_list.append(f"{attr.value} {attr.uom}")
        elif attr.label not in ["Series", "Material"]:
            spec_list.append(f"{attr.value}")
            
    if extracted.get("material"):
        spec_list.append(extracted["material"])
        
    return f"{intro}, " + ", ".join(spec_list)

def build_retail_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds consumer-friendly RETAIL_DESC.
    """
    series = extracted.get("series", "").strip()
    prod_type = item.get("product_name", "").strip()
    mount = f"{extracted.get('mount_type')} Mounting" if extracted.get("mount_type") else ""
    mat = extracted.get("material", "")
    
    parts = [f"{series} {prod_type}".strip()]
    if mount: parts.append(mount)
    if mat: parts.append(mat)
    
    return ", ".join([p for p in parts if p])

def build_all_descriptions(item: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, str]:
    """
    Builds all 5 multichannel descriptions for an item.
    """
    return {
        "invoice_desc": build_invoice_desc(item, extracted),
        "mobile_desc": build_mobile_desc(item, extracted),
        "short_desc": build_short_desc(item, extracted),
        "long_desc1": build_long_desc1(item, extracted),
        "retail_desc": build_retail_desc(item, extracted)
    }
