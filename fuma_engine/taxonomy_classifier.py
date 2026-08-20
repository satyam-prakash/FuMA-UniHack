"""
Taxonomy and Classpath Classifier
Owned by Member 2.
Maps raw part descriptions and part numbers to hierarchical Classpath and base Product Name.
"""

import re
from typing import Tuple, Optional

# Pre-defined taxonomy mapping rules for target categories
TAXONOMY_RULES = [
    {
        "keywords": ["dishwasher", "dish washer"],
        "classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
        "unspsc": "52141505",
        "product_name": "Dishwasher"
    },
    {
        "keywords": ["faucet", "sink faucet", "lavatory faucet", "kitchen faucet"],
        "classpath": "Plumbing>Faucets & Fixtures>Kitchen & Bath Sink Faucets",
        "unspsc": "30181702",
        "product_name": "Sink Faucet"
    },
    {
        "keywords": ["cut-off disc", "cut off disc", "cut-off wheel", "metal cut off", "cut off wheel"],
        "classpath": "Abrasives>Cutting & Grinding Wheels>Cut-Off Wheels",
        "unspsc": "31191600",
        "product_name": "Cut-Off Disc"
    },
    {
        "keywords": ["sanding belt", "sanding disc", "stikit film", "abranet", "hiolit"],
        "classpath": "Abrasives>Sandpaper & Sanding Discs>Sanding Belts & Discs",
        "unspsc": "31191500",
        "product_name": "Sanding Disc"
    },
    {
        "keywords": ["cplg", "coupling", "fitting", "elbow", "tee", "adapter", "bushing", "nipple"],
        "classpath": "Plumbing>Pipe, Tube & Hose Fittings>Pipe Fittings",
        "unspsc": "40141700",
        "product_name": "Pipe Fitting"
    }
]

def classify_taxonomy(part_desc: str, mfg_part_num: Optional[str] = "") -> Tuple[str, str, str]:
    """
    Classifies a product description into (classpath, unspsc, product_name).
    
    Returns:
        tuple: (classpath, unspsc, product_name)
    """
    text = (part_desc + " " + (mfg_part_num or "")).lower()
    
    for rule in TAXONOMY_RULES:
        for kw in rule["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                return rule["classpath"], rule["unspsc"], rule["product_name"]
            
    # Default generic fallback
    return "Industrial Supplies & MRO>General Hardware", "", "Hardware Component"
