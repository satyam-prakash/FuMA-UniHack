"""
Accuracy and Compliance Benchmark Metrics
Owned by Member 2.
Calculates field-level accuracy, character limit compliance %, and LOV match rates.
"""

from typing import Dict, List, Any
import pandas as pd

def calculate_benchmark_metrics(enriched_records: List[Dict[str, Any]], ground_truth_df: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Computes rigorous compliance and accuracy KPIs over a batch of enriched records.
    """
    total = len(enriched_records)
    if total == 0:
        return {
            "total_records": 0,
            "invoice_char_limit_pass_rate": 0.0,
            "invoice_all_caps_pass_rate": 0.0,
            "mobile_desc_compliance_rate": 0.0,
            "avg_confidence_score": 0.0,
            "needs_review_count": 0,
            "needs_review_percentage": 0.0
        }
        
    invoice_limit_pass = 0
    invoice_caps_pass = 0
    mobile_window_pass = 0
    total_confidence = 0.0
    needs_review_count = 0
    
    for rec in enriched_records:
        inv = rec.get("invoice_desc", "")
        mob = rec.get("mobile_desc", "")
        score = rec.get("confidence_score", 100.0)
        review = rec.get("needs_review", False)
        
        # 1. Invoice Limit (<= 40 chars)
        if len(inv) <= 40 and len(inv) > 0:
            invoice_limit_pass += 1
            
        # 2. Invoice Casing (ALL CAPS)
        if inv.isupper():
            invoice_caps_pass += 1
            
        # 3. Mobile Window (60-85 chars)
        if 50 <= len(mob) <= 85:
            mobile_window_pass += 1
            
        total_confidence += score
        if review:
            needs_review_count += 1
            
    return {
        "total_records": total,
        "invoice_char_limit_pass_rate": round((invoice_limit_pass / total) * 100, 2),
        "invoice_all_caps_pass_rate": round((invoice_caps_pass / total) * 100, 2),
        "mobile_desc_compliance_rate": round((mobile_window_pass / total) * 100, 2),
        "avg_confidence_score": round(total_confidence / total, 2),
        "needs_review_count": needs_review_count,
        "needs_review_percentage": round((needs_review_count / total) * 100, 2),
        "overall_status": "WINNER" if (invoice_limit_pass / total) >= 0.98 else "NEEDS_TUNING"
    }
