"""
Confidence & Quality Scorer
Owned by Member 2.

Evaluates character-limit compliance, attribute completeness, sparse descriptions,
brand-evidence strength and LOV compliance, then sets the review flag.

TWO DELIBERATE POSITIONS
------------------------
1. Blank-but-honest provenance (no verified manufacturer domain) is NOT penalised.
   Fabricating URLs to force a fill rate is worse than leaving them blank.

2. A weakly-evidenced brand is capped below the review threshold. Previously a
   brand guessed from an MPN substring shipped at confidence 100 -- 8.6% of the
   sample was confidently wrong. Under the brief's "invented values score zero"
   rule, a plausible wrong brand is worse than a blank, so weak matches are
   forced into the human queue rather than published.
"""

import re
from typing import Any, Dict, List, Tuple

PRODUCT_NOUNS = r'\b(dishwasher|refrigerator|fridge|freezer|microwave|washer|dryer|faucet|valve|fitting|coupling|elbow|tee|nipple|bushing|disc|wheel|belt|blade|bit|drill|driver|saw|sander|grinder|lamp|bulb|light|fixture|chandelier|pendant|sconce|outlet|switch|dimmer|panel|board|decking|fascia|railing|post|skylight|door|window|sheathing|siding|mortar|tape|screw|bolt|nut|anchor|latch|hanger|glove|glasses|mask|gauge|meter|apparel|hoodie|jacket|bottle|chest|box|nailer|stapler|planer|router|trimmer|blower|extractor|ratchet|wrench|cutter|knife|snip|fan|coffee|espresso|oven|cooktop|range|heater|thermostat|alarm|speaker)\b'

#: Rows scoring below this are queued for human review.
REVIEW_THRESHOLD = 80.0

#: Ceiling applied when the brand rests on weak evidence. Sits just below
#: REVIEW_THRESHOLD so such a row can never present as a clean success.
WEAK_BRAND_CONFIDENCE_CAP = 75.0

#: Brand tiers that constitute strong evidence (mirrors fuma_rules.brand_matcher).
#: DESCRIPTION_KEYWORD counts as strong because a distinctive brand name written
#: as a whole word in the supplier's own description is real evidence -- the old
#: danger was matching short tokens inside MPNs, which is now impossible.
STRONG_BRAND_TIERS = frozenset(
    {
        "EXPLICIT_BRAND_MASTER",
        "MANUFACTURER_EXACT",
        "DISTRIBUTOR_OVERRIDE",
        "MANUFACTURER_ALIAS",
        "DESCRIPTION_KEYWORD",
    }
)

#: Human-readable label per weak tier, used in the review reason.
_WEAK_TIER_LABELS = {
    "MANUFACTURER_FUZZY": "fuzzy manufacturer match",
    "DESCRIPTION_KEYWORD_AMBIGUOUS": "ambiguous description token",
}



def evaluate_record(
    descs: Dict[str, str],
    extracted: Dict[str, Any],
    classpath: str,
    raw_brand: str = "",
    raw_desc: str = "",
    brand_tier: str = "",
    brand_name: str = "",
    lov_compliance: float = -1.0,
) -> Tuple[float, bool, List[str]]:
    """
    Evaluates quality and generates (confidence_score, needs_review, review_reasons).

    Args:
        brand_tier: evidence tier from ``BrandMatch.tier``. Weak tiers cap the score.
        brand_name: resolved brand; blank means unresolved and needs a human.
        lov_compliance: fraction (0..1) of emitted values found in the approved
            LOV, or -1 when no LOV file is loaded (then it is not scored, because
            scoring our own seed list against itself would be meaningless).

    Returns:
        tuple: (score: float, needs_review: bool, reasons: List[str])
    """
    score = 100.0
    reasons: List[str] = []

    # 1. INVOICE_DESC limits (<= 40 chars & ALL CAPS)
    invoice = descs.get("invoice_desc", "")
    if len(invoice) > 40:
        score -= 20.0
        reasons.append(f"INVOICE_DESC exceeds 40 characters ({len(invoice)} chars)")
    if not invoice.isupper() and invoice:
        score -= 10.0
        reasons.append("INVOICE_DESC is not uppercase")

    # 2. MOBILE_DESC target window (60-80 chars)
    mobile = descs.get("mobile_desc", "")
    if len(mobile) < 60 or len(mobile) > 80:
        score -= 10.0
        reasons.append(f"MOBILE_DESC length ({len(mobile)} chars) outside optimal 60-80 window")

    # 3. Attribute completeness
    attrs = extracted.get("attributes", [])
    if len(attrs) == 0:
        score -= 25.0
        reasons.append("No technical attributes could be extracted from description")

    # 4. Classpath specificity
    if not classpath or "General Hardware" in classpath:
        score -= 15.0
        reasons.append("Uncertain category / generic classpath fallback")

    # 5. Sparse / low-context descriptions missing a product noun.
    # Penalty kept low (10 pts) so it does not trigger review on its own -- it
    # only bites in combination with another issue, keeping the queue honest.
    desc_str = raw_desc.strip().lower() if raw_desc else ""
    if desc_str and len(desc_str) < 30 and not re.search(PRODUCT_NOUNS, desc_str):
        score -= 10.0
        reasons.append(
            "Low-context description missing explicit product noun; manual verification recommended"
        )

    # 6. LOV compliance, only when a real LOV backs the vocabulary.
    if lov_compliance >= 0.0 and attrs:
        if lov_compliance < 0.5:
            score -= 20.0
            reasons.append(
                f"Only {lov_compliance * 100:.0f}% of attribute values matched the approved LOV"
            )
        elif lov_compliance < 0.8:
            score -= 10.0
            reasons.append(
                f"{lov_compliance * 100:.0f}% LOV compliance; some values are outside the approved vocabulary"
            )

    score = max(0.0, min(100.0, score))

    # 7. Brand-evidence gate. Applied AFTER clamping so it is a hard ceiling:
    # a weakly-evidenced brand cannot present as a clean success no matter how
    # well the row scores on formatting.
    if brand_tier:
        if not brand_name:
            score = min(score, WEAK_BRAND_CONFIDENCE_CAP)
            reasons.append(
                "Brand could not be resolved to the approved list (supplier gave a "
                "distributor/co-op name); needs human assignment"
            )
        elif brand_tier not in STRONG_BRAND_TIERS:
            score = min(score, WEAK_BRAND_CONFIDENCE_CAP)
            label = _WEAK_TIER_LABELS.get(brand_tier, brand_tier.lower().replace("_", " "))
            reasons.append(
                f"Brand '{brand_name}' rests on weak evidence ({label}); verify before publishing"
            )


    needs_review = score < REVIEW_THRESHOLD

    return score, needs_review, reasons
