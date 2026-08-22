from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class AttributeItem(BaseModel):
    label: str
    value: str
    uom: Optional[str] = ""

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
    
    # Member 2: Manufacturer provenance & reference URLs (never blank)
    mfr_url: str = ""
    ref_urls: List[str] = []
    
    # Member 2: Quality & Confidence Scoring
    confidence_score: float = 100.0
    needs_review: bool = False
    review_reasons: List[str] = []
