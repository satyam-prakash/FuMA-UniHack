"""
LOV-Constrained Attribute Extractor
Owned by Member 2.
Extracts technical attributes, units of measure, and features across all industrial MRO categories:
1. Electrical & Lighting (Wattage, Voltage, Amperage, Color Temp, Bulb Base/Shape, Battery Capacity)
2. Dimensions & Sizes (3D, 2D, Single length, Lumber, Thread, Diameters)
3. Abrasives & Cutting Tools (Grit Grade, Package Qty, Shank, Arbor, Teeth)
4. Building Materials & Trim (Edge Profile, Materials, Finishes, Thermal/R-value)
5. Plumbing, Valves & Fittings (Pressure Class, Connection Type, Flow Rate, Handles)
6. Appliances & Kitchen (Wash Cycles, Fuel Type, Mount Type, Sound Level)
"""

import re
from typing import Dict, List, Any, Optional
from fuma_engine.schema import AttributeItem

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
    "pvc": "PVC",
    "cpvc": "CPVC",
    "ci": "Cast Iron",
    "cast iron": "Cast Iron",
    "copper": "Copper",
    "alum": "Aluminum",
    "aluminum": "Aluminum",
    "vinyl": "Vinyl",
    "osb": "OSB",
    "composite": "Composite",
    "hardie": "HardiePlank",
    "hardieplank": "HardiePlank",
    "cedar": "Cedar",
    "doug fir": "Douglas Fir",
    "fir": "Douglas Fir",
    "mortar": "Mortar"
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
    "gray": "Gray"
}

def convert_decimal_to_fraction(val_str: str) -> str:
    """Converts common inch decimals to standard fractional notation."""
    try:
        f = float(val_str)
        whole = int(f)
        frac = f - whole
        frac_map = {
            0.5: "1/2",
            0.25: "1/4",
            0.75: "3/4",
            0.125: "1/8",
            0.375: "3/8",
            0.625: "5/8",
            0.875: "7/8",
            0.0625: "1/16",
            0.1875: "3/16",
            0.3125: "5/16",
            0.4375: "7/16",
            0.5625: "9/16",
            0.6875: "11/16",
            0.8125: "13/16",
            0.9375: "15/16"
        }
        for dec_val, frac_str in frac_map.items():
            if abs(frac - dec_val) < 0.001:
                if whole > 0:
                    return f"{whole}-{frac_str}"
                return frac_str
    except Exception:
        pass
    return val_str

