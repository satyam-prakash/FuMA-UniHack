"""
Delivery column contract for the FuMA 252-column export.

Owned by Member 3. Generated verbatim from
``member3/data/expected_delivery_format.csv`` (the client-supplied expected
output). Treat this module as a versioned contract: nothing here may be
reordered, renamed or extended without regenerating from that reference file.
"""

from typing import List

ATTRIBUTE_SLOTS = 50

#: Columns that precede the fixed attribute block.
LEADING_COLUMNS: List[str] = [
    'MFR URL',
    'Ref URL 1',
    'Ref URL 2',
    'Ref URL 3',
    'Ref URL 4',
    'Ref URL 5',
    'PART_NUMBER',
    'Dept',
    'Class',
    'Fine',
    'SKU - MY_PART_NUMBER',
    'Mfg_Part_Num',
    'Part_Desc',
    'E1_Brand',
    'Unilog_Brand',
    'DIB_Brand',
    'Part_Manuf',
    'MANUFACTURER_NAME',
    'BRAND_NAME',
    'TRADE_NAME',
    'MANUFACTURER_PART_NUMBER',
    'ALTERNATE_PART_NUMBER',
    'Classpath',
    'MOBILE_DESC',
    'INVOICE_DESC',
    'SHORT_DESC',
    'LONG_DESC1',
    'RETAIL_DESC',
    'MARKETING_DESCRIPTION',
    'ITEM_FEATURES_1',
    'ITEM_FEATURES_2',
    'ITEM_FEATURES_3',
    'ITEM_FEATURES_4',
    'ITEM_FEATURES_5',
    'ITEM_FEATURES_6',
    'ITEM_FEATURES_7',
    'ITEM_FEATURES_8',
    'ITEM_FEATURES_9',
    'ITEM_FEATURES_10',
    'ITEM_FEATURES_11',
    'ITEM_FEATURES_12',
    'ITEM_FEATURES_13',
    'ITEM_FEATURES_14',
    'ITEM_FEATURES_15',
    'ITEM_FEATURES_16',
    'ITEM_FEATURES_17',
    'ITEM_FEATURES_18',
    'ITEM_FEATURES_19',
    'ITEM_FEATURES_20',
    'With',
    'Standard/Approvals',
    'Prop 65',
    'Application',
    'Includes',
    'Product Name',
]

#: Columns that follow the fixed attribute block.
TRAILING_COLUMNS: List[str] = [
    'UPC',
    'EAN',
    'GTIN',
    'UNSPSC',
    'Warranty',
    'List Price',
    'Selling Qty',
    'Selling UOM',
    'Standard Packaging Information',
    'LENGTH',
    'LENGTH_UOM',
    'HEIGHT',
    'HEIGHT_UOM',
    'WIDTH',
    'WIDTH_UOM',
    'WEIGHT',
    'WEIGHT_UOM',
    'VOLUME',
    'VOLUME_UOM',
    'Product Image',
    'Alternate Image 1',
    'Alternate Image 2',
    'Alternate Image 3',
    'Alternate Image 4',
    'SDS',
    'SDS_1',
    'Warranty Information',
    'Catalog',
    'Specification Sheet',
    'Instruction/Installation Manual',
    'Service Manual',
    'Owners/User Manual',
    'Line Drawing',
    'MTR',
    'RoHS',
    'Full Engineering Drawing',
    'Energy Star Guide',
    'Technical Bulletin',
    'Submittal',
    'Compatibility Chart',
    'Size Chart',
    'Product Label/Insert',
    'Video Link',
    'Video Link 1',
    'Country Of Origin',
    'Discontinued',
    'Actual Image (Yes/No)',
]


def _attribute_columns() -> List[str]:
    """Builds the fixed ``ATTRIBUTE_LABEL/VALUE/UOM n`` triplets, n = 1..50."""
    cols: List[str] = []
    for slot in range(1, ATTRIBUTE_SLOTS + 1):
        cols.append(f"ATTRIBUTE_LABEL {slot}")
        cols.append(f"ATTRIBUTE_VALUE {slot}")
        cols.append(f"ATTRIBUTE_UOM {slot}")
    return cols


#: The exact 252 delivery headers, in the exact required order.
DELIVERY_COLUMNS: List[str] = LEADING_COLUMNS + _attribute_columns() + TRAILING_COLUMNS

DELIVERY_COLUMN_COUNT = 252

assert len(DELIVERY_COLUMNS) == DELIVERY_COLUMN_COUNT, (
    f"delivery contract broken: {len(DELIVERY_COLUMNS)} columns"
)
assert len(set(DELIVERY_COLUMNS)) == DELIVERY_COLUMN_COUNT, "duplicate delivery header"
