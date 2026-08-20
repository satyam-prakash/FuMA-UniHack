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
    
    mat = "SST" if "Stainless" in extracted.get("material", "") else ("BRS" if "Brass" in extracted.get("material", "") else "")
    volt = f"{extracted.get('voltage')}V" if extracted.get("voltage") else ""
    amp = f"{extracted.get('amperage')}A" if extracted.get("amperage") else ""
    sound = f"{extracted.get('sound_level')}DBA" if extracted.get("sound_level") else ""
    
    dims = extracted.get("dimensions", {})
    size_str = ""
    if "depth_with_door_open" in dims:
        size_str = f"{dims['depth_with_door_open']}IN".replace(" ", "")
    elif "diameter" in dims and "thickness" in dims and "arbor" in dims:
        size_str = f"{dims['diameter']}X{dims['thickness']}X{dims['arbor']}".replace('"', '')
    elif "diameter" in dims:
        size_str = f"{dims['diameter']}IN"
    elif "width" in dims and "length" in dims:
        size_str = f"{dims['width']}X{dims['length']}".replace('"', '')

    grit = ""
    cycles = ""
    for attr in extracted.get("attributes", []):
        if attr.label == "Number of Wash Cycles":
            cycles = attr.value
        elif attr.label == "Grit Grade":
            grit = attr.value

    # Build sequence of tokens
    tokens = [product_name]
    if mount: tokens.append(mount)
    if cycles: tokens.append(cycles)
    if mat: tokens.append(mat)
    if grit: tokens.append(grit)
    if volt: tokens.append(volt)
    if amp: tokens.append(amp)
    if sound: tokens.append(sound)
    if size_str: tokens.append(size_str)
    
    invoice = " ".join([t for t in tokens if t]).upper()
    
    # Strict 40 character limit enforcement
    if len(invoice) > 40:
        invoice = invoice[:40].rstrip()
        
    return invoice

def build_mobile_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds the MOBILE_DESC targeting 60-80 characters in structured comma format:
    [Mfg] [Brand], [Type], [Series], [MPN], [Mounting/Specs]
    """
    mfg = item.get("manufacturer_name", "").strip()
    brand = item.get("brand_name", "").replace("®", "").replace("™", "").strip()
    prod_type = item.get("product_name", "Product").strip()
    series = extracted.get("series", "").replace("™", "").strip()
    mpn = item.get("mfg_part_num", "").strip()
    mount = f"{extracted.get('mount_type')} Mounting" if extracted.get("mount_type") else ""
    mat = extracted.get("material", "")
    
    parts = []
    if mfg and brand and mfg != brand:
        parts.append(f"{mfg} {brand}")
    elif brand:
        parts.append(brand)
    elif mfg:
        parts.append(mfg)
        
    if prod_type: parts.append(prod_type)
    if series: parts.append(series)
    if mpn: parts.append(mpn)
    if mount: parts.append(mount)
    elif mat: parts.append(mat)
    
    mobile = ", ".join([p for p in parts if p])
    
    # Trim to fit 80 chars max
    if len(mobile) > 80 and len(parts) > 3:
        mobile = ", ".join(parts[:-1])
        
    return mobile

def build_short_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds the SHORT_DESC / Product Title using standard Unilog Formulas:
    - Appliance: [Brand®] [Series] [MPN] [Type] [With Feature], [Mounting], [Specs]
    - Abrasive: [Brand®] [Series] [MPN] [Size] [Type], [Grit]
    - Fitting: [Brand®] [Size] [Connection] [Material] [Fitting Type], [Class]
    - Faucet: [Brand®] [Series] [MPN] [Type], [Mounting], [Flow], [Finish]
    """
    brand = item.get("brand_name", "").strip()
    series = extracted.get("series", "").strip()
    mpn = item.get("mfg_part_num", "").strip()
    prod_type = item.get("product_name", "").strip()
    
    dims = extracted.get("dimensions", {})
    features = extracted.get("features", [])
    feature_str = f" {features[0]}" if features else ""
    
    # 1. Abrasives formula
    if prod_type in ["Cut-Off Disc", "Sanding Disc", "Sanding Belt"]:
        size_part = ""
        if "diameter" in dims and "thickness" in dims and "arbor" in dims:
            size_part = f"{dims['diameter']} in x {dims['thickness']} in x {dims['arbor']} in"
        elif "width" in dims and "length" in dims:
            size_part = f"{dims['width']} in x {dims['length']} in"
        elif "diameter" in dims:
            size_part = f"{dims['diameter']} in"
            
        components = [brand, series, mpn, size_part, prod_type]
        title = " ".join([c for c in components if c]).strip()
        
        extra = []
        for attr in extracted.get("attributes", []):
            if attr.label == "Grit Grade":
                extra.append(f"{attr.value} Grit")
            elif attr.label == "Package Quantity":
                extra.append(f"{attr.value} Pack")
        if extra:
            return f"{title}, {', '.join(extra)}"
        return title

    # 2. Pipe Fittings formula
    if prod_type == "Pipe Fitting":
        conn = extracted.get("connection_type", "")
        mat = extracted.get("material", "")
        press = extracted.get("pressure_class", "")
        size = dims.get("width", "") or dims.get("diameter", "")
        
        components = [brand, size, conn, mat, prod_type]
        title = " ".join([c for c in components if c]).strip()
        if press:
            return f"{title}, {press}"
        return title

    # 3. Standard Appliance / Faucet formula
    prefix = f"{brand} {series} {mpn} {prod_type}{feature_str}".replace("  ", " ").strip()
    
    spec_parts = []
    if extracted.get("mount_type"):
        spec_parts.append(f"{extracted['mount_type']} Mounting")
        
    for attr in extracted.get("attributes", []):
        if attr.label == "Number of Wash Cycles":
            spec_parts.append(f"{attr.value}-Wash Cycle")
        elif attr.label == "Flow Rate":
            spec_parts.append(f"{attr.value} gpm")
            
    if extracted.get("finish"):
        spec_parts.append(extracted["finish"])
    elif extracted.get("material"):
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
        elif attr.uom and not attr.value.endswith(attr.uom):
            spec_list.append(f"{attr.value} {attr.uom}")
        elif attr.label not in ["Series", "Material", "Finish"]:
            spec_list.append(f"{attr.value}")
            
    if extracted.get("finish"):
        spec_list.append(extracted["finish"])
    elif extracted.get("material"):
        spec_list.append(extracted["material"])
        
    return f"{intro}, " + ", ".join(spec_list)

def build_retail_desc(item: Dict[str, Any], extracted: Dict[str, Any]) -> str:
    """
    Builds consumer-friendly RETAIL_DESC.
    """
    series = extracted.get("series", "").strip()
    prod_type = item.get("product_name", "").strip()
    mount = f"{extracted.get('mount_type')} Mounting" if extracted.get("mount_type") else ""
    mat = extracted.get("finish", "") or extracted.get("material", "")
    
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
