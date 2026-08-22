"""
Maps an enriched ProductRecord onto the locked 252-column delivery row.

Owned by Member 3. Every row starts as 252 blank strings and is filled in
place, so the output can never gain or lose a column no matter how many
attributes or features the engine extracted.
"""

from typing import Any, Dict, List, Mapping, Tuple

from member3.delivery.columns import ATTRIBUTE_SLOTS, DELIVERY_COLUMNS

#: Feature slots the delivery format provides (ITEM_FEATURES_1..20).
FEATURE_SLOTS = 20

#: Columns copied straight from the raw upload row under the same name.
PASSTHROUGH_COLUMNS = (
    "PART_NUMBER",
    "Dept",
    "Class",
    "Fine",
    "SKU - MY_PART_NUMBER",
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
)

#: Delivery column -> ProductRecord field.
ENRICHED_COLUMNS = {
    "MANUFACTURER_NAME": "manufacturer_name",
    "BRAND_NAME": "brand_name",
    "MANUFACTURER_PART_NUMBER": "mfg_part_num",
    "Classpath": "classpath",
    "MOBILE_DESC": "mobile_desc",
    "INVOICE_DESC": "invoice_desc",
    "SHORT_DESC": "short_desc",
    "LONG_DESC1": "long_desc1",
    "RETAIL_DESC": "retail_desc",
    "MARKETING_DESCRIPTION": "marketing_description",
    "MFR URL": "mfr_url",
    "Product Name": "product_name",
    "UNSPSC": "unspsc",
    # Digital asset, derived from the verified BRAND_MPN.jpg convention seen in
    # the delivery ground truth. Blank when the brand is unresolved.
    "Product Image": "product_image",
}


#: Ref URL slots the delivery format provides (Ref URL 1..5).
REF_URL_SLOTS = 5


def _s(value: Any) -> str:
    """Coerces a cell to a plain string; None/NaN become blank, never a placeholder."""
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def map_record_to_delivery(
    enriched: Mapping[str, Any], raw: Mapping[str, Any]
) -> Tuple[Dict[str, str], List[str]]:
    """Builds one delivery row from an enriched record plus its original CSV row.

    `enriched` is ``ProductRecord.model_dump()``, `raw` the upload row. Returns
    (row, warnings): the row always has exactly the 252 DELIVERY_COLUMNS keys in
    order with string values, and warnings reports data dropped because the
    fixed format has no slot for it. Columns with no source stay blank.
    """
    row: Dict[str, str] = {column: "" for column in DELIVERY_COLUMNS}
    warnings: List[str] = []

    for column in PASSTHROUGH_COLUMNS:
        row[column] = _s(raw.get(column))

    for column, field in ENRICHED_COLUMNS.items():
        row[column] = _s(enriched.get(field))

    ref_urls = list(enriched.get("ref_urls") or [])
    for slot, url in enumerate(ref_urls[:REF_URL_SLOTS], start=1):
        row[f"Ref URL {slot}"] = _s(url)

    features = list(enriched.get("features") or [])
    if len(features) > FEATURE_SLOTS:
        warnings.append(
            f"feature overflow: {len(features)} features extracted, "
            f"only first {FEATURE_SLOTS} exported"
        )
    for slot, feature in enumerate(features[:FEATURE_SLOTS], start=1):
        row[f"ITEM_FEATURES_{slot}"] = _s(feature)

    attributes = list(enriched.get("attributes") or [])
    if len(attributes) > ATTRIBUTE_SLOTS:
        warnings.append(
            f"attribute overflow: {len(attributes)} attributes extracted, "
            f"only first {ATTRIBUTE_SLOTS} exported"
        )
    for slot, attribute in enumerate(attributes[:ATTRIBUTE_SLOTS], start=1):
        row[f"ATTRIBUTE_LABEL {slot}"] = _s(attribute.get("label"))
        row[f"ATTRIBUTE_VALUE {slot}"] = _s(attribute.get("value"))
        row[f"ATTRIBUTE_UOM {slot}"] = _s(attribute.get("uom"))

    return row, warnings
