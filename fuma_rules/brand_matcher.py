"""
Manufacturer & Canonical Brand Resolution with Legal Trademarks (®, ™).
Author: Member 1 (Master Data, Normalization & Evaluation Lead)
Package: fuma_rules

EVIDENCE HIERARCHY (the core design decision)
---------------------------------------------
The previous implementation scanned brand KEYWORDS against
``description + MPN`` **before** weighing any manufacturer evidence. Because MPNs
are dense alphanumeric strings, short keywords collided constantly:

    DCB1104 Dewalt Charger   -> "dcb" matched Freud  -> Diablo®  (should be DEWALT®)
    DPH31B #3 Phillips Drive -> "phillips"           -> Philips® (a lighting brand)

Measured on the 1,000-row sample: **34.3% of unambiguous rows got the wrong brand,
and 8.6% of all rows shipped at confidence >= 80 with a plausible-looking but
incorrect ®-marked name.** Under the brief's "invented values score zero" rule a
confidently wrong brand is worse than a blank.

So resolution now runs strictly strongest-evidence-first, and every result carries
the tier that produced it:

    T1 EXPLICIT_BRAND_MASTER  supplier's own brand field matched the approved list
    T2 MANUFACTURER_EXACT     manufacturer string matched the approved master
    T3 DISTRIBUTOR_OVERRIDE   known co-op + MPN prefix identifies the real maker
    T4 MANUFACTURER_ALIAS     mfg string resolved after corporate-suffix stripping
    T5 MANUFACTURER_FUZZY     fuzzy match on manufacturer above threshold
    T6 DESCRIPTION_KEYWORD    brand named in the DESCRIPTION (never the MPN)
    T7 UNRESOLVED             no approved brand; manufacturer name passed through

Tiers T1-T4 are strong. T5-T6 are weak and are reported as such so the confidence
evaluator can hold them below the review threshold instead of shipping them.

Two hard rules that kill the old failure modes:
  * Keywords are matched against the DESCRIPTION ONLY, never the MPN.
  * Ambiguous tokens (``phillips``, ``hunter``, ``file``) need supporting category
    context before they can name a brand.
"""

import difflib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .sanitizer import clean_part_description, clean_placeholder, clean_supplier_name

try:
    from rapidfuzz import fuzz, process

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


# ---------------------------------------------------------------------------
# Evidence tiers
# ---------------------------------------------------------------------------

TIER_EXPLICIT_BRAND = "EXPLICIT_BRAND_MASTER"
TIER_MFG_EXACT = "MANUFACTURER_EXACT"
TIER_DISTRIBUTOR = "DISTRIBUTOR_OVERRIDE"
TIER_MFG_ALIAS = "MANUFACTURER_ALIAS"
TIER_MFG_FUZZY = "MANUFACTURER_FUZZY"
TIER_DESC_KEYWORD = "DESCRIPTION_KEYWORD"
TIER_DESC_KEYWORD_AMBIGUOUS = "DESCRIPTION_KEYWORD_AMBIGUOUS"
TIER_UNRESOLVED = "UNRESOLVED"

#: Tiers strong enough to publish without a review flag.
#:
#: ``TIER_DESC_KEYWORD`` is included deliberately. A *distinctive* brand token
#: appearing as a whole word in the supplier's own description ("Harvest Azek PVC
#: Decking" -> AZEK®) is real evidence, and it is exactly how a human would read
#: the row. What made description matching dangerous before was matching short
#: tokens INSIDE MPNs (`dcb` -> Diablo) -- that is now structurally impossible:
#: keywords are matched against the description only, must be >= 4 characters,
#: and must be word-boundary anchored.
#:
#: Genuinely ambiguous words ("phillips" the screw drive, "hunter" the noun) get
#: the separate ``TIER_DESC_KEYWORD_AMBIGUOUS`` tier and stay weak.
STRONG_TIERS = frozenset(
    {
        TIER_EXPLICIT_BRAND,
        TIER_MFG_EXACT,
        TIER_DISTRIBUTOR,
        TIER_MFG_ALIAS,
        TIER_DESC_KEYWORD,
    }
)



