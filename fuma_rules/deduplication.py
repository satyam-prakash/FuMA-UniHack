"""
De-duplication / Entity Resolution Stage.
Author: Member 1 (Master Data)
Package: fuma_rules

The brief lists de-duplication as an explicit pipeline stage:

    input analysis -> DE-DUPLICATION -> taxonomy -> attribute extraction -> ...

DESIGN DECISION: FLAG, NEVER DELETE
-----------------------------------
Duplicate rows are marked, not removed. A distributor's feed legitimately
contains the same MPN twice (two warehouses, two pack sizes, a re-listing), and
silently dropping rows would mean the delivery file no longer reconciles with the
input the client handed us -- an unauditable pipeline. Every row survives and
carries ``duplicate_of`` pointing at the row it duplicates, so a human can decide.

TWO-LEVEL MATCHING
------------------
1. **Primary (exact)** -- normalised ``Mfg_Part_Num``. An MPN is a manufacturer's
   own identifier, so a repeat is a genuine duplicate. High confidence.
2. **Secondary (similarity)** -- normalised ``Part_Desc`` + ``Part_Manuf`` for
   rows whose MPNs differ. Catches the same item re-keyed under a variant part
   number. Lower confidence, so it is reported separately.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

#: Reason codes surfaced in the review queue.
DUPLICATE_EXACT_MPN = "duplicate_exact_mpn"
DUPLICATE_SIMILAR_DESC = "duplicate_similar_description"


def _norm_key(value: Any) -> str:
    """Case/punctuation-insensitive key.

    ``"49-94-1940"`` and ``"49 94 1940"`` are the same part; ``"4x4 1G Box Cover"``
    and ``"4X4 1G BOX COVER"`` are the same description.
    """
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _desc_key(row: Dict[str, Any]) -> str:
    """Secondary key: description + manufacturer.

    Manufacturer is included deliberately -- two suppliers can ship a "4x4 1G Box
    Cover" and those are different products, not duplicates.
    """
    return f"{_norm_key(row.get('Part_Desc'))}|{_norm_key(row.get('Part_Manuf'))}"


def detect_duplicates(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Annotates each row with duplicate metadata. Input order is preserved.

    Adds four keys per row:
        ``is_duplicate``     bool
        ``duplicate_of``     1-based row number of the first occurrence, or None
        ``duplicate_reason`` reason code, or ""
        ``duplicate_group``  key shared by all members of the group, or ""

    The first occurrence of a group is NOT marked a duplicate: it is the primary.
    """
    first_by_mpn: Dict[str, int] = {}
    first_by_desc: Dict[str, int] = {}
    annotated: List[Dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        out = dict(row)
        out.update(
            {
                "is_duplicate": False,
                "duplicate_of": None,
                "duplicate_reason": "",
                "duplicate_group": "",
            }
        )

        mpn_key = _norm_key(row.get("Mfg_Part_Num"))
        desc_key = _desc_key(row)

        if mpn_key and mpn_key in first_by_mpn:
            out.update(
                {
                    "is_duplicate": True,
                    "duplicate_of": first_by_mpn[mpn_key],
                    "duplicate_reason": DUPLICATE_EXACT_MPN,
                    "duplicate_group": mpn_key,
                }
            )
        elif desc_key.strip("|") and desc_key in first_by_desc:
            # Same description AND manufacturer but a different MPN -- probably
            # the same item re-keyed. Lower confidence than an MPN collision.
            out.update(
                {
                    "is_duplicate": True,
                    "duplicate_of": first_by_desc[desc_key],
                    "duplicate_reason": DUPLICATE_SIMILAR_DESC,
                    "duplicate_group": desc_key,
                }
            )

        if mpn_key:
            first_by_mpn.setdefault(mpn_key, index)
        if desc_key.strip("|"):
            first_by_desc.setdefault(desc_key, index)

        annotated.append(out)

    return annotated


def duplicate_summary(annotated_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts for the dashboard and the benchmark scorecard."""
    total = len(annotated_rows)
    exact = sum(1 for r in annotated_rows if r.get("duplicate_reason") == DUPLICATE_EXACT_MPN)
    similar = sum(
        1 for r in annotated_rows if r.get("duplicate_reason") == DUPLICATE_SIMILAR_DESC
    )
    groups = {
        r["duplicate_group"]
        for r in annotated_rows
        if r.get("is_duplicate") and r.get("duplicate_group")
    }
    return {
        "total_rows": total,
        "duplicate_rows": exact + similar,
        "exact_mpn_duplicates": exact,
        "similar_description_duplicates": similar,
        "duplicate_groups": len(groups),
        "unique_rows": total - (exact + similar),
        "policy": "flagged, not deleted (traceability preserved)",
    }
