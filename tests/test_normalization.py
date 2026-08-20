"""
Unit tests for Member 1: Master Data, Normalization & Evaluation Engine.
"""

import pytest
from fuma_rules import (
    clean_placeholder,
    clean_supplier_name,
    clean_part_description,
    BrandManufacturerResolver,
    decimal_to_trade_fraction,
    standardize_uom,
    format_measurement,
    standardize_dimension_string,
    GroundTruthBenchmark,
    MasterDataPipelineStage,
)


class TestSanitizer:
    def test_clean_placeholder(self):
        assert clean_placeholder("-- Unbranded --") is None
        assert clean_placeholder("-- No Unilog Brand --") is None
        assert clean_placeholder("-- No DIB Brand --") is None
        assert clean_placeholder("N/A") is None
        assert clean_placeholder("") is None
        assert clean_placeholder(None) is None
        assert clean_placeholder("3M") == "3M"

    def test_clean_supplier_name(self):
        assert clean_supplier_name("Freud Inc (2435)") == "Freud Inc"
        assert clean_supplier_name("Jam Industrial Supply LLC (JAMIN)") == "Jam Industrial Supply LLC"
        assert clean_supplier_name("Milwaukee Accessory (4031)") == "Milwaukee Accessory"
        assert clean_supplier_name("3 M Co (5293)") == "3 M Co"
        assert clean_supplier_name("-- Unbranded --") is None

    def test_clean_part_description(self):
        assert clean_part_description("PDSH4816AF Dishwasher SS - Display Only") == "PDSH4816AF Dishwasher SS"
        assert clean_part_description('49-94-0013 Milw 5""x.045""x7/8"" Metal Cut Off Disc') == '49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc'


class TestBrandMatcher:
    def setup_method(self):
        self.resolver = BrandManufacturerResolver()

    def test_resolve_frigidaire(self):
        mfg, brand = self.resolver.resolve(
            raw_mfg="Appliance Dealers Cooperative (APPDE)",
            raw_desc="PDSH4816AF Dishwasher SS - Display Only",
            mfg_part_num="PDSH4816AF"
        )
        assert mfg == "Rheem Manufacturing"
        assert brand == "FRIGIDAIRE®"

    def test_resolve_whirlpool(self):
        mfg, brand = self.resolver.resolve(
            raw_mfg="Appliance Dealers Cooperative (APPDE)",
            raw_desc="WDTS7024RZ Dishwasher SS - Display Only",
            mfg_part_num="WDTS7024RZ"
        )
        assert mfg == "Whirlpool Corporation"
        assert brand == "Whirlpool®"

    def test_resolve_diablo(self):
        mfg, brand = self.resolver.resolve(
            raw_mfg="Freud Inc (2435)",
            raw_desc="DCB518ASTS06G Diablo 1/2\"x18\" - Sanding Belt 6pc",
            mfg_part_num="DCB518ASTS06G"
        )
        assert mfg == "Freud America, Inc."
        assert brand == "Diablo®"

    def test_resolve_milwaukee(self):
        mfg, brand = self.resolver.resolve(
            raw_mfg="Milwaukee Accessory (4031)",
            raw_desc="49-94-0013 Milw 5\"x.045\"x7/8\" Metal Cut Off Disc",
            mfg_part_num="49-94-0013"
        )
        assert mfg == "Milwaukee Electric Tool Corporation"
        assert brand == "Milwaukee®"

    def test_resolve_3m(self):
        mfg, brand = self.resolver.resolve(
            raw_mfg="Jam Industrial Supply LLC (JAMIN)",
            raw_desc="3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box",
            mfg_part_num="3MABR-7100075678"
        )
        assert mfg == "3M"
        assert brand == "3M™"


class TestUOMAndFraction:
    def test_decimal_to_fraction(self):
        assert decimal_to_trade_fraction(50.25) == "50-1/4"
        assert decimal_to_trade_fraction(0.25) == "1/4"
        assert decimal_to_trade_fraction(0.5) == "1/2"
        assert decimal_to_trade_fraction(24.0) == "24"
        assert decimal_to_trade_fraction("6.5") == "6-1/2"
        assert decimal_to_trade_fraction(0.045) == "0.045"

    def test_standardize_uom(self):
        assert standardize_uom("inches") == "in"
        assert standardize_uom("IN.") == "in"
        assert standardize_uom("volts") == "V"
        assert standardize_uom("amps") == "A"
        assert standardize_uom("dba") == "dBA"
        assert standardize_uom("lbs") == "lb"

    def test_format_measurement(self):
        assert format_measurement(50.25, "in") == "50-1/4 in"
        assert format_measurement(24, "in") == "24 in"
        assert format_measurement(120, "volts") == "120 V"
        assert format_measurement(15, "amps") == "15 A"
        assert format_measurement(47, "dba") == "47 dBA"

    def test_standardize_dimension_string(self):
        assert standardize_dimension_string('5"x.045"x7/8"') == "5 in x .045 in x 7/8 in"
        assert standardize_dimension_string("3/4x60'") == "3/4 in x 60 ft"


class TestPipelineStage1:
    def test_stage1_processing(self):
        stage = MasterDataPipelineStage()
        raw_row = {
            "Mfg_Part_Num": "PDSH4816AF",
            "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
            "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
            "Unilog_Brand": "-- No Unilog Brand --"
        }
        result = stage.process_item(raw_row)
        assert result["MANUFACTURER_NAME"] == "Rheem Manufacturing"
        assert result["BRAND_NAME"] == "FRIGIDAIRE®"
        assert result["CLEAN_DESC"] == "PDSH4816AF Dishwasher SS"
        assert result["STAGE1_STATUS"] == "NORMALIZED"