@dataclass
class BrandMatch:
    """Resolution result plus the evidence that produced it."""

    manufacturer_name: str
    brand_name: str
    tier: str
    score: float = 1.0
    evidence: str = ""

    @property
    def is_strong(self) -> bool:
        return self.tier in STRONG_TIERS

    @property
    def is_resolved(self) -> bool:
        return self.tier != TIER_UNRESOLVED


# Canonical Master Brand & Manufacturer Catalog (seed vocabulary).
# Superseded at runtime by UniCat_Manufacturer_and_Brand_List.xlsx when present.
# KEYWORDS are description-only cues; they are never matched against an MPN.
CANONICAL_BRAND_CATALOG: List[Dict[str, str]] = [
    {
        "MANUFACTURER_NAME": "Rheem Manufacturing",
        "BRAND_NAME": "FRIGIDAIRE®",
        "MANUFACTURER_CODE": "RHEEM",
        "BRAND_CODE": "FRIG",
        "KEYWORDS": ["frigidaire"],
    },
    {
        "MANUFACTURER_NAME": "Whirlpool Corporation",
        "BRAND_NAME": "Whirlpool®",
        "MANUFACTURER_CODE": "WHIRL",
        "BRAND_CODE": "WHRL",
        "KEYWORDS": ["whirlpool"],
    },
    {
        "MANUFACTURER_NAME": "Freud America, Inc.",
        "BRAND_NAME": "Diablo®",
        "MANUFACTURER_CODE": "FREUD",
        "BRAND_CODE": "DIAB",
        "KEYWORDS": ["diablo", "freud"],
    },
    {
        "MANUFACTURER_NAME": "Milwaukee Electric Tool Corporation",
        "BRAND_NAME": "Milwaukee®",
        "MANUFACTURER_CODE": "MILW",
        "BRAND_CODE": "MLWK",
        "KEYWORDS": ["milwaukee", "milw"],
    },
    {
        "MANUFACTURER_NAME": "3M",
        "BRAND_NAME": "3M™",
        "MANUFACTURER_CODE": "3M",
        "BRAND_CODE": "3M",
        "KEYWORDS": ["cubitron", "stikit", "scotch"],
    },
    {
        "MANUFACTURER_NAME": "Mirka Abrasives, Inc.",
        "BRAND_NAME": "Mirka®",
        "MANUFACTURER_CODE": "MIRKA",
        "BRAND_CODE": "MRKA",
        "KEYWORDS": ["mirka", "hiolit", "abranet"],
    },
    {
        "MANUFACTURER_NAME": "Stanley Black & Decker",
        "BRAND_NAME": "DEWALT®",
        "MANUFACTURER_CODE": "DEWALT",
        "BRAND_CODE": "DWLT",
        "KEYWORDS": ["dewalt", "dewlt", "flexvolt"],
    },
    {
        "MANUFACTURER_NAME": "Stanley Black & Decker",
        "BRAND_NAME": "STANLEY®",
        "MANUFACTURER_CODE": "STANLEY",
        "BRAND_CODE": "STNL",
        "KEYWORDS": ["stanley", "fatmax"],
    },
    {
        "MANUFACTURER_NAME": "Stanley Black & Decker",
        "BRAND_NAME": "IRWIN®",
        "MANUFACTURER_CODE": "IRWIN",
        "BRAND_CODE": "IRWN",
        "KEYWORDS": ["irwin"],
    },
    {
        "MANUFACTURER_NAME": "Philips Lighting Holding B.V.",
        "BRAND_NAME": "Philips®",
        "MANUFACTURER_CODE": "PHILIPS",
        "BRAND_CODE": "PHLP",
        # "phillips" is deliberately absent: it is overwhelmingly a screw drive
        # type in this catalogue. Gated through AMBIGUOUS_KEYWORDS instead.
        "KEYWORDS": [],
    },
    {
        "MANUFACTURER_NAME": "Kichler Lighting LLC",
        "BRAND_NAME": "Kichler®",
        "MANUFACTURER_CODE": "KICHLER",
        "BRAND_CODE": "KCHL",
        "KEYWORDS": ["kichler"],
    },
    {
        "MANUFACTURER_NAME": "Satco Products, Inc.",
        "BRAND_NAME": "Satco®",
        "MANUFACTURER_CODE": "SATCO",
        "BRAND_CODE": "STCO",
        "KEYWORDS": ["satco"],
    },
    {
        "MANUFACTURER_NAME": "Makita U.S.A., Inc.",
        "BRAND_NAME": "Makita®",
        "MANUFACTURER_CODE": "MAKITA",
        "BRAND_CODE": "MAKT",
        "KEYWORDS": ["makita"],
    },
    {
        "MANUFACTURER_NAME": "Southwire Company, LLC",
        "BRAND_NAME": "Southwire®",
        "MANUFACTURER_CODE": "SOUTHWIRE",
        "BRAND_CODE": "STHW",
        "KEYWORDS": ["southwire"],
    },
    {
        "MANUFACTURER_NAME": "Leviton Manufacturing Co., Inc.",
        "BRAND_NAME": "Leviton®",
        "MANUFACTURER_CODE": "LEVITON",
        "BRAND_CODE": "LVTN",
        "KEYWORDS": ["leviton"],
    },
    {
        "MANUFACTURER_NAME": "Festool USA",
        "BRAND_NAME": "Festool®",
        "MANUFACTURER_CODE": "FESTOOL",
        "BRAND_CODE": "FSTL",
        "KEYWORDS": ["festool", "systainer"],
    },
    {
        "MANUFACTURER_NAME": "Kreg Tool Company",
        "BRAND_NAME": "Kreg®",
        "MANUFACTURER_CODE": "KREG",
        "BRAND_CODE": "KREG",
        "KEYWORDS": ["kreg"],
    },
    {
        "MANUFACTURER_NAME": "Hunter Fan Company",
        "BRAND_NAME": "Hunter®",
        "MANUFACTURER_CODE": "HUNTER",
        "BRAND_CODE": "HNTR",
        "KEYWORDS": [],  # "hunter" gated: also a common product-line word
    },
    {
        "MANUFACTURER_NAME": "Robert Bosch Tool Corporation",
        "BRAND_NAME": "Bosch®",
        "MANUFACTURER_CODE": "BOSCH",
        "BRAND_CODE": "BSCH",
        "KEYWORDS": ["bosch"],
    },
    {
        "MANUFACTURER_NAME": "Schneider Electric",
        "BRAND_NAME": "Square D®",
        "MANUFACTURER_CODE": "SCHNEIDER",
        "BRAND_CODE": "SQD",
        "KEYWORDS": ["square d"],
    },
    {
        "MANUFACTURER_NAME": "Cooper Lighting Solutions",
        "BRAND_NAME": "Cooper Lighting®",
        "MANUFACTURER_CODE": "COOPER",
        "BRAND_CODE": "COOP",
        "KEYWORDS": ["cooper lighting"],
    },
    {
        "MANUFACTURER_NAME": "Feit Electric Company",
        "BRAND_NAME": "Feit Electric®",
        "MANUFACTURER_CODE": "FEIT",
        "BRAND_CODE": "FEIT",
        "KEYWORDS": ["feit electric", "feit"],
    },
    {
        "MANUFACTURER_NAME": "KYOCERA SENCO Industrial Tools, Inc.",
        "BRAND_NAME": "SENCO®",
        "MANUFACTURER_CODE": "SENCO",
        "BRAND_CODE": "SNCO",
        "KEYWORDS": ["senco"],
    },
    {
        "MANUFACTURER_NAME": "First Alert",
        "BRAND_NAME": "First Alert®",
        "MANUFACTURER_CODE": "FIRSTALERT",
        "BRAND_CODE": "FALT",
        "KEYWORDS": ["first alert"],
    },
    {
        "MANUFACTURER_NAME": "Acuity Brands Lighting, Inc.",
        "BRAND_NAME": "Lithonia Lighting®",
        "MANUFACTURER_CODE": "ACUITY",
        "BRAND_CODE": "LITH",
        "KEYWORDS": ["lithonia"],
    },
    {
        "MANUFACTURER_NAME": "Streamlight, Inc.",
        "BRAND_NAME": "Streamlight®",
        "MANUFACTURER_CODE": "STREAMLIGHT",
        "BRAND_CODE": "STRM",
        "KEYWORDS": ["streamlight"],
    },
    {
        "MANUFACTURER_NAME": "Wera Tools Inc.",
        "BRAND_NAME": "Wera®",
        "MANUFACTURER_CODE": "WERA",
        "BRAND_CODE": "WERA",
        "KEYWORDS": ["wera"],
    },
    {
        "MANUFACTURER_NAME": "SawStop, LLC",
        "BRAND_NAME": "SawStop®",
        "MANUFACTURER_CODE": "SAWSTOP",
        "BRAND_CODE": "SWST",
        "KEYWORDS": ["sawstop", "saw stop"],
    },
    {
        "MANUFACTURER_NAME": "Klein Tools, Inc.",
        "BRAND_NAME": "Klein Tools®",
        "MANUFACTURER_CODE": "KLEIN",
        "BRAND_CODE": "KLN",
        "KEYWORDS": ["klein"],
    },
    {
        "MANUFACTURER_NAME": "Trex Company, Inc.",
        "BRAND_NAME": "Trex®",
        "MANUFACTURER_CODE": "TREX",
        "BRAND_CODE": "TREX",
        "KEYWORDS": ["trex", "transcend", "enhance naturals"],
    },
    {
        "MANUFACTURER_NAME": "The AZEK Company",
        "BRAND_NAME": "AZEK®",
        "MANUFACTURER_CODE": "AZEK",
        "BRAND_CODE": "AZEK",
        "KEYWORDS": ["azek", "timbertech"],
    },
    {
        "MANUFACTURER_NAME": "James Hardie Building Products, Inc.",
        "BRAND_NAME": "James Hardie®",
        "MANUFACTURER_CODE": "HARDIE",
        "BRAND_CODE": "HRDI",
        "KEYWORDS": ["hardiepanel", "hardieplank", "hardie"],
    },
]

