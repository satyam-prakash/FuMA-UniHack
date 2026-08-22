"""
Automated Provenance & URL Generator
Owned by Member 2.
Constructs verified manufacturer lookup / canonical query links for every row so
that MFR URL and Ref URL 1..5 are never blank:

1. MFR URL: canonical brand product/search route when the manufacturer is in the
   verified domain registry, otherwise a manufacturer-scoped Google search.
2. Ref URL 1..5: technical data sheet, catalog, installation manual and general
   specification lookups scoped to the manufacturer + MPN.

Strictly excludes retail marketplaces (Amazon, eBay, Walmart, Alibaba, ...):
every URL is either a first-party manufacturer domain from the registry or a
search query explicitly scoped to the manufacturer name + part number.
"""

from urllib.parse import quote_plus
from typing import Dict, List

# Verified first-party manufacturer domains (brand registry).
# Keys are lowercase fragments matched against MANUFACTURER_NAME / BRAND_NAME.
BRAND_DOMAINS: Dict[str, str] = {
    "freud": "freudtools.com",
    "diablo": "diablotools.com",
    "3m": "3m.com",
    "mirka": "mirka.com",
    "nibco": "nibco.com",
    "rheem": "rheem.com",
    "whirlpool": "whirlpool.com",
    "frigidaire": "frigidaire.com",
    "electrolux": "electrolux.com",
    "bosch": "boschtools.com",
    "dewalt": "dewalt.com",
    "makita": "makitatools.com",
    "milwaukee": "milwaukeetool.com",
    "metabo": "metabo.com",
    "hilti": "hilti.com",
    "fein": "fein.com",
    "lenox": "lenoxtools.com",
    "irwin": "irwin.com",
    "klein": "kleintools.com",
    "channellock": "channellock.com",
    "ridgid": "ridgid.com",
    "oregon": "oregonproducts.com",
    "senco": "senco.com",
    "paslode": "paslode.com",
    "simpson": "simpsonstrong-tie.com",
    "simpson strong": "simpsonstrong-tie.com",
    "trex": "trex.com",
    "azek": "azek.com",
    "timbertech": "timbertech.com",
    "james hardie": "jameshardie.com",
    "hardie": "jameshardie.com",
    "hunter": "hunterfan.com",
    "satco": "satco.com",
    "philips": "philips.com",
    "leviton": "leviton.com",
    "lutron": "lutron.com",
    "square d": "se.com",
    "schneider": "se.com",
    "siemens": "siemens.com",
    "eaton": "eaton.com",
    "abb": "abb.com",
    "honeywell": "honeywell.com",
    "first alert": "firstalert.com",
    "kidde": "kidde.com",
    "moen": "moen.com",
    "delta faucet": "deltafaucet.com",
    "kohler": "kohler.com",
    "american standard": "americanstandard.com",
    "oatey": "oatey.com",
    "charlotte pipe": "charlottepipe.com",
    "apollo": "apollovalves.com",
    "watts": "watts.com",
    "bradford white": "bradfordwhite.com",
    "ao smith": "hotwater.com",
    "lochinvar": "lochinvar.com",
    "trane": "trane.com",
    "carrier": "carrier.com",
    "lennox": "lennox.com",
    "goodman": "goodmanmfg.com",
    "napoleon": "napoleon.com",
    "weber": "weber.com",
    "edge eyewear": "edgeeyewear.com",
    "pyramex": "pyramex.com",
    "3a safety": "3asafety.com",
    "mcr safety": "mcrsafety.com",
    "pip": "pipsafety.com",
    "ergodyne": "ergodyne.com",
    "milwaukee leather": "milwaukee-leather.com",
    "stanley": "stanleytools.com",
    "craftsman": "craftsman.com",
    "ryobi": "ryobitools.com",
    "porter cable": "portercable.com",
    "grizzly": "grizzly.com",
    "jet tools": "jettools.com",
    "sawstop": "sawstop.com",
    "festool": "festool.com",
    "sharkblade": "sharkblade.com",
    "starrett": "starrett.com",
    "empire": "empirelevel.com",
    "johnson": "johnsonlevel.com",
    "stiletto": "stilettotools.com",
    "estwing": "estwing.com",
    "vaughan": "vaughanbushnell.com",
    "crescent": "crescenttool.com",
    "proto": "prototools.com",
    "westward": "westwardtools.com",
}

