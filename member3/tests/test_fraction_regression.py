"""
Regression test suite for numeric fraction preservation, dimension grammar,
and anti-fabrication constraints in FuMA Engine (Member 2).
"""
import pytest
from fuma_engine.attribute_extractor import extract_attributes
from fuma_engine.description_builder import (
    build_mobile_desc,
    build_marketing_description,
    synthesize_features,
)
from fuma_engine.sourcing_engine import build_provenance_urls


def test_fraction_and_compound_dimension_preservation():
    """Verify that fractions like 1/2, 3/8, 5/16, 1-1/4, 0.375, 0.5 preserve complete tokens."""
    # Case 1: 1/2"x18" Sanding Belt
    r1 = extract_attributes("Diablo 1/2\"x18\" Sanding Belt", "DCB518", category="Sanding Belt")
    w = next((a for a in r1["attributes"] if a.label == "Width"), None)
    l = next((a for a in r1["attributes"] if a.label == "Length"), None)
    assert w is not None, "Width attribute not extracted"
    assert w.value == "1/2", f"Expected '1/2', got {w.value!r} (must not be parsed as 2)"
    assert w.uom == "in"
    assert l is not None
    assert l.value == "18"
    assert l.uom == "in"

    # Case 2: 3/8" Pipe Fitting
    r2 = extract_attributes("3/8 CPLG BRS 150# FNPT Coupling", "CPLG-38", category="Pipe Fitting")
    sz2 = next((a for a in r2["attributes"] if "Size" in a.label or "Diameter" in a.label), None)
    assert sz2 is not None
    assert sz2.value == "3/8"
    assert sz2.uom == "in"

    # Case 3: 5/16" Dimension
    r3 = extract_attributes("Steel Rod 5/16\" x 36\"", "ROD-516", category="Steel Rod")
    w3 = next((a for a in r3["attributes"] if a.label == "Width" or "Diameter" in a.label), None)
    assert w3 is not None
    assert w3.value == "5/16"
    assert w3.uom == "in"

    # Case 4: 1-1/4" Mixed Fraction
    r4 = extract_attributes("Oliver Shaper 1-1/4 Spindle", "10047VS", category="Woodworking Shaper")
    sz4 = next((a for a in r4["attributes"] if "Size" in a.label or "Diameter" in a.label or "Arbor" in a.label), None)
    assert sz4 is not None
    assert sz4.value == "1-1/4"
    assert sz4.uom == "in"

    # Case 5: 0.375" and 0.5" Decimals
    r5 = extract_attributes("Precision Pin 0.375\" x 2.5\"", "PIN-375", category="Hardware Pin")
    w5 = next((a for a in r5["attributes"] if a.label == "Width" or "Diameter" in a.label), None)
    assert w5 is not None
    assert w5.value == "0.375"
    assert w5.uom == "in"

    r6 = extract_attributes("Precision Bushing 0.5\" ID", "BSH-05", category="Bushing")
    sz6 = next((a for a in r6["attributes"] if "Size" in a.label or "Diameter" in a.label), None)
    assert sz6 is not None
    assert sz6.value == "0.5"
    assert sz6.uom == "in"


def test_no_heavy_duty_or_fabricated_filler():
    """Verify that description_builder never injects fabricated filler words like 'Heavy Duty'."""
    attrs = {"attributes": [], "dimensions": {}, "series": ""}
    
    # Short description context that is < 60 characters
    mobile = build_mobile_desc("NIBCO", "NIBCO", "123", "Cap", attrs, classpath="Plumbing > Pipe Fittings")
    assert "Heavy Duty" not in mobile, "Heavy Duty must never be appended as artificial filler"
    assert "Premium" not in mobile
    assert "High Performance" not in mobile
    assert "Superior" not in mobile


def test_grounded_features_only():
    """Verify that synthesize_features emits only verified extracted specs and does not invent filler."""
    extracted = extract_attributes("PDSH4816AF Dishwasher SS 120V 15A 5-Wash Cycle", "PDSH4816AF", category="Dishwasher")
    features = synthesize_features("Frigidaire", "Frigidaire", "PDSH4816AF", "Dishwasher", extracted, "Appliances > Built-In Dishwashers")
    
    # Should only contain verified features
    assert any("Stainless Steel" in f for f in features)
    assert any("120 V" in f for f in features)
    assert any("15 A" in f for f in features)
    assert any("5 wash cycles" in f for f in features)
    
    # Must NOT contain boilerplate filler pads
    assert not any("Engineered by" in f for f in features)
    assert not any("Backed by" in f for f in features)
    assert not any("Ideal choice for professional" in f for f in features)


def test_verified_sourcing_never_emits_search_engines():
    """Verify that sourcing_engine never emits google.com or bing.com query URLs."""
    # Unknown manufacturer should return blank
    u1 = build_provenance_urls("Unknown Random Mfg Co", "XYZ-999")
    assert u1["mfr_url"] == ""
    assert u1["ref_urls"] == []
    assert "google.com" not in u1["mfr_url"]
    
    # Known manufacturer should produce verified first-party domain
    u2 = build_provenance_urls("Milwaukee Accessory (4031)", "48-22-9483")
    assert "milwaukeetool.com" in u2["mfr_url"]
    assert "google.com" not in u2["mfr_url"]
    assert all("google.com" not in r for r in u2["ref_urls"])
    assert all("amazon." not in r for r in u2["ref_urls"])