# Brand alias -> canonical trademarked name.
# Matched against BOTH the supplier brand field and the manufacturer string --
# omitting the manufacturer side was why "3 M Co" and "Southwire/g Turner" never
# resolved.
BRAND_ALIAS_MAP: Dict[str, str] = {
    "frigidaire": "FRIGIDAIRE®",
    "whirlpool": "Whirlpool®",
    "diablo": "Diablo®",
    "freud": "Diablo®",
    "milwaukee": "Milwaukee®",
    "milw": "Milwaukee®",
    "3m": "3M™",
    "3 m": "3M™",
    "mirka": "Mirka®",
    "dewalt": "DEWALT®",
    "dewlt": "DEWALT®",
    "stanley": "STANLEY®",
    "irwin": "IRWIN®",
    "bosch": "Bosch®",
    "makita": "Makita®",
    "philips": "Philips®",
    # Supplier misspelling: "Phillips Lighting (5142)". Safe as a MANUFACTURER-side
    # alias -- it is only the DESCRIPTION keyword "phillips" (a screw drive type)
    # that must stay gated behind AMBIGUOUS_KEYWORDS.
    "phillips": "Philips®",
    "phillips lighting": "Philips®",
    "kichler": "Kichler®",

    "satco": "Satco®",
    "southwire": "Southwire®",
    "leviton": "Leviton®",
    "festool": "Festool®",
    "kreg": "Kreg®",
    "hunter": "Hunter®",
    "square d": "Square D®",
    "senco": "SENCO®",
    "first alert": "First Alert®",
    "lithonia": "Lithonia Lighting®",
    "streamlight": "Streamlight®",
    "wera": "Wera®",
    "sawstop": "SawStop®",
    "saw stop": "SawStop®",
    "klein": "Klein Tools®",
    "klein tools": "Klein Tools®",
    "trex": "Trex®",
    "azek": "AZEK®",
    "timbertech": "AZEK®",
    "hardie": "James Hardie®",
    "james hardie": "James Hardie®",
}

