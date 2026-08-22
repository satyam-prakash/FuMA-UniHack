"""
Canonical enriched-record schema.
Owned by Member 2.

The Pydantic model is the contract between the engines and Member 3's delivery
mapper: if a field is not declared here it cannot reach the 252-column file.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AttributeItem(BaseModel):
    """One structured attribute, with Value and UOM strictly separated.

    ``evidence`` records where the attribute came from:
        ``"evidence"`` -- parsed from the supplier's own description/MPN
        ``"inferred"`` -- derived from the taxonomy we assigned
    Reporting these separately is what stops "100% attribute coverage" from
    being a tautology (the pipeline guarantees >= 1 attribute per classified row).
    """

    label: str
    value: str
    uom: Optional[str] = ""
    evidence: str = "evidence"


class ProductRecord(BaseModel):
    # Base input & Member 1 fields
    mfg_part_num: str
    part_desc_raw: str
    manufacturer_name: str
    brand_name: str
    series: Optional[str] = ""

    # Member 2: Classification & Taxonomy
    classpath: str
    unspsc: Optional[str] = ""
    product_name: str

    # Member 2: Extracted Attributes & Features
    attributes: List[AttributeItem] = []
    features: List[str] = []

    # Member 2: 5 Multichannel Descriptions
    invoice_desc: str = Field(..., max_length=40, description="Invoice Description, max 40 chars, ALL CAPS")
    mobile_desc: str = Field(..., max_length=85, description="Mobile Description, 60-80 chars")
    short_desc: str = Field(..., description="Product Title / Short Description formula")
    long_desc1: str = Field(..., description="Complete spec chain description")
    retail_desc: str = Field(..., description="Retail / Marketing summary")

    # Member 2: Grounded B2B marketing copy (2-sentence professional summary)
    marketing_description: str = ""

    # Member 2: Manufacturer provenance & reference URLs.
    # Blank when no first-party source can be verified -- deliberately not
    # backfilled with a marketplace or search-engine link.
    mfr_url: str = ""
    ref_urls: List[str] = []

    # Member 2: Digital assets. Populated only where a verified naming
    # convention exists; otherwise blank rather than a guessed filename.
    product_image: str = ""

    # Member 2: Quality & Confidence Scoring
    confidence_score: float = 100.0
    needs_review: bool = False
    review_reasons: List[str] = []

    #: Evidence tier behind the brand decision (see fuma_rules.brand_matcher).
    #: Weak tiers are capped below the review threshold rather than published.
    brand_match_tier: str = ""

    #: Share of emitted values found in the approved LOV, or None when no LOV
    #: file is loaded. None is reported as "not measurable", never as 0%.
    lov_compliance: Optional[float] = None

    #: De-duplication result. Duplicates are flagged, never deleted, so the
    #: delivery file still reconciles with the client's input.
    is_duplicate: bool = False
    duplicate_of: Optional[int] = None

    def attribute_provenance(self) -> Dict[str, Any]:
        """Three-tier attribute breakdown for honest KPI reporting."""
        total = len(self.attributes)
        evidence = sum(1 for a in self.attributes if a.evidence == "evidence")
        return {
            "total": total,
            "evidence_backed": evidence,
            "inferred": total - evidence,
            "evidence_ratio": round(evidence / total, 4) if total else 0.0,
        }