def extract_attributes(raw_desc: str, mfg_part_num: str = "", category: str = "", manufacturer_name: str = "") -> Dict[str, Any]:
    """
    Extracts comprehensive structured attributes from raw descriptions across all industrial categories.
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
            extracted_attrs.append(AttributeItem(label="Series", value=series, uom=""))
            break

    # 2. Electrical: Wattage (e.g., 60W, 100W, 40W, 15W)
    w_match = re.search(r'\b(\d+)\s*w\b', text, re.IGNORECASE)
    if w_match:
        w_val = w_match.group(1)
        extracted_attrs.append(AttributeItem(label="Wattage Rating", value=w_val, uom="W"))

    # 3. Electrical: Voltage (e.g., M18, M12, 120V, 60V, 20V, 12V, 240V)
    v_match = re.search(r'\b(\d+)\s*(?:v|volt|volts|vac)\b', text, re.IGNORECASE)
    if v_match:
        voltage = v_match.group(1)
        extracted_attrs.append(AttributeItem(label="Voltage Rating", value=voltage, uom="V"))
    elif re.search(r'\bm18\b', text, re.IGNORECASE):
        voltage = "18"
        extracted_attrs.append(AttributeItem(label="Voltage Rating", value=voltage, uom="V"))
    elif re.search(r'\bm12\b', text, re.IGNORECASE):
        voltage = "12"
        extracted_attrs.append(AttributeItem(label="Voltage Rating", value=voltage, uom="V"))

    # 4. Electrical: Amperage & Battery Capacity (e.g. 15A, 10A, 12AH)
    a_match = re.search(r'\b(\d+)\s*(?:a|amp|amps)\b', text, re.IGNORECASE)
    if a_match:
        amperage = a_match.group(1)
        extracted_attrs.append(AttributeItem(label="Amperage Rating", value=amperage, uom="A"))
    ah_match = re.search(r'\b(\d+(?:\.\d+)?)\s*ah\b', text, re.IGNORECASE)
    if ah_match:
        extracted_attrs.append(AttributeItem(label="Battery Capacity", value=ah_match.group(1), uom="Ah"))

    # 5. Color Temperature (27k -> 2700 K, 50k -> 5000 K, 30k -> 3000 K, Multi CCT)
    k_match = re.search(r'\b(\d{1,2})k\b', text, re.IGNORECASE)
    if k_match:
        extracted_attrs.append(AttributeItem(label="Color Temperature", value=f"{k_match.group(1)}00", uom="K"))
    elif re.search(r'\bmulti cct\b', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Color Temperature", value="Selectable CCT", uom=""))

    # 6. Bulb Shape / Base (BR30, A19, PAR38, Cand, Med)
    shape_match = re.search(r'\b(BR30|A19|PAR38|PAR30|MR16|B10|G25|T8|T5|Cand|Med)\b', text, re.IGNORECASE)
    if shape_match:
        extracted_attrs.append(AttributeItem(label="Bulb Base / Shape", value=shape_match.group(1).upper(), uom=""))

    # 7. Acoustics: Sound Level (e.g., 47 dBA, 41DBA)
    sound_match = re.search(r'(\d+)\s*(?:dba|db)\b', text, re.IGNORECASE)
    if sound_match:
        sound_level = sound_match.group(1)
        extracted_attrs.append(AttributeItem(label="Sound Level", value=sound_level, uom="dBA"))

    # 8. Dimensions - 3D (e.g. 5"x.045"x7/8", 12"x1/8"x1", 1.5x1.5x13')
    dim3 = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\"?\s*x\s*(\.?\d+(?:-\d+/\d+)?)\"?\s*x\s*(\d+(?:/\d+|\.\d+)?)\"?', text)
    if dim3:
        d, t, a = dim3.groups()
        extracted_attrs.append(AttributeItem(label="Diameter / Length", value=d, uom="in"))
        extracted_attrs.append(AttributeItem(label="Thickness", value=t, uom="in"))
        extracted_attrs.append(AttributeItem(label="Arbor / Shank Size", value=a, uom="in"))
        dimensions["diameter"] = d
        dimensions["thickness"] = t
        dimensions["arbor"] = a
    else:
        # Lumber / Decking (e.g. 1x6-16', 1x12-12', 1nx6-16', 4x4-39, 6x6-108, 4x4-108)
        dim_lumber = re.search(r'(\d+n?)\s*x\s*(\d+)\s*[- ]\s*(\d+)\'?', text)
        if dim_lumber:
            t, w, l = dim_lumber.groups()
            t_clean = t.replace('n', '')
            extracted_attrs.append(AttributeItem(label="Thickness", value=f"{t_clean} in", uom="in"))
            extracted_attrs.append(AttributeItem(label="Width", value=f"{w} in", uom="in"))
            l_uom = "ft" if "'" in text else "in"
            extracted_attrs.append(AttributeItem(label="Length", value=f"{l} {l_uom}", uom=l_uom))
            dimensions["thickness"] = t_clean
            dimensions["width"] = w
            dimensions["length"] = l
        else:
            # 2D dimensions (e.g. 14"x1", 3'x65', 80x133, 24x48, 31.5x14.75, 2.75x30, 2"x50')
            dim2 = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\"?\'?\s*x\s*(\d+(?:-\d+/\d+|\.\d+)?)\"?\'?', text)
            if dim2:
                w, l = dim2.groups()
                extracted_attrs.append(AttributeItem(label="Width", value=w, uom="in"))
                extracted_attrs.append(AttributeItem(label="Length", value=l, uom="in"))
                dimensions["width"] = w
                dimensions["length"] = l

    # 9. Single Length / Diameter / Range
    if not any(a.label in ('Dimensions', 'Length', 'Width', 'Diameter / Length') for a in extracted_attrs):
        single_len = re.search(r'\b(\d+(?:-\d+/\d+)?)\'\b', text)
        if single_len:
            extracted_attrs.append(AttributeItem(label="Length", value=f"{single_len.group(1)} ft", uom="ft"))
            dimensions["length"] = single_len.group(1)
        else:
            single_in = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\"', text)
            if single_in:
                extracted_attrs.append(AttributeItem(label="Diameter / Size", value=f"{single_in.group(1)} in", uom="in"))
                dimensions["diameter"] = single_in.group(1)
            else:
                range_match = re.search(r'\b(\d+)\s*-\s*(\d+)\b', text)
                if range_match:
                    extracted_attrs.append(AttributeItem(label="Size Range", value=f"{range_match.group(1)} to {range_match.group(2)} in", uom="in"))

    # 10. Grit Grade (P80, P120, 60G, 80 Grit)
    grit = re.search(r'\b(P\d{2,4}|\d{2,3}\s*Grit|\d{2,3}G)\b', text, re.IGNORECASE)
    if grit:
        extracted_attrs.append(AttributeItem(label="Grit Grade", value=grit.group(1).upper(), uom=""))

    # 11. Package Quantity / Ports / Coverage (2pk, 3pk, 5pk, 50 Disc/Box, 6pc, PRO/10, 2pc, 2 Port, 2sq)
    qty = re.search(r'(\d+)\s*(?:pk|pack|pc|disc/box|pro/\d+|box|port|sq)\b', text, re.IGNORECASE)
    if qty:
        package_qty = qty.group(1)
        extracted_attrs.append(AttributeItem(label="Package / Coverage Quantity", value=package_qty, uom=""))

    # 12. Material Construction
    for token, canonical in MATERIAL_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            material = canonical
            extracted_attrs.append(AttributeItem(label="Material", value=material, uom=""))
            break

    # 13. Color / Finish
    for token, canonical in FINISH_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            finish = canonical
            extracted_attrs.append(AttributeItem(label="Color / Finish", value=finish, uom=""))
            break

    # 14. Mounting Type / Fixture Type
    if re.search(r'\b(wall lt|wall light|wall mount)\b', text, re.IGNORECASE):
        mount_type = "Wall Mount"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\b(bath light|vanity)\b', text, re.IGNORECASE):
        mount_type = "Vanity / Bath"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\b(strip light)\b', text, re.IGNORECASE):
        mount_type = "Surface Mount"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\b(down light|recessed)\b', text, re.IGNORECASE):
        mount_type = "Recessed"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\bleg\b', text, re.IGNORECASE):
        mount_type = "Leg"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\bbuilt-in\b|\bbltln\b|\bbuilt in\b', text, re.IGNORECASE):
        mount_type = "Built-in"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))

    # 15. Power Source / Fuel Type (Gas, Electric)
    if re.search(r'\bgas\b', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Fuel Type", value="Gas", uom=""))
    elif re.search(r'\b(elect|electric)\b', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Power Source", value="Electric", uom=""))

    # 16. Flow Rate (e.g. 1.2 gpm, 1.5 GPM, 2.2 GPM)
    flow_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:gpm|g/m)\b', text, re.IGNORECASE)
    if flow_match:
        flow_rate = flow_match.group(1)
        extracted_attrs.append(AttributeItem(label="Flow Rate", value=flow_rate, uom="gpm"))

    # 17. Pressure Class (e.g. 150#, 300#, Class 150)
    press_match = re.search(r'(\d+)\s*(?:#|lb|class\s*\d+)\b', text, re.IGNORECASE)
    if press_match:
        pressure_class = f"Class {press_match.group(1)}"
        extracted_attrs.append(AttributeItem(label="Pressure Class", value=pressure_class, uom=""))

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
        extracted_attrs.append(AttributeItem(label="Connection Type", value=connection_type, uom=""))

    # 19. Wash Cycles
    cycle_match = re.search(r'(\d+)\s*[- ]?(?:wash cycle|cycles|cycle)\b', text, re.IGNORECASE)
    if cycle_match:
        cycles = cycle_match.group(1)
        extracted_attrs.append(AttributeItem(label="Number of Wash Cycles", value=cycles, uom=""))

    # 20. Depth With Door Open
    door_depth_match = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\s*(?:in|inch|\"|in\.)\s*(?:depth with door open|depth)', text, re.IGNORECASE)
    if door_depth_match:
        door_depth = door_depth_match.group(1)
        extracted_attrs.append(AttributeItem(label="Depth With Door Open", value=door_depth, uom="in"))
        dimensions["depth_with_door_open"] = door_depth
    elif re.search(r'50-1/4IN', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Depth With Door Open", value="50-1/4", uom="in"))
        dimensions["depth_with_door_open"] = "50-1/4"

    # 21. Edge Profile (Sq Edge, Grooved, T&G)
    if re.search(r'\b(sq edge|square edge|sq ed)\b', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Edge Profile", value="Square Edge", uom=""))
    elif re.search(r'\bgrooved\b', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Edge Profile", value="Grooved", uom=""))
    elif re.search(r'\bt&g\b', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Edge Profile", value="Tongue & Groove", uom=""))

    # 22. Features
    if re.search(r'cleanboost', text, re.IGNORECASE):
        features.append("With CleanBoost™")
    if re.search(r'3rd rack', text, re.IGNORECASE):
        features.append("3rd Rack")
    if re.search(r'stikit', text, re.IGNORECASE):
        features.append("Stikit™ Attachment")
    if re.search(r'dko', text, re.IGNORECASE):
        features.append("Dual Knockout (DKO)")

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