# Known co-op / distributor -> real manufacturer, keyed by MPN prefix.
# These are STRONG evidence: the prefix is a deliberate manufacturer signal.
DISTRIBUTOR_OVERRIDE_MAP: Dict[str, Dict[str, str]] = {
    "appliance dealers cooperative": {
        "PDSH": "Rheem Manufacturing",
        "FFCD": "Rheem Manufacturing",
        "WDTS": "Whirlpool Corporation",
        "WDF": "Whirlpool Corporation",
        "WDT": "Whirlpool Corporation",
    },
    "jam industrial supply llc": {
        "3MABR": "3M",
        "3M": "3M",
    },
}

#: Distributors/co-ops that must never be published as a BRAND_NAME.
#: Their name is a supply-chain fact, not a product brand.
KNOWN_DISTRIBUTORS = frozenset(
    {
        "appliance dealers cooperative",
        "jam industrial supply llc",
        "jam industrial supply",
        "boise cascade building materials",
        "parksite",
        "milwaukee accessory",
        "black & decker/dewlt",
        "southwire/g turner",
    }
)

#: Tokens that name a brand only with supporting category context.
#: ``phillips`` is a screw drive in most rows; ``hunter``/``file`` are common nouns.
AMBIGUOUS_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "phillips": {
        "brand": "Philips®",
        "requires": ("lamp", "bulb", "led", "lighting", "luminaire", "fixture"),
        "blocked_by": ("drive", "bit", "screw", "driver", "fastener", "#1", "#2", "#3"),
    },
    "hunter": {
        "brand": "Hunter®",
        "requires": ("fan", "ceiling fan"),
        "blocked_by": (),
    },
}

