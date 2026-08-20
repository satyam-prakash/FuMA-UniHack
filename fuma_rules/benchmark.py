"""
Evaluation & Ground-Truth Benchmarking Engine for Industrial Product Catalog Data.
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
Package: fuma_rules
"""

import csv
import os
from typing import Dict, List, Any, Optional, Tuple
from .uom_standardizer import MASTER_UOM_MAP, standardize_uom

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False


class GroundTruthBenchmark:
    """
    Evaluates catalog enrichment pipeline predictions against Ground Truth delivery format.
    Calculates field-level precision, character-limit compliance, UOM standardization, and audit flags.
    """

    def __init__(self, ground_truth_path: Optional[str] = None):
        self.ground_truth_path = ground_truth_path
        self.ground_truth_records: List[Dict[str, str]] = []
        if ground_truth_path and os.path.exists(ground_truth_path):
            self.load_ground_truth(ground_truth_path)

    def load_ground_truth(self, file_path: str) -> None:
        """Loads ground truth rows from CSV file."""
        self.ground_truth_records = []
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.ground_truth_records.append(row)

    def _token_similarity(self, s1: str, s2: str) -> float:
        """Calculates token similarity (0.0 to 100.0)."""
        if not s1 and not s2:
            return 100.0
        if not s1 or not s2:
            return 0.0
        if HAS_RAPIDFUZZ:
            return float(fuzz.token_sort_ratio(s1, s2))
        import difflib
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100.0

    def evaluate_record(self, gt: Dict[str, str], pred: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a single predicted row against a ground truth row.
        Returns field-by-field scores and audit flags.
        """
        scores: Dict[str, Any] = {}
        audit_issues: List[str] = []

        # 1. Manufacturer Name Match
        gt_mfg = str(gt.get("MANUFACTURER_NAME", "")).strip()
        pred_mfg = str(pred.get("MANUFACTURER_NAME", "")).strip()
        mfg_match = (gt_mfg.lower() == pred_mfg.lower()) if (gt_mfg and pred_mfg) else (gt_mfg == pred_mfg)
        scores["mfg_match"] = mfg_match
        if not mfg_match and gt_mfg:
            audit_issues.append(f"Manufacturer mismatch: expected '{gt_mfg}', got '{pred_mfg}'")

        # 2. Brand Name Match (including ® / ™)
        gt_brand = str(gt.get("BRAND_NAME", "")).strip()
        pred_brand = str(pred.get("BRAND_NAME", "")).strip()
        brand_match = (gt_brand == pred_brand)
        scores["brand_match"] = brand_match
        if not brand_match and gt_brand:
            audit_issues.append(f"Brand mismatch: expected '{gt_brand}', got '{pred_brand}'")

        # 3. Invoice Description (<= 40 chars, ALL CAPS)
        pred_inv = str(pred.get("INVOICE_DESC", "")).strip()
        inv_len_valid = len(pred_inv) <= 40
        inv_caps_valid = (pred_inv == pred_inv.upper()) if pred_inv else True
        scores["invoice_desc_len_valid"] = inv_len_valid
        scores["invoice_desc_caps_valid"] = inv_caps_valid
        if not inv_len_valid:
            audit_issues.append(f"INVOICE_DESC exceeds 40 chars ({len(pred_inv)} chars)")

        # 4. Mobile Description (60-80 chars)
        pred_mob = str(pred.get("MOBILE_DESC", "")).strip()
        mob_len_valid = 60 <= len(pred_mob) <= 80 if pred_mob else False
        scores["mobile_desc_len_valid"] = mob_len_valid
        if pred_mob and not (60 <= len(pred_mob) <= 80):
            audit_issues.append(f"MOBILE_DESC outside 60-80 char range ({len(pred_mob)} chars)")

        # 5. Short Description Similarity
        gt_short = str(gt.get("SHORT_DESC", "")).strip()
        pred_short = str(pred.get("SHORT_DESC", "")).strip()
        short_sim = self._token_similarity(gt_short, pred_short)
        scores["short_desc_similarity"] = short_sim

        # 6. Overall Row Confidence Calculation
        weights = {
            "mfg": 0.25,
            "brand": 0.25,
            "inv_len": 0.15,
            "mob_len": 0.15,
            "short_sim": 0.20,
        }
        confidence = (
            (100.0 if mfg_match else 0.0) * weights["mfg"]
            + (100.0 if brand_match else 0.0) * weights["brand"]
            + (100.0 if inv_len_valid and inv_caps_valid else 0.0) * weights["inv_len"]
            + (100.0 if mob_len_valid else 0.0) * weights["mob_len"]
            + short_sim * weights["short_sim"]
        )
        scores["confidence_score"] = round(confidence, 2)
        scores["needs_human_review"] = confidence < 75.0 or len(audit_issues) > 0
        scores["audit_issues"] = audit_issues

        return scores

    def evaluate_batch(
        self,
        predicted_records: List[Dict[str, Any]],
        ground_truth_records: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a batch of predicted records against the ground truth records.
        """
        gt_list = ground_truth_records if ground_truth_records is not None else self.ground_truth_records
        total = min(len(gt_list), len(predicted_records))
        if total == 0:
            return {"error": "No records to evaluate", "total_evaluated": 0}

        mfg_matches = 0
        brand_matches = 0
        inv_valid_count = 0
        mob_valid_count = 0
        short_sim_sum = 0.0
        confidence_sum = 0.0
        review_queue_count = 0
        row_evaluations: List[Dict[str, Any]] = []

        for i in range(total):
            gt = gt_list[i]
            pred = predicted_records[i]
            rec_eval = self.evaluate_record(gt, pred)
            rec_eval["row_index"] = i
            rec_eval["mpn"] = pred.get("Mfg_Part_Num") or gt.get("Mfg_Part_Num")
            row_evaluations.append(rec_eval)

            if rec_eval["mfg_match"]:
                mfg_matches += 1
            if rec_eval["brand_match"]:
                brand_matches += 1
            if rec_eval["invoice_desc_len_valid"] and rec_eval["invoice_desc_caps_valid"]:
                inv_valid_count += 1
            if rec_eval["mobile_desc_len_valid"]:
                mob_valid_count += 1
            short_sim_sum += rec_eval["short_desc_similarity"]
            confidence_sum += rec_eval["confidence_score"]
            if rec_eval["needs_human_review"]:
                review_queue_count += 1

        summary = {
            "total_evaluated": total,
            "mfg_accuracy_pct": round((mfg_matches / total) * 100, 2),
            "brand_accuracy_pct": round((brand_matches / total) * 100, 2),
            "invoice_desc_compliance_pct": round((inv_valid_count / total) * 100, 2),
            "mobile_desc_compliance_pct": round((mob_valid_count / total) * 100, 2),
            "short_desc_avg_similarity_pct": round(short_sim_sum / total, 2),
            "avg_confidence_score_pct": round(confidence_sum / total, 2),
            "needs_human_review_count": review_queue_count,
            "review_rate_pct": round((review_queue_count / total) * 100, 2),
            "row_evaluations": row_evaluations,
        }

        return summary
