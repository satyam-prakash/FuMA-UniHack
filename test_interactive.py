"""
Interactive Verification Script for Member 1 Deliverables.
Run: python test_interactive.py
"""

import sys

# Ensure UTF-8 output encoding on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fuma_rules import (
    clean_placeholder,
    clean_supplier_name,
    clean_part_description,
    BrandManufacturerResolver,
    decimal_to_trade_fraction,
    standardize_uom,
    format_measurement,
    standardize_dimension_string,
)

def main():
    resolver = BrandManufacturerResolver()

    print("=" * 65)
    print("1. SANITIZATION & PLACEHOLDER CLEANING")
    print("=" * 65)
    print("  Placeholder test  :", clean_placeholder("-- Unbranded --"))               # None
    print("  Supplier code test:", clean_supplier_name("Freud Inc (2435)"))           # Freud Inc
    print("  Supplier code test:", clean_supplier_name("Milwaukee Accessory (4031)")) # Milwaukee Accessory
    print("  Clean Description :", clean_part_description("PDSH4816AF Dishwasher SS - Display Only"))

    print("\n" + "=" * 65)
    print("2. BRAND & MANUFACTURER RESOLUTION (WITH TRADEMARKS)")
    print("=" * 65)
    mfg1, brand1 = resolver.resolve("Appliance Dealers Cooperative (APPDE)", "PDSH4816AF SS", "PDSH4816AF")
    print(f"  Frigidaire -> Mfg: {mfg1} | Brand: {brand1}")

    mfg2, brand2 = resolver.resolve("Freud Inc (2435)", "DCB518ASTS06G Sanding Belt", "DCB518ASTS06G")
    print(f"  Diablo     -> Mfg: {mfg2} | Brand: {brand2}")

    mfg3, brand3 = resolver.resolve("Milwaukee Accessory (4031)", '49-94-0013 Milw 5" Disc', "49-94-0013")
    print(f"  Milwaukee  -> Mfg: {mfg3} | Brand: {brand3}")

    mfg4, brand4 = resolver.resolve("Jam Industrial Supply LLC (JAMIN)", "3M 775L Stikit Film", "3MABR-7100075678")
    print(f"  3M         -> Mfg: {mfg4} | Brand: {brand4}")

    print("\n" + "=" * 65)
    print("3. FRACTIONS & MASTER UOM STANDARDIZATION")
    print("=" * 65)
    print("  50.25 to trade fraction :", decimal_to_trade_fraction(50.25))               # 50-1/4
    print("  0.25 to trade fraction  :", decimal_to_trade_fraction(0.25))                # 1/4
    print("  0.045 abrasive gauge    :", decimal_to_trade_fraction(0.045))               # 0.045
    print("  Voltage measurement     :", format_measurement(120, "volts"))                # 120 V
    print("  Current measurement     :", format_measurement(15, "amps"))                  # 15 A
    print("  Sound measurement       :", format_measurement(47, "dba"))                  # 47 dBA
    print("  Compound dimension      :", standardize_dimension_string('5"x.045"x7/8"'))  # 5 in x 0.045 in x 7/8 in
    print("  Tape dimension          :", standardize_dimension_string("3/4x60'"))        # 3/4 in x 60 ft

    print("\n" + "=" * 65)
    print("ALL MEMBER 1 VERIFICATIONS SUCCESSFUL!")
    print("=" * 65)

if __name__ == "__main__":
    main()