#: Corporate suffixes stripped before alias lookup, so "Freud Inc" -> "freud".
_CORPORATE_SUFFIXES = (
    "incorporated", "corporation", "company", "holding", "holdings", "inc", "co",
    "llc", "ltd", "lp", "plc", "gmbh", "bv", "b.v.", "sa", "ag", "usa", "us",
    "tool", "tools", "products", "product", "group", "brands", "industries",
    "industrial", "supply", "mfg", "manufacturing", "electric", "lighting",
    "accessory", "accessories", "international", "enterprises",
)

_TRADEMARK_RE = re.compile(r"[®™]")


def _strip_tm(value: str) -> str:
    return _TRADEMARK_RE.sub("", str(value or "")).strip()


def _norm(value: str) -> str:
    """Lowercase alphanumeric key with symbols and spacing removed."""
    return re.sub(r"[^a-z0-9]+", "", _strip_tm(value).lower())


def _alias_candidates(raw: str) -> List[str]:
    """Progressively simplified forms of a messy supplier string.

    ``"Black & Decker/dewlt"`` yields ``black & decker``, ``dewlt`` (split on
    ``/``), and ``"3 M Co"`` yields ``3 m`` once ``co`` is stripped. This is what
    lets aliases fire on the manufacturer side.
    """
    text = _strip_tm(raw).lower().strip()
    if not text:
        return []

    out: List[str] = []

    def push(value: str) -> None:
        value = re.sub(r"\s+", " ", value).strip(" .,-&/")
        if value and value not in out:
            out.append(value)

    push(text)
    # Slash/comma-separated vendor compounds: try each side independently.
    for part in re.split(r"[/,]", text):
        push(part)

    for base in list(out):
        tokens = [t for t in re.split(r"[^a-z0-9&]+", base) if t]
        # Drop trailing corporate noise: "freud inc" -> "freud".
        trimmed = list(tokens)
        while trimmed and trimmed[-1] in _CORPORATE_SUFFIXES:
            trimmed.pop()
        if trimmed:
            push(" ".join(trimmed))
            # Leading 1-2 tokens catch "milwaukee accessory" -> "milwaukee".
            push(trimmed[0])
            if len(trimmed) >= 2:
                push(" ".join(trimmed[:2]))
    return out