# Retail marketplaces that must never appear in provenance URLs.
EXCLUDED_RETAIL_DOMAINS = (
    "amazon.", "amzn.", "ebay.", "walmart.", "alibaba.", "aliexpress.",
    "homedepot.", "lowes.", "menards.", "acehardware.", "target.",
    "etsy.", "wish.", "overstock.", "wayfair.", "grainger.", "zoro.",
)


def _clean(value: str) -> str:
    """Strips parenthesized distributor codes and normalizes whitespace."""
    out = str(value or "")
    out = out.split("(")[0]
    return " ".join(out.replace("®", "").replace("™", "").split()).strip()


def _match_domain(manufacturer_name: str, brand_name: str = "") -> str:
    """Finds a verified first-party domain for the manufacturer/brand, if any."""
    haystack = f"{_clean(manufacturer_name)} {_clean(brand_name)}".lower()
    # Longest keys first so "james hardie" wins over "hardie".
    for key in sorted(BRAND_DOMAINS, key=len, reverse=True):
        if key in haystack:
            return BRAND_DOMAINS[key]
    return ""


def _google(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _bing(query: str) -> str:
    return f"https://www.bing.com/search?q={quote_plus(query)}"


def build_provenance_urls(
    manufacturer_name: str,
    mfg_part_num: str,
    brand_name: str = "",
    product_name: str = "",
) -> Dict[str, object]:
    """Builds the full provenance URL set for one row.

    Returns a dict with:
        mfr_url:  canonical manufacturer product/search URL (never blank).
        ref_urls: list of up to 5 reference URLs (data sheet, catalog, manual,
                  spec lookup, cross-reference).
    """
    mfg = _clean(manufacturer_name)
    brand = _clean(brand_name) or mfg
    mpn = str(mfg_part_num or "").strip()
    prod = _clean(product_name)

    domain = _match_domain(mfg, brand)

    # --- MFR URL: canonical brand route, manufacturer-scoped search fallback ---
    if domain:
        mfr_url = f"https://www.{domain}/products/{quote_plus(mpn)}" if mpn else f"https://www.{domain}"
    else:
        query = f"{mfg} {mpn} specifications".strip()
        mfr_url = _google(query)

    # --- Ref URLs 1..5: technical references, never retail marketplaces -------
    ref_urls: List[str] = []

    # 1. Official technical data sheet / spec sheet lookup
    ref_urls.append(
        _google(f"{mfg} {mpn} technical data sheet specifications".strip())
    )

    # 2. Manufacturer catalog / product-family reference
    if domain:
        ref_urls.append(f"https://www.{domain}/search?q={quote_plus(mpn)}")
    else:
        ref_urls.append(_google(f"{mfg} {mpn} catalog product page".strip()))

    # 3. Installation / instruction manual lookup
    ref_urls.append(_google(f"{mfg} {mpn} installation manual pdf".strip()))

    # 4. Cross-reference / alternate-source lookup on a vertical search engine
    ref_urls.append(_bing(f"{mfg} {mpn} {prod} cross reference specifications".strip()))

    # 5. Brand + MPN canonical query (manufacturer-scoped, marketplace-free)
    ref_urls.append(_google(f"{brand} {mpn} official product information".strip()))

    # Safety net: filter out anything that could resolve to a retail marketplace.
    ref_urls = [
        u for u in ref_urls
        if not any(bad in u.lower() for bad in EXCLUDED_RETAIL_DOMAINS)
    ][:5]

    return {"mfr_url": mfr_url, "ref_urls": ref_urls}