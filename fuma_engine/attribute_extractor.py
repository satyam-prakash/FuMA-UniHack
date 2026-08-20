"""
LOV-Constrained Attribute Extractor
Owned by Member 2.
Extracts technical attributes, units of measure, and features from raw descriptions.
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
    "copper": "Copper"
}

def extract_attributes(raw_desc: str, mfg_part_num: str = "", category: str = "") -> Dict[str, Any]:
    """
    Extracts structured attributes from raw descriptions.
    
    Returns a dict containing:
        - "attributes": List[AttributeItem]
        - "features": List[str]
        - "series": str
        - "mount_type": str
        - "material": str
        - "voltage": str
        - "amperage": str
        - "sound_level": str
        - "dimensions": Dict[str, str]
    """
    text = raw_desc
    extracted_attrs: List[AttributeItem] = []
    features: List[str] = []
    
    series = ""
    mount_type = ""
    material = ""
    voltage = ""
    amperage = ""
    sound_level = ""
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
        
    if series:
        extracted_attrs.append(AttributeItem(label="Series", value=series, uom=""))

    # 2. Electrical: Voltage (e.g., 120V, 120 V, 240V)
    volt_match = re.search(r'(\d+)\s*(?:v|volt|volts|vac)\b', text, re.IGNORECASE)
    if volt_match:
        voltage = volt_match.group(1)
        extracted_attrs.append(AttributeItem(label="Voltage Rating", value=voltage, uom="V"))

    # 3. Electrical: Amperage (e.g., 15A, 10 A, 15 amp)
    amp_match = re.search(r'(\d+)\s*(?:a|amp|amps)\b', text, re.IGNORECASE)
    if amp_match:
        amperage = amp_match.group(1)
        extracted_attrs.append(AttributeItem(label="Amperage Rating", value=amperage, uom="A"))

    # 4. Acoustics: Sound Level (e.g., 47 dBA, 41DBA)
    sound_match = re.search(r'(\d+)\s*(?:dba|db)\b', text, re.IGNORECASE)
    if sound_match:
        sound_level = sound_match.group(1)
        extracted_attrs.append(AttributeItem(label="Sound Level", value=sound_level, uom="dBA"))

    # 5. Mounting Type (e.g., Leg Mounting, Built-In)
    if re.search(r'\bleg\b', text, re.IGNORECASE):
        mount_type = "Leg"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))
    elif re.search(r'\bbuilt-in\b|\bbltln\b|\bbuilt in\b', text, re.IGNORECASE):
        mount_type = "Built-in"
        extracted_attrs.append(AttributeItem(label="Mounting Type", value=mount_type, uom=""))

    # 6. Material (e.g., SS, SST, Stainless Steel, Brass)
    for token, canonical in MATERIAL_MAP.items():
        if re.search(r'\b' + re.escape(token) + r'\b', text, re.IGNORECASE):
            material = canonical
            extracted_attrs.append(AttributeItem(label="Material", value=material, uom=""))
            break

    # 7. Wash Cycles (e.g., 5-Wash Cycle, 5 Wash Cycles, 5)
    cycle_match = re.search(r'(\d+)\s*[- ]?(?:wash cycle|cycles|cycle)\b', text, re.IGNORECASE)
    if cycle_match:
        cycles = cycle_match.group(1)
        extracted_attrs.append(AttributeItem(label="Number of Wash Cycles", value=cycles, uom=""))

    # 8. Dimensions & Depth With Door Open (e.g., 50-1/4IN, 50-3/16 in)
    door_depth_match = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\s*(?:in|inch|\"|in\.)\s*(?:depth with door open|depth)', text, re.IGNORECASE)
    if door_depth_match:
        door_depth = door_depth_match.group(1)
        extracted_attrs.append(AttributeItem(label="Depth With Door Open", value=door_depth, uom="in"))
        dimensions["depth_with_door_open"] = door_depth
    elif re.search(r'50-1/4IN', text, re.IGNORECASE):
        extracted_attrs.append(AttributeItem(label="Depth With Door Open", value="50-1/4", uom="in"))
        dimensions["depth_with_door_open"] = "50-1/4"

    # 9. Abrasives Dimensions (e.g., 5"x.045"x7/8", 12"x1/8"x1", 1/2"x18")
    dim_3_match = re.search(r'(\d+(?:-\d+/\d+|\.\d+)?)\"?\s*x\s*(\.?\d+(?:-\d+/\d+)?)\"?\s*x\s*(\d+(?:/\d+)?)\"?', text)
    if dim_3_match:
        diameter, thickness, arbor = dim_3_match.groups()
        extracted_attrs.append(AttributeItem(label="Wheel Diameter", value=diameter, uom="in"))
        extracted_attrs.append(AttributeItem(label="Thickness", value=thickness, uom="in"))
        extracted_attrs.append(AttributeItem(label="Arbor Size", value=arbor, uom="in"))
        dimensions["diameter"] = diameter
        dimensions["thickness"] = thickness
        dimensions["arbor"] = arbor

    # 10. Grit (e.g., P80, P120, P150, P220)
    grit_match = re.search(r'\b(P\d{2,4})\b', text, re.IGNORECASE)
    if grit_match:
        grit = grit_match.group(1).upper()
        extracted_attrs.append(AttributeItem(label="Grit Grade", value=grit, uom=""))

    # 11. Features
    if re.search(r'cleanboost', text, re.IGNORECASE):
        features.append("With CleanBoost™")
    if re.search(r'3rd rack', text, re.IGNORECASE):
        features.append("3rd Rack")
    if re.search(r'sensor cycle', text, re.IGNORECASE):
        features.append("Sensor Cycle")

    return {
        "attributes": extracted_attrs,
        "features": features,
        "series": series,
        "mount_type": mount_type,
        "material": material,
        "voltage": voltage,
        "amperage": amperage,
        "sound_level": sound_level,
        "dimensions": dimensions
    }