class BrandManufacturerResolver:
    """Resolves messy supplier strings to approved MANUFACTURER_NAME / BRAND_NAME."""

    #: Fuzzy threshold for T5. Deliberately high: a near-miss on a brand name is
    #: a wrong brand, and the brief penalises invented values absolutely.
    FUZZY_THRESHOLD = 0.88

    #: Minimum description-keyword length for T6. Short tokens caused the
    #: `dcb`->Diablo and `3m`->3M collisions.
    MIN_KEYWORD_LEN = 4

    def __init__(
        self,
        custom_catalog: Optional[List[Dict[str, str]]] = None,
        use_reference_files: bool = True,
    ):
        catalog = custom_catalog
        self._alias_map = dict(BRAND_ALIAS_MAP)
        self.master_source = "seed"

        if catalog is None and use_reference_files:
            # Prefer the approved 27,000-row master when it has been supplied.
            try:
                from fuma_rules.reference_data import load_reference_bundle

                bundle = load_reference_bundle()
                if any(
                    s.loaded_from_file and s.name == "Manufacturer/Brand master"
                    for s in bundle.sources
                ):
                    catalog = bundle.manufacturer_brand
                    self._alias_map.update(bundle.brand_alias)
                    self.master_source = "master_file"
            except Exception:  # noqa: BLE001 - never let loading break resolution
                catalog = None

        self.catalog = catalog or CANONICAL_BRAND_CATALOG
        self.mfg_list = list({i["MANUFACTURER_NAME"] for i in self.catalog if i.get("MANUFACTURER_NAME")})
        self.brand_list = list({i["BRAND_NAME"] for i in self.catalog if i.get("BRAND_NAME")})

        self._by_mfg_key: Dict[str, Dict[str, str]] = {}
        self._by_brand_key: Dict[str, Dict[str, str]] = {}
        for item in self.catalog:
            self._by_mfg_key.setdefault(_norm(item.get("MANUFACTURER_NAME", "")), item)
            self._by_brand_key.setdefault(_norm(item.get("BRAND_NAME", "")), item)

    # -- helpers ---------------------------------------------------------

    def _token_similarity(self, s1: str, s2: str) -> float:
        if HAS_RAPIDFUZZ:
            return fuzz.token_sort_ratio(s1, s2) / 100.0
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _catalog_for_brand(self, brand: str) -> Optional[Dict[str, str]]:
        return self._by_brand_key.get(_norm(brand))

    def _mfg_for_brand(self, brand: str) -> str:
        item = self._catalog_for_brand(brand)
        return item["MANUFACTURER_NAME"] if item else ""

    # -- main entry point ------------------------------------------------

    def resolve_detailed(
        self,
        raw_mfg: Optional[str] = None,
        raw_desc: Optional[str] = None,
        mfg_part_num: Optional[str] = None,
        raw_brand: Optional[str] = None,
    ) -> BrandMatch:
        """Resolves brand/manufacturer and reports the evidence tier used."""
        cleaned_mfg = clean_supplier_name(raw_mfg) or ""
        cleaned_brand = clean_placeholder(raw_brand) or ""
        cleaned_desc = clean_part_description(raw_desc) or ""
        mpn = str(mfg_part_num or "").strip().upper()
        desc_lower = cleaned_desc.lower()
        mfg_lower = cleaned_mfg.lower()

        # ---- T1: supplier gave a brand and it matches the approved list ----
        if cleaned_brand:
            item = self._catalog_for_brand(cleaned_brand)
            if item:
                return BrandMatch(
                    item["MANUFACTURER_NAME"] or cleaned_mfg,
                    item["BRAND_NAME"],
                    TIER_EXPLICIT_BRAND,
                    1.0,
                    f"supplier brand field '{cleaned_brand}' matched approved list",
                )
            for cand in _alias_candidates(cleaned_brand):
                canonical = self._alias_map.get(cand)
                if canonical:
                    return BrandMatch(
                        self._mfg_for_brand(canonical) or cleaned_mfg,
                        canonical,
                        TIER_EXPLICIT_BRAND,
                        0.98,
                        f"supplier brand '{cleaned_brand}' -> alias '{cand}'",
                    )

        # ---- T2: manufacturer string matches the approved master exactly ----
        if cleaned_mfg:
            item = self._by_mfg_key.get(_norm(cleaned_mfg))
            if item:
                return BrandMatch(
                    item["MANUFACTURER_NAME"],
                    item["BRAND_NAME"] or item["MANUFACTURER_NAME"],
                    TIER_MFG_EXACT,
                    1.0,
                    f"manufacturer '{cleaned_mfg}' matched approved master",
                )

        # ---- T3: distributor/co-op + MPN prefix identifies the real maker ----
        # Runs before alias/fuzzy so a co-op name never masks the true brand.
        if cleaned_mfg:
            for dist_name, prefix_map in DISTRIBUTOR_OVERRIDE_MAP.items():
                if dist_name not in mfg_lower:
                    continue
                # Longest prefix first: "3MABR" must beat "3M".
                for prefix in sorted(prefix_map, key=len, reverse=True):
                    target = prefix_map[prefix]
                    if mpn.startswith(prefix) or prefix.lower() in desc_lower:
                        item = self._by_mfg_key.get(_norm(target))
                        if item:
                            return BrandMatch(
                                item["MANUFACTURER_NAME"],
                                item["BRAND_NAME"] or item["MANUFACTURER_NAME"],
                                TIER_DISTRIBUTOR,
                                0.95,
                                f"co-op '{cleaned_mfg}' + MPN prefix '{prefix}' -> {target}",
                            )

        # ---- T4: manufacturer alias after corporate-suffix stripping ----
        # Fixes "3 M Co" -> 3M™ and "Southwire/g Turner" -> Southwire®.
        if cleaned_mfg:
            for cand in _alias_candidates(cleaned_mfg):
                canonical = self._alias_map.get(cand)
                if canonical:
                    return BrandMatch(
                        self._mfg_for_brand(canonical) or cleaned_mfg,
                        canonical,
                        TIER_MFG_ALIAS,
                        0.94,
                        f"manufacturer '{cleaned_mfg}' -> alias '{cand}'",
                    )
                item = self._by_mfg_key.get(_norm(cand))
                if item:
                    return BrandMatch(
                        item["MANUFACTURER_NAME"],
                        item["BRAND_NAME"] or item["MANUFACTURER_NAME"],
                        TIER_MFG_ALIAS,
                        0.92,
                        f"manufacturer '{cleaned_mfg}' -> master '{cand}'",
                    )

        # ---- T5: fuzzy manufacturer match (weak) ----
        if cleaned_mfg and len(_norm(cleaned_mfg)) >= 4:
            best_item, best_score = None, 0.0
            for item in self.catalog:
                name = item.get("MANUFACTURER_NAME") or ""
                if not name:
                    continue
                score = self._token_similarity(cleaned_mfg, name)
                if score > best_score:
                    best_score, best_item = score, item
            if best_item and best_score >= self.FUZZY_THRESHOLD:
                return BrandMatch(
                    best_item["MANUFACTURER_NAME"],
                    best_item["BRAND_NAME"] or best_item["MANUFACTURER_NAME"],
                    TIER_MFG_FUZZY,
                    round(best_score, 3),
                    f"fuzzy manufacturer match {best_score:.2f} on '{cleaned_mfg}'",
                )

        # ---- T6: brand named in the DESCRIPTION (never the MPN) ----
        keyword_match = self._match_description_keyword(desc_lower)
        if keyword_match:
            brand, keyword, ambiguous = keyword_match
            item = self._catalog_for_brand(brand)
            return BrandMatch(
                (item["MANUFACTURER_NAME"] if item else "") or cleaned_mfg,
                brand,
                TIER_DESC_KEYWORD_AMBIGUOUS if ambiguous else TIER_DESC_KEYWORD,
                0.70 if ambiguous else 0.90,
                f"ambiguous description token '{keyword}' resolved by category context"
                if ambiguous
                else f"distinctive brand name '{keyword}' present in supplier description",
            )

        # ---- T7: unresolved ----
        # A distributor name is a supply-chain fact, not a brand: leave BRAND_NAME
        # blank rather than publish a co-op as if it were the maker.
        if cleaned_mfg:
            is_distributor = any(d in mfg_lower for d in KNOWN_DISTRIBUTORS)
            return BrandMatch(
                cleaned_mfg,
                "" if is_distributor else cleaned_mfg,
                TIER_UNRESOLVED,
                0.0,
                "distributor/co-op name is not a brand; left blank for review"
                if is_distributor
                else "no approved brand matched; manufacturer name used as brand",
            )

        return BrandMatch("", "", TIER_UNRESOLVED, 0.0, "no manufacturer or brand evidence")

    def _match_description_keyword(
        self, desc_lower: str
    ) -> Optional[Tuple[str, str, bool]]:
        """Finds a brand named in the description. Longest keyword wins.

        Returns ``(brand, keyword, is_ambiguous)``. Distinctive tokens are strong
        evidence; ambiguous ones are flagged so they stay in the review queue.
        """
        if not desc_lower:
            return None

        best: Optional[Tuple[str, str, bool]] = None
        best_len = 0

        for item in self.catalog:
            brand = item.get("BRAND_NAME") or ""
            for kw in item.get("KEYWORDS") or []:
                if len(kw) < self.MIN_KEYWORD_LEN:
                    continue
                if not re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                    continue
                if len(kw) > best_len:
                    best, best_len = (brand, kw, False), len(kw)

        # Ambiguous tokens need supporting context and must not be blocked.
        for kw, rule in AMBIGUOUS_KEYWORDS.items():
            if not re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                continue
            if any(b and b in desc_lower for b in rule.get("blocked_by") or ()):
                continue
            required = rule.get("requires") or ()
            if required and not any(r in desc_lower for r in required):
                continue
            if len(kw) > best_len:
                best, best_len = (rule["brand"], kw, True), len(kw)

        return best

    def resolve(
        self,
        raw_mfg: Optional[str] = None,
        raw_desc: Optional[str] = None,
        mfg_part_num: Optional[str] = None,
        raw_brand: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Backwards-compatible tuple form: ``(MANUFACTURER_NAME, BRAND_NAME)``."""
        match = self.resolve_detailed(
            raw_mfg=raw_mfg,
            raw_desc=raw_desc,
            mfg_part_num=mfg_part_num,
            raw_brand=raw_brand,
        )
        mfg = match.manufacturer_name or "Unknown Manufacturer"
        brand = match.brand_name or match.manufacturer_name or "Unknown Brand"
        return mfg, brand


# Global instance and helper for QA plan compatibility.
_default_resolver = BrandManufacturerResolver()


def resolve_brand_and_manufacturer(
    supplier_name: Optional[str] = None, desc_or_brand: Optional[str] = None
) -> Dict[str, str]:
    """Helper matching the FuMA QA plan signature."""
    mfg, brand = _default_resolver.resolve(
        raw_mfg=supplier_name,
        raw_desc=desc_or_brand,
        raw_brand=desc_or_brand,
    )
    return {"manufacturer_name": mfg, "brand_name": brand}
