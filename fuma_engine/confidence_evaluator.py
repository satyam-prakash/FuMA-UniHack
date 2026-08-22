"""
Confidence & Quality Scorer
Owned by Member 2.
Evaluates character limit compliance, attribute completeness, sparse descriptions, and sets review flags.
Blank-but-honest provenance (no verified manufacturer domain) is NOT penalized —
fabricating URLs to force fill rate is worse than leaving them blank.
"""

import re
from typing import Dict, List, Any, Tuple

PRODUCT_NOUNS = r'\b(dishwasher|refrigerator|fridge|freezer|microwave|washer|dryer|faucet|valve|fitting|coupling|elbow|tee|nipple|bushing|disc|wheel|belt|blade|bit|drill|driver|saw|sander|grinder|lamp|bulb|light|fixture|chandelier|pendant|sconce|outlet|switch|dimmer|panel|board|decking|fascia|railing|post|skylight|door|window|sheathing|siding|mortar|tape|screw|bolt|nut|anchor|latch|hanger|glove|glasses|mask|gauge|meter|apparel|hoodie|jacket|bottle|chest|box|nailer|stapler|planer|router|trimmer|blower|extractor|ratchet|wrench|cutter|knife|snip|fan|coffee|espresso|oven|cooktop|range|heater|thermostat|alarm|speaker)\b'

def evaluate_record(descs: Dict[str, str], extracted: Dict[str, Any], classpath: str, raw_brand: str = "", raw_desc: str = "") -> Tuple[float, bool, List[str]]:
    """
    Evaluates quality and generates (confidence_score, needs_review, review_reasons).
    
    Returns:
        tuple: (score: float, needs_review: bool, reasons: List[str])
    """
    score = 100.0
    reasons = []
    
    # 1. Check INVOICE_DESC limit (<= 40 chars & ALL CAPS)
    invoice = descs.get("invoice_desc", "")
    if len(invoice) > 40:
        score -= 20.0
        reasons.append(f"INVOICE_DESC exceeds 40 characters ({len(invoice)} chars)")
    if not invoice.isupper() and invoice:
        score -= 10.0
        reasons.append("INVOICE_DESC is not uppercase")
        
    # 2. Check MOBILE_DESC limit (60-80 chars target)
    mobile = descs.get("mobile_desc", "")
    if len(mobile) < 60 or len(mobile) > 80:
        score -= 10.0
        reasons.append(f"MOBILE_DESC length ({len(mobile)} chars) outside optimal 60-80 window")
        
    # 3. Check Attribute Completeness
    attrs = extracted.get("attributes", [])
    if len(attrs) == 0:
        score -= 25.0
        reasons.append("No technical attributes could be extracted from description")
        
    # 4. Check Classpath
    if not classpath or "General Hardware" in classpath:
        score -= 15.0
        reasons.append("Uncertain category / generic classpath fallback")
        
    # 5. Check Sparse / Low-Context Descriptions missing product noun
    # Descriptions under 30 chars with no recognisable product noun get a
    # mild review flag.  The penalty is kept low (10 pts) so it does not
    # trigger review on its own — it only bites when combined with another
    # issue, keeping the review queue honest.
    desc_str = raw_desc.strip().lower() if raw_desc else ""
    if desc_str and len(desc_str) < 30 and not re.search(PRODUCT_NOUNS, desc_str):
        score -= 10.0
        reasons.append("Low-context description missing explicit product noun; manual verification recommended")
        
    score = max(0.0, min(100.0, score))
    needs_review = score < 80.0
    
    return score, needs_review, reasons
