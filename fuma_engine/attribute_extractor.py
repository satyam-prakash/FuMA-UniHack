"""
LOV-Constrained Attribute Extractor
Owned by Member 2.
Extracts technical attributes, units of measure, and features from raw descriptions across:
1. Dishwashers & Large Appliances
2. Kitchen & Bath Sink Faucets
3. Pipe, Tube & Hose Fittings
4. Abrasives (Cut-Off Wheels, Sanding Discs & Belts)
"""

import re
from typing import Dict, List, Any, Optional
from fuma_engine.schema import AttributeItem

# Material mapping to canonical names
MATERIAL_MAP = {
    "ss": "Stainless Steel",
    "sst": "Stainless Steel",
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
    "aluminum": "Aluminum"
}

# Faucet finish mapping
FINISH_MAP = {
    "chrome": "Chrome Plated",
    "cp": "Chrome Plated",
    "brushed nickel": "Brushed Nickel",
    "bn": "Brushed Nickel",
    "matte black": "Matte Black",
    "mb": "Matte Black",
    "oil rubbed bronze": "Oil Rubbed Bronze",
    "orb": "Oil Rubbed Bronze",
    "stainless": "Stainless Steel"
}

def extract_attributes(raw_desc: str, mfg_part_num: str = "", category: str = "") -> Dict[str, Any]:
    """
    Extracts structured attributes from raw descriptions across multiple categories.
    """
    text = raw_desc
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
    dimensions = {}
    
    # 1. Detect Series
    if re.search(r'\bprofessional\b', text, re.IGNORECASE):
        series = "Professional Series"
    elif re.search(r'\beco\b', text, re.IGNORECASE):
        series = "Eco Series"
    elif re.search(r'\bsteel demon\b', text, re.IGNORECASE):
        series = "Steel Demon"
    elif re.search(r'\bspeed demon\b', text, re.IGNORECASE):
        series = "Speed Demon"
    elif re.search(r'\bcubitron ii\b|\bcubitron 2\b', text, re.IGNORECASE):
        series = "Cubitron™ II"
    elif re.search(r'\babranet\b', text, re.IGNORECASE):
        series = "Abranet"
    elif re.search(r'\bhiolit\b', text, re.IGNORECASE):
        series = "Hiolit"
        
    if series:
        extracted_attrs.append(AttributeItem(label="Series", value=series, uom=""))

    # 2. Electrical: Voltage (e.g., 120V, 120 V, 240V)
    volt_match = re.search(r'(\d+)\s*(?:v|volt|volts|vac)\b', text, re.IGNORECASE)
    if volt_match:
        voltage = volt_match.group(1)
        extracted_attrs.append(AttributeItem(label="Voltage Rating", value=voltage, uom="V"))

    # 3. Electrical: Amperage (e.g., 15A, 10 A)
    amp_match = re.search(r'(\d+)\s*(?:a|amp|amps)\b', text, re.IGNORECASE)
    if amp_match:
        amperage = amp_match.group(1)
        extracted_attrs.append(AttributeItem(label="Amperage Rating", value=amperage, uom="A"))

    # 4. Acoustics: Sound Level (e.g., 47 dBA, 41DBA)
    sound_match = re.search(r'(\d+)\s*(?:dba|db)\b', text, re.IGNORECASE)
    if sound_match:
        sound_level = sound_match.group(1)
        extracted_attrs.append(AttributeItem(label="Sound Level", value=sound_level, uom="dBA"))

    # 5. Mounting Type (e.g., Leg Mounting, Built-In, Deck Mount, Wall Mount)
    if re.search(r'\bleg\b', text, re.IGNORECASE):
        mount_type = "Leg"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\bbuilt-in\b|\bbltln\b|\bbuilt in\b', text, re.IGNORECASE):
        mount_type = "Built-in"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\bdeck mount\b|\bdeck\b', text, re.IGNORECASE):
        mount_type = "Deck Mount"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\bwall mount\b', text, re.IGNORECASE):
        mount_type = "Wall Mount"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))

    # 6. Material (e.g., SS, SST, Brass, PVC)
    for token, canonical in MATERIAL_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            material = canonical
            extracted_attrs.append(AttributeItem(label="Material", value=material, uom=""))
            break

    # 7. Finish (e.g. Chrome, Brushed Nickel)
    for token, canonical in FINISH_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            finish = canonical
            extracted_attrs.append(AttributeItem(label="Finish", value=finish, uom=""))
            break

    # 8. Flow Rate (e.g. 1.2 gpm, 1.5 GPM, 2.2 GPM)
    flow_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:gpm|g/m)\b', text, re.IGNORECASE)
    if flow_match:
        flow_rate = flow_match.group(1)
        extracted_attrs.append(AttributeItem(label="Flow Rate", value=flow_rate, uom="gpm"))

    # 9. Pressure Class (e.g. 150#, 300#, Class 150)
    press_match = re.search(r'(\d+)\s*(?:#|lb|class\s*\d+)\b', text, re.IGNORECASE)
    if press_match:
        pressure_class = f"Class {press_match.group(1)}"
        extracted_attrs.append(AttributeItem(label="Pressure Class", value=pressure_class, uom=""))

    # 10. Connection Type (e.g. FNPT x MNPT, NPT, Push-Fit, Flanged)
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

    # 11. Wash Cycles (e.g., 5-Wash Cycle)
    cycle_match = re.search(r'(\d+)\s*[- ]?(?:wash cycle|cycles|cycle)\b', text, re.IGNORECASE)
    if cycle_match:
        cycles = cycle_match.group(1)
        extracted_attrs.append(AttributeItem(label="Number of Wash Cycles", value=cycles, uom=""))

    # 12. Dimensions & Depth With Door Open
    door_depth_match = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\s*(?:in|inch|\"|in\.)\s*(?:depth with door open|depth)', text, re.IGNORECASE)
    if door_depth_match:
        door_depth = door_depth_match.group(1)
        extracted_attrs.append(AttributeItem(label="Depth With Door Open", value=door_depth, uom="in"))
        dimensions["depth_with_door_open"] = door_depth
    elif re.search(r'50-1/4IN', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Depth With Door Open", value="50-1/4", uom="in"))
        dimensions["depth_with_door_open"] = "50-1/4"

    # 13. Abrasives Dimensions (e.g., 5"x.045"x7/8", 12"x1/8"x1", 1/2"x18", 2.75x30)
    dim_3_match = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\"?\s*x\s*(\.?\d+(?:-\d+/\d+)?)\"?\s*x\s*(\d+(?:/\d+)?)\"?', text)
    if dim_3_match:
        diameter, thickness, arbor = dim_3_match.groups()
        extracted_attrs.append(AttributeItem(label="Wheel Diameter", value=f"{diameter} in", uom="in"))
        extracted_attrs.append(AttributeItem(label="Thickness", value=f"{thickness} in", uom="in"))
        extracted_attrs.append(AttributeItem(label="Arbor Size", value=f"{arbor} in", uom="in"))
        dimensions["diameter"] = diameter
        dimensions["thickness"] = thickness
        dimensions["arbor"] = arbor
    else:
        # 2-Dimension check (e.g. 1/2"x18", 2.75x30)
        dim_2_match = re.search(r'(\d+(?:/\d+|\.\d+)?)\"?\s*x\s*(\d+(?:/\d+|\.\d+)?)\"?', text)
        if dim_2_match:
            w, l = dim_2_match.groups()
            extracted_attrs.append(AttributeItem(label="Width", value=f"{w} in", uom="in"))
            extracted_attrs.append(AttributeItem(label="Length", value=f"{l} in", uom="in"))
            dimensions["width"] = w
            dimensions["length"] = l

    # 14. Single diameter check (e.g., 5", 9", 12")
    if "diameter" not in dimensions and "width" not in dimensions:
        single_diam = re.search(r'\b(\d+(?:-\d+/\d+)?)\"\s*(?:metal cut|cut-off|cut off|hiolit|sanding)', text, re.IGNORECASE)
        if single_diam:
            diam = single_diam.group(1)
            extracted_attrs.append(AttributeItem(label="Wheel Diameter", value=f"{diam} in", uom="in"))
            dimensions["diameter"] = diam

    # 15. Grit (e.g., P80, P120, P150, P180, P220, P320)
    grit_match = re.search(r'\b(P\d{2,4})\b', text, re.IGNORECASE)
    if grit_match:
        grit = grit_match.group(1).upper()
        extracted_attrs.append(AttributeItem(label="Grit Grade", value=grit, uom=""))

    # 16. Package / Quantity (e.g. 6pc, 50 Disc/Box, 10/Pack)
    qty_match = re.search(r'(\d+)\s*(?:pc|disc/box|pk|pack|box)\b', text, re.IGNORECASE)
    if qty_match:
        package_qty = qty_match.group(1)
        extracted_attrs.append(AttributeItem(label="Package Quantity", value=package_qty, uom=""))

    # 17. Features
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
