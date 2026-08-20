"""
Confidence & Quality Scorer
Owned by Member 2.
Evaluates character limit compliance, attribute completeness, and sets review flags.
"""

from typing import Dict, List, Any, Tuple

def evaluate_record(descs: Dict[str, str], extracted: Dict[str, Any], classpath: str) -> Tuple[float, bool, List[str]]:
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
    if len(mobile) < 40 or len(mobile) > 85:
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
        
    score = max(0.0, min(100.0, score))
    needs_review = score < 80.0
    
    return score, needs_review, reasons
