"""
QA & Verification Suite for Member 1 according to FuMA_Verification_and_QA_Plan.md.
"""

import pytest
from fuma_rules import (
    resolve_brand_and_manufacturer,
    convert_decimal_to_fraction,
    normalize_uom,
    clean_placeholder,
    clean_supplier_name,
)


def test_brand_matcher_qa():
    # 1. Test noisy supplier string resolution with legal trademarks
    res1 = resolve_brand_and_manufacturer("Freud Inc (2435)", "Freud")
    assert "®" in res1["brand_name"] or "Freud" in res1["brand_name"]
    assert res1["brand_name"] == "Diablo®"
    assert res1["manufacturer_name"] == "Freud America, Inc."

    # 2. Test cooperative/distributor string mapping to canonical brand
    res2 = resolve_brand_and_manufacturer("Appliance Dealers Cooperative (APPDE)", "PDSH4816AF")
    assert res2["brand_name"] == "FRIGIDAIRE®"
    assert res2["manufacturer_name"] == "Rheem Manufacturing"

    # 3. Test Whirlpool co-op resolution
    res3 = resolve_brand_and_manufacturer("Appliance Dealers Cooperative (APPDE)", "WDTS7024RZ")
    assert res3["brand_name"] == "Whirlpool®"
    assert res3["manufacturer_name"] == "Whirlpool Corporation"

    # 4. Test Milwaukee resolution
    res4 = resolve_brand_and_manufacturer("Milwaukee Accessory (4031)", "49-94-0013")
    assert res4["brand_name"] == "Milwaukee®"
    assert res4["manufacturer_name"] == "Milwaukee Electric Tool Corporation"

    # 5. Test 3M resolution
    res5 = resolve_brand_and_manufacturer("Jam Industrial Supply LLC (JAMIN)", "3M 775L Stikit Film")
    assert res5["brand_name"] == "3M™"
    assert res5["manufacturer_name"] == "3M"


def test_placeholder_sanitization_qa():
    assert clean_placeholder("-- Unbranded --") is None
    assert clean_placeholder("-- No DIB Brand --") is None
    assert clean_placeholder("-- No Unilog Brand --") is None
    assert clean_placeholder("N/A") is None
    assert clean_supplier_name("Freud Inc (2435)") == "Freud Inc"
    assert clean_supplier_name("Milwaukee Accessory (4031)") == "Milwaukee Accessory"


def test_decimal_to_fraction_qa():
    assert convert_decimal_to_fraction(50.25) == "50-1/4"
    assert convert_decimal_to_fraction(0.5) == "1/2"
    assert convert_decimal_to_fraction(0.25) == "1/4"
    assert convert_decimal_to_fraction(24.0) == "24"
    assert convert_decimal_to_fraction(0.045) in [".045", "0.045"]


def test_uom_normalizer_qa():
    assert normalize_uom("24in") == "24 in"
    assert normalize_uom("120v") == "120 V"
    assert normalize_uom("47dba") == "47 dBA"
    assert normalize_uom("1.5GPM") == "1.5 gpm"
    assert normalize_uom("15amps") == "15 A"
