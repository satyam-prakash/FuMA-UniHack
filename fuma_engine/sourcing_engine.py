"""
Verified Manufacturer Provenance & URL Generator
Owned by Member 2.

Provides manufacturer provenance URLs following strict verification rules:

1. MFR URL: Only the verified manufacturer homepage (never a fabricated
   product-specific URL unless the pattern is verified).
2. Ref URL 1..5: Only populated with verified catalog/search patterns for
   manufacturers whose URL structures are known.

Rules:
- Never fabricate product-specific URLs (e.g. /products/{MPN}) unless the
  URL pattern has been verified for that manufacturer.
- Never emit search engine URLs (Google, Bing).
- Never emit retail/distributor marketplace URLs.
- Return blank ("") + review flag when a URL cannot be verified.
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
    "kichler": "kichlerlighting.com",
    "ge": "geappliances.com",
    "lg": "lg.com",
}

# Verified search URL patterns — only for manufacturers whose site search
# URL structure has been verified to actually work.
VERIFIED_SEARCH_PATTERNS: Dict[str, str] = {
    "milwaukeetool.com": "https://www.milwaukeetool.com/search?q={mpn}",
    "dewalt.com": "https://www.dewalt.com/search?query={mpn}",
    "makitatools.com": "https://www.makitatools.com/search?q={mpn}",
    "boschtools.com": "https://www.boschtools.com/us/en/search?q={mpn}",
    "festool.com": "https://www.festool.com/search?q={mpn}",
    "kleintools.com": "https://www.kleintools.com/search?q={mpn}",
    "3m.com": "https://www.3m.com/3M/en_US/search/?Ntt={mpn}",
    "diablotools.com": "https://www.diablotools.com/search?q={mpn}",
    "freudtools.com": "https://www.freudtools.com/search?q={mpn}",
    "trex.com": "https://www.trex.com/search?q={mpn}",
    "satco.com": "https://www.satco.com/search?q={mpn}",
    "leviton.com": "https://www.leviton.com/search?q={mpn}",
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


def build_provenance_urls(
    manufacturer_name: str,
    mfg_part_num: str,
    brand_name: str = "",
    product_name: str = "",
) -> Dict[str, object]:
    """Builds verified manufacturer provenance URLs for one row.

    Returns a dict with:
        mfr_url:  verified manufacturer homepage if domain is recognized,
                  otherwise blank ("").
        ref_urls: list of verified search/catalog URLs if the manufacturer's
                  search URL pattern is known, otherwise empty list ([]).

    Strictly excludes search engines (Google, Bing) and retail marketplaces
    (Amazon, eBay, Walmart, etc.). Never fabricates URLs to force fill rate.
    """
    mfg = _clean(manufacturer_name)
    brand = _clean(brand_name) or mfg
    mpn = str(mfg_part_num or "").strip()

    domain = _match_domain(mfg, brand)

    # If no verified manufacturer domain is recognized, return blank/empty
    if not domain:
        return {"mfr_url": "", "ref_urls": []}

    # Verified first-party manufacturer homepage (the only URL we can
    # guarantee exists without actually fetching it).
    mfr_url = f"https://www.{domain}"

    ref_urls: List[str] = []

    # Only emit a search/product URL if we have a verified URL pattern
    # for this manufacturer's website.
    if mpn and domain in VERIFIED_SEARCH_PATTERNS:
        pattern = VERIFIED_SEARCH_PATTERNS[domain]
        ref_urls.append(pattern.format(mpn=quote_plus(mpn)))

    # Safety net: filter out any excluded marketplace domains
    ref_urls = [
        u for u in ref_urls
        if not any(bad in u.lower() for bad in EXCLUDED_RETAIL_DOMAINS)
    ][:5]

    return {"mfr_url": mfr_url, "ref_urls": ref_urls}