"""
Reference-data loader layer for the supplied Unilog master/LOV pack.

Author: Member 1 (Master Data)
Package: fuma_rules

WHY THIS MODULE EXISTS
----------------------
The problem statement supplies seven reference files and states plainly that
attribute values must come from the LOV, that manufacturer/brand names must match
the approved list exactly, and that units must use the approved abbreviation --
"a fluent description made of invented values scores zero".

Before this module the pipeline satisfied none of that: every vocabulary was a
Python literal (29 hand-typed brands against a supplied 27,000). This module is
the single seam through which real reference data enters the pipeline.

DESIGN: GRACEFUL DEGRADATION WITH HONEST PROVENANCE
---------------------------------------------------
The reference files are licensed client data and are NOT committed to this repo.
So every loader here is written to:

  1. Parse the real file if it is present in ``reference_data/`` (or wherever
     ``FUMA_REFERENCE_DIR`` points).
  2. Fall back to the curated built-in seed vocabulary if it is absent.
  3. **Report which of the two happened**, via :func:`provenance_report`.

That third point is the important one. A pipeline that silently substitutes a
29-row literal for a 27,000-row master file is claiming accuracy it has not
earned. Every consumer of this module can ask where its vocabulary came from,
and the benchmark prints it. We would rather show "seed fallback, 29 rows" than
imply full master-data coverage.

These sheets are deliberately messy -- merged cells, multi-row headers,
``Decimal_Fraction`` is four side-by-side Fraction|Decimal blocks, and the UOM
sheet parks notes in stray columns. Each loader therefore sniffs for its header
row rather than assuming row 1.

USAGE
-----
Drop the seven files into ``reference_data/`` and everything below activates with
no code change::

    reference_data/
        UniCat_Manufacturer_and_Brand_List.xlsx
        Unicat_Lov_v1_0_Updated_With_Remarks.xlsx
        FAUCETS_LOV.xlsx
        Fittings_LOV.xlsx
        Unilog_Master_UOM_Standards_Abbreviations_and_Terms.xlsx
        Decimal_Fraction.xlsx
        UNILOG_INTERNAL_CONTENT_GUIDELINES.docx
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:  # pandas is already a dependency; guard so the pipeline survives without it
    import pandas as pd

    HAS_PANDAS = True
except ImportError:  # pragma: no cover - defensive
    HAS_PANDAS = False


# ---------------------------------------------------------------------------
# Where the reference pack lives
# ---------------------------------------------------------------------------

#: Repo-root-relative default. Overridable so judges/CI can point elsewhere.
DEFAULT_REFERENCE_DIRNAME = "reference_data"


def reference_dir() -> Path:
    """Directory holding the supplied reference pack.

    ``FUMA_REFERENCE_DIR`` wins if set, so the same code runs against a local
    copy, a mounted share or a CI fixture without edits.
    """
    override = os.environ.get("FUMA_REFERENCE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / DEFAULT_REFERENCE_DIRNAME


#: Canonical filenames as shipped in the challenge pack.
FILE_MANUFACTURER_BRAND = "UniCat_Manufacturer_and_Brand_List.xlsx"
FILE_CROSS_CATEGORY_LOV = "Unicat_Lov_v1_0_Updated_With_Remarks.xlsx"
FILE_FAUCETS_LOV = "FAUCETS_LOV.xlsx"
FILE_FITTINGS_LOV = "Fittings_LOV.xlsx"
FILE_UOM_STANDARDS = "Unilog_Master_UOM_Standards_Abbreviations_and_Terms.xlsx"
FILE_DECIMAL_FRACTION = "Decimal_Fraction.xlsx"
FILE_CONTENT_GUIDELINES = "UNILOG_INTERNAL_CONTENT_GUIDELINES.docx"

ALL_REFERENCE_FILES = (
    FILE_MANUFACTURER_BRAND,
    FILE_CROSS_CATEGORY_LOV,
    FILE_FAUCETS_LOV,
    FILE_FITTINGS_LOV,
    FILE_UOM_STANDARDS,
    FILE_DECIMAL_FRACTION,
    FILE_CONTENT_GUIDELINES,
)


def _resolve(filename: str) -> Optional[Path]:
    """Returns the file path if present, else None.

    Tolerates case and separator drift (`Unicat_Lov...` vs `UniCat_LOV...`,
    spaces vs underscores) because real hand-managed packs are inconsistent.
    """
    base = reference_dir()
    if not base.is_dir():
        return None

    direct = base / filename
    if direct.is_file():
        return direct

    def norm(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", name.lower())

    target = norm(filename)
    for candidate in base.iterdir():
        if candidate.is_file() and norm(candidate.name) == target:
            return candidate
    return None


def _find_header_row(
    frame: "pd.DataFrame", required_tokens: Sequence[str], scan_rows: int = 12
) -> Optional[int]:
    """Locates the real header row in a sheet read with ``header=None``.

    Returns the row index whose cells contain all `required_tokens`
    (case/punctuation-insensitive), or None. This is what lets us survive
    title banners and merged cells above the true header.
    """
    wanted = [re.sub(r"[^a-z0-9]+", "", t.lower()) for t in required_tokens]
    for idx in range(min(scan_rows, len(frame))):
        cells = [
            re.sub(r"[^a-z0-9]+", "", str(v).lower())
            for v in frame.iloc[idx].tolist()
            if v is not None and str(v).strip()
        ]
        if all(any(w and w in c for c in cells) for w in wanted):
            return idx
    return None


# ---------------------------------------------------------------------------
# Provenance: the honesty mechanism
# ---------------------------------------------------------------------------


@dataclass
class SourceInfo:
    """Where one vocabulary actually came from, and how big it is."""

    name: str
    loaded_from_file: bool
    row_count: int
    path: Optional[str] = None
    detail: str = ""

    @property
    def status(self) -> str:
        return "MASTER FILE" if self.loaded_from_file else "SEED FALLBACK"

    def describe(self) -> str:
        return f"{self.name}: {self.status} ({self.row_count} rows)"


@dataclass
class ReferenceBundle:
    """Every vocabulary the pipeline needs, plus provenance for each."""

    manufacturer_brand: List[Dict[str, str]] = field(default_factory=list)
    brand_alias: Dict[str, str] = field(default_factory=dict)
    lov_by_classpath: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)
    lov_all_values: Set[str] = field(default_factory=set)
    lov_value_to_label: Dict[str, str] = field(default_factory=dict)
    fitting_types: Set[str] = field(default_factory=set)
    connection_map: Dict[str, str] = field(default_factory=dict)
    material_map: Dict[str, str] = field(default_factory=dict)
    faucet_attribute_order: List[str] = field(default_factory=list)
    uom_map: Dict[str, str] = field(default_factory=dict)
    decimal_fraction: Dict[float, str] = field(default_factory=dict)
    sources: List[SourceInfo] = field(default_factory=list)

    @property
    def any_master_file_loaded(self) -> bool:
        return any(s.loaded_from_file for s in self.sources)

    @property
    def lov_available(self) -> bool:
        """True only when a real LOV file backs the constrained vocabulary.

        Gates the LOV-compliance metric: without this we would be scoring our
        own seed list against itself, which is meaningless.
        """
        return any(
            s.loaded_from_file
            and s.name in ("Cross-category LOV", "Fittings LOV", "Faucets LOV")
            for s in self.sources
        )


# ---------------------------------------------------------------------------
# 1. Manufacturer & brand master (27,000+ approved rows)
# ---------------------------------------------------------------------------

_TRADEMARK_RE = re.compile(r"[®™]")


def _norm_key(value: Any) -> str:
    """Aggressive match key: lowercase alphanumerics only, symbols dropped."""
    text = _TRADEMARK_RE.sub("", str(value or "")).lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def load_manufacturer_brand() -> Tuple[List[Dict[str, str]], Dict[str, str], SourceInfo]:
    """Loads the approved manufacturer/brand master.

    Returns (rows, alias_map, provenance). Legal casing and ®/™ are preserved
    exactly as published -- the brief requires names to match "symbols and all".
    """
    path = _resolve(FILE_MANUFACTURER_BRAND)
    if path is None or not HAS_PANDAS:
        from fuma_rules.brand_matcher import BRAND_ALIAS_MAP, CANONICAL_BRAND_CATALOG

        return (
            list(CANONICAL_BRAND_CATALOG),
            dict(BRAND_ALIAS_MAP),
            SourceInfo(
                "Manufacturer/Brand master",
                False,
                len(CANONICAL_BRAND_CATALOG),
                detail=f"{FILE_MANUFACTURER_BRAND} not found in {reference_dir()}",
            ),
        )

    raw = pd.read_excel(path, header=None, dtype=str)
    header_idx = _find_header_row(raw, ["manufacturer name", "brand name"]) or 0
    frame = pd.read_excel(path, header=header_idx, dtype=str).fillna("")
    frame.columns = [str(c).strip() for c in frame.columns]

    def col(*candidates: str) -> Optional[str]:
        norm = {_norm_key(c): c for c in frame.columns}
        for cand in candidates:
            if _norm_key(cand) in norm:
                return norm[_norm_key(cand)]
        return None

    c_mfg = col("MANUFACTURER_NAME", "Manufacturer Name")
    c_brand = col("BRAND_NAME", "Brand Name")
    c_mcode = col("MANUFACTURER_CODE", "Manufacturer Code")
    c_bcode = col("BRAND_CODE", "Brand Code")

    rows: List[Dict[str, str]] = []
    alias: Dict[str, str] = {}
    for _, r in frame.iterrows():
        mfg = str(r.get(c_mfg, "") if c_mfg else "").strip()
        brand = str(r.get(c_brand, "") if c_brand else "").strip()
        if not mfg and not brand:
            continue
        # "Where an item has no brand, the manufacturer name is used instead."
        brand = brand or mfg
        rows.append(
            {
                "MANUFACTURER_NAME": mfg,
                "BRAND_NAME": brand,
                "MANUFACTURER_CODE": str(r.get(c_mcode, "") if c_mcode else "").strip(),
                "BRAND_CODE": str(r.get(c_bcode, "") if c_bcode else "").strip(),
                "KEYWORDS": [],
            }
        )
        if brand:
            alias.setdefault(_norm_key(brand), brand)
        if mfg:
            alias.setdefault(_norm_key(mfg), brand)

    return (
        rows,
        alias,
        SourceInfo(
            "Manufacturer/Brand master", True, len(rows), str(path),
            "approved names with legal casing and ®/™ preserved",
        ),
    )


# ---------------------------------------------------------------------------
# 2. Cross-category LOV (~161,000 rows)
# ---------------------------------------------------------------------------


def load_cross_category_lov() -> Tuple[
    Dict[str, Dict[str, Set[str]]], Set[str], Dict[str, str], SourceInfo
]:
    """Loads Classpath -> {Attribute Label -> {allowed values}}.

    Prefers the Normalized Label/Values columns: the brief says the normalised
    form is what output must take.
    """
    path = _resolve(FILE_CROSS_CATEGORY_LOV)
    if path is None or not HAS_PANDAS:
        return (
            {},
            set(),
            {},
            SourceInfo(
                "Cross-category LOV", False, 0,
                detail=f"{FILE_CROSS_CATEGORY_LOV} not found in {reference_dir()}",
            ),
        )

    raw = pd.read_excel(path, header=None, dtype=str)
    header_idx = _find_header_row(raw, ["classpath", "attribute label"]) or 0
    frame = pd.read_excel(path, header=header_idx, dtype=str).fillna("")
    frame.columns = [str(c).strip() for c in frame.columns]
    lookup = {_norm_key(c): c for c in frame.columns}

    def col(*candidates: str) -> Optional[str]:
        for cand in candidates:
            if _norm_key(cand) in lookup:
                return lookup[_norm_key(cand)]
        return None

    c_path = col("Classpath")
    c_label = col("Normalized Label", "Attribute Label")
    c_value = col("Normalized Values", "Attribute Values")

    by_path: Dict[str, Dict[str, Set[str]]] = {}
    all_values: Set[str] = set()
    value_to_label: Dict[str, str] = {}

    for _, r in frame.iterrows():
        classpath = str(r.get(c_path, "") if c_path else "").strip()
        label = str(r.get(c_label, "") if c_label else "").strip()
        value_cell = str(r.get(c_value, "") if c_value else "").strip()
        if not label:
            continue
        # One cell can hold several permitted values.
        values = [v.strip() for v in re.split(r"[|;\n]+", value_cell) if v.strip()]
        key = _normalize_classpath(classpath)
        bucket = by_path.setdefault(key, {})
        target = bucket.setdefault(label, set())
        for v in values:
            target.add(v)
            all_values.add(_norm_key(v))
            value_to_label.setdefault(_norm_key(v), label)

    return (
        by_path,
        all_values,
        value_to_label,
        SourceInfo(
            "Cross-category LOV", True, len(frame), str(path),
            f"{len(by_path)} classpaths, {len(all_values)} distinct normalized values",
        ),
    )


def _normalize_classpath(classpath: str) -> str:
    """Canonical classpath key: ground truth uses ``A>B>C``, our engine ``A > B > C``."""
    parts = [p.strip() for p in str(classpath or "").split(">") if p.strip()]
    return ">".join(parts).lower()


# ---------------------------------------------------------------------------
# 3. Fittings LOV -- the many-to-one normalisation showcase
# ---------------------------------------------------------------------------


def load_fittings_lov() -> Tuple[Set[str], Dict[str, str], Dict[str, str], SourceInfo]:
    """Loads 390 fitting types, 1,472->515 connection and 464->113 material maps.

    Sheet names vary between pack revisions, so sheets are classified by the
    column tokens they contain rather than by name.
    """
    path = _resolve(FILE_FITTINGS_LOV)
    if path is None or not HAS_PANDAS:
        return (
            set(),
            {},
            {},
            SourceInfo(
                "Fittings LOV", False, 0,
                detail=f"{FILE_FITTINGS_LOV} not found in {reference_dir()}",
            ),
        )

    book = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    fitting_types: Set[str] = set()
    connection_map: Dict[str, str] = {}
    material_map: Dict[str, str] = {}
    total_rows = 0

    for _, raw in book.items():
        if raw.empty:
            continue
        header_idx = _find_header_row(raw, ["fitting type"])
        if header_idx is not None:
            frame = _reheader(raw, header_idx)
            c = _pick(frame, "Fitting Type")
            if c:
                for v in frame[c].dropna():
                    text = str(v).strip()
                    if text:
                        fitting_types.add(text)
                total_rows += len(frame)
                continue

        # Variant -> canonical mapping sheets.
        for src_tokens, dst_tokens, target in (
            (("connection type", "manufacturer"), ("canonical", "normalized", "approved"), connection_map),
            (("material construction",), ("material", "normalized", "approved"), material_map),
        ):
            header_idx = _find_header_row(raw, [src_tokens[0]])
            if header_idx is None:
                continue
            frame = _reheader(raw, header_idx)
            c_src = _pick(frame, *src_tokens)
            c_dst = _pick(frame, *dst_tokens)
            if not c_src or not c_dst or c_src == c_dst:
                continue
            for _, r in frame.iterrows():
                src = str(r.get(c_src, "") or "").strip()
                dst = str(r.get(c_dst, "") or "").strip()
                if src and dst:
                    target[_norm_key(src)] = dst
            total_rows += len(frame)

    return (
        fitting_types,
        connection_map,
        material_map,
        SourceInfo(
            "Fittings LOV", True, total_rows, str(path),
            f"{len(fitting_types)} types, {len(connection_map)} connection variants, "
            f"{len(material_map)} material variants",
        ),
    )


def _reheader(raw: "pd.DataFrame", header_idx: int) -> "pd.DataFrame":
    """Promotes row ``header_idx`` to the header and drops everything above it."""
    frame = raw.iloc[header_idx + 1 :].copy()
    frame.columns = [str(c).strip() for c in raw.iloc[header_idx].tolist()]
    return frame.loc[:, [c for c in frame.columns if c and c.lower() != "nan"]]


def _pick(frame: "pd.DataFrame", *tokens: str) -> Optional[str]:
    """First column whose normalised name contains any of ``tokens``."""
    for col in frame.columns:
        key = _norm_key(col)
        for token in tokens:
            if _norm_key(token) in key:
                return col
    return None


# ---------------------------------------------------------------------------
# 4. Faucets LOV -- fixed attribute order for one deep category
# ---------------------------------------------------------------------------


def load_faucets_lov() -> Tuple[List[str], Dict[str, Set[str]], SourceInfo]:
    """Loads the faucet attribute sequence and permitted values.

    Order matters: the spec fixes attribute and title word order, so we read the
    sequence rather than inventing one.
    """
    path = _resolve(FILE_FAUCETS_LOV)
    if path is None or not HAS_PANDAS:
        return (
            [],
            {},
            SourceInfo(
                "Faucets LOV", False, 0,
                detail=f"{FILE_FAUCETS_LOV} not found in {reference_dir()}",
            ),
        )

    book = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    order: List[str] = []
    values: Dict[str, Set[str]] = {}
    total = 0

    for _, raw in book.items():
        if raw.empty:
            continue
        header_idx = _find_header_row(raw, ["attribute"])
        if header_idx is None:
            continue
        frame = _reheader(raw, header_idx)
        c_label = _pick(frame, "attribute label", "attribute name", "attribute")
        c_seq = _pick(frame, "sequence", "sort", "order")
        c_val = _pick(frame, "permitted", "attribute values", "values")
        if not c_label:
            continue

        if c_seq:
            frame = frame.assign(
                _seq=pd.to_numeric(frame[c_seq], errors="coerce")
            ).sort_values("_seq", na_position="last")

        for _, r in frame.iterrows():
            label = str(r.get(c_label, "") or "").strip()
            if not label or label.lower() == "nan":
                continue
            if label not in order:
                order.append(label)
            if c_val:
                cell = str(r.get(c_val, "") or "")
                for v in re.split(r"[|;,\n]+", cell):
                    v = v.strip()
                    if v:
                        values.setdefault(label, set()).add(v)
        total += len(frame)

    return (
        order,
        values,
        SourceInfo(
            "Faucets LOV", True, total, str(path),
            f"{len(order)} attributes in fixed sequence",
        ),
    )


# ---------------------------------------------------------------------------
# 5. Master UOM standards (~500 approved abbreviations)
# ---------------------------------------------------------------------------


def load_uom_standards() -> Tuple[Dict[str, str], SourceInfo]:
    """Loads variant -> approved UOM abbreviation.

    Merges onto the built-in map so the curated entries stay as a safety net
    while the master file becomes authoritative on conflict.
    """
    from fuma_rules.uom_standardizer import MASTER_UOM_MAP

    path = _resolve(FILE_UOM_STANDARDS)
    if path is None or not HAS_PANDAS:
        return (
            dict(MASTER_UOM_MAP),
            SourceInfo(
                "Master UOM standards", False, len(MASTER_UOM_MAP),
                detail=f"{FILE_UOM_STANDARDS} not found in {reference_dir()}",
            ),
        )

    merged = dict(MASTER_UOM_MAP)
    added = 0
    book = pd.read_excel(path, sheet_name=None, header=None, dtype=str)

    for _, raw in book.items():
        if raw.empty:
            continue
        header_idx = _find_header_row(raw, ["uom"]) or _find_header_row(raw, ["abbreviation"])
        if header_idx is None:
            continue
        frame = _reheader(raw, header_idx)
        c_approved = _pick(frame, "capture form", "approved", "abbreviation", "uom")
        c_variant = _pick(frame, "variant", "synonym", "term", "measurement type", "unit")
        if not c_approved:
            continue

        for _, r in frame.iterrows():
            approved = str(r.get(c_approved, "") or "").strip()
            if not approved or approved.lower() == "nan":
                continue
            merged[approved.strip().lower()] = approved
            added += 1
            if c_variant:
                cell = str(r.get(c_variant, "") or "")
                for variant in re.split(r"[|;,/\n]+", cell):
                    variant = variant.strip()
                    if variant and variant.lower() != "nan":
                        merged[variant.lower()] = approved
                        added += 1

    return (
        merged,
        SourceInfo(
            "Master UOM standards", True, added, str(path),
            f"{len(merged)} total variant->approved mappings after merge",
        ),
    )


# ---------------------------------------------------------------------------
# 6. Decimal <-> fraction (63 exact inch conversions)
# ---------------------------------------------------------------------------


def load_decimal_fraction() -> Tuple[Dict[float, str], SourceInfo]:
    """Loads decimal -> fraction conversions.

    The sheet is laid out as FOUR side-by-side Fraction|Decimal blocks, so we
    scan every cell pair rather than assuming a single two-column table.
    """
    from fuma_rules.uom_standardizer import DECIMAL_FRACTION_LOOKUP

    path = _resolve(FILE_DECIMAL_FRACTION)
    if path is None or not HAS_PANDAS:
        return (
            dict(DECIMAL_FRACTION_LOOKUP),
            SourceInfo(
                "Decimal/Fraction table", False, len(DECIMAL_FRACTION_LOOKUP),
                detail=f"{FILE_DECIMAL_FRACTION} not found in {reference_dir()}",
            ),
        )

    raw = pd.read_excel(path, header=None, dtype=str)
    table: Dict[float, str] = {}
    frac_re = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")

    for _, row in raw.iterrows():
        cells = [str(v).strip() if v is not None else "" for v in row.tolist()]
        for i, cell in enumerate(cells[:-1]):
            m = frac_re.match(cell)
            if not m:
                continue
            try:
                decimal = float(cells[i + 1])
            except (TypeError, ValueError):
                continue
            table[round(decimal, 6)] = f"{int(m.group(1))}/{int(m.group(2))}"

    if not table:  # unrecognised layout -> keep the verified built-in table
        return (
            dict(DECIMAL_FRACTION_LOOKUP),
            SourceInfo(
                "Decimal/Fraction table", False, len(DECIMAL_FRACTION_LOOKUP),
                str(path), "file present but layout unrecognised; using built-in table",
            ),
        )

    return (
        table,
        SourceInfo(
            "Decimal/Fraction table", True, len(table), str(path),
            "parsed from four side-by-side Fraction|Decimal blocks",
        ),
    )


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_reference_bundle() -> ReferenceBundle:
    """Loads every vocabulary once per process and caches the result.

    Never raises: a malformed sheet degrades that one vocabulary to its seed
    fallback and records the reason, rather than taking down enrichment.
    """
    bundle = ReferenceBundle()

    def attempt(fn, apply) -> None:
        try:
            apply(fn())
        except Exception as exc:  # noqa: BLE001 - one bad sheet must not kill the run
            bundle.sources.append(
                SourceInfo(getattr(fn, "__name__", "reference"), False, 0,
                           detail=f"load failed: {type(exc).__name__}: {exc}")
            )

    def _mfg(result):
        rows, alias, info = result
        bundle.manufacturer_brand = rows
        bundle.brand_alias = alias
        bundle.sources.append(info)

    def _lov(result):
        by_path, all_values, value_to_label, info = result
        bundle.lov_by_classpath = by_path
        bundle.lov_all_values = all_values
        bundle.lov_value_to_label = value_to_label
        bundle.sources.append(info)

    def _fit(result):
        types, conn, mat, info = result
        bundle.fitting_types = types
        bundle.connection_map = conn
        bundle.material_map = mat
        bundle.sources.append(info)

    def _fauc(result):
        order, values, info = result
        bundle.faucet_attribute_order = order
        for label, vals in values.items():
            bucket = bundle.lov_by_classpath.setdefault(
                _normalize_classpath("Plumbing>Faucets & Fixtures>Kitchen & Bath Sink Faucets"),
                {},
            )
            bucket.setdefault(label, set()).update(vals)
            for v in vals:
                bundle.lov_all_values.add(_norm_key(v))
                bundle.lov_value_to_label.setdefault(_norm_key(v), label)
        bundle.sources.append(info)

    def _uom(result):
        mapping, info = result
        bundle.uom_map = mapping
        bundle.sources.append(info)

    def _dec(result):
        table, info = result
        bundle.decimal_fraction = table
        bundle.sources.append(info)

    attempt(load_manufacturer_brand, _mfg)
    attempt(load_cross_category_lov, _lov)
    attempt(load_fittings_lov, _fit)
    attempt(load_faucets_lov, _fauc)
    attempt(load_uom_standards, _uom)
    attempt(load_decimal_fraction, _dec)

    return bundle


def provenance_report() -> Dict[str, Any]:
    """Machine-readable answer to "where did this vocabulary come from?".

    Surfaced in the benchmark and the API so a reviewer never has to take our
    coverage claims on trust.
    """
    bundle = load_reference_bundle()
    return {
        "reference_dir": str(reference_dir()),
        "reference_dir_exists": reference_dir().is_dir(),
        "files_expected": list(ALL_REFERENCE_FILES),
        "files_present": [f for f in ALL_REFERENCE_FILES if _resolve(f) is not None],
        "files_missing": [f for f in ALL_REFERENCE_FILES if _resolve(f) is None],
        "lov_enforcement_active": bundle.lov_available,
        "sources": [
            {
                "name": s.name,
                "status": s.status,
                "rows": s.row_count,
                "path": s.path,
                "detail": s.detail,
            }
            for s in bundle.sources
        ],
    }


def lov_values_for_classpath(classpath: str) -> Dict[str, Set[str]]:
    """Permitted ``{label: {values}}`` for a classpath, walking up on miss.

    A leaf like ``A>B>C`` inherits from ``A>B`` when the LOV specifies the
    parent, which mirrors how the sheets are organised.
    """
    bundle = load_reference_bundle()
    if not bundle.lov_by_classpath:
        return {}

    key = _normalize_classpath(classpath)
    if key in bundle.lov_by_classpath:
        return bundle.lov_by_classpath[key]

    parts = key.split(">")
    for depth in range(len(parts) - 1, 0, -1):
        candidate = ">".join(parts[:depth])
        if candidate in bundle.lov_by_classpath:
            return bundle.lov_by_classpath[candidate]
    return {}


def is_lov_value(value: str) -> bool:
    """True if ``value`` appears anywhere in the approved LOV vocabulary."""
    bundle = load_reference_bundle()
    if not bundle.lov_all_values:
        return False
    return _norm_key(value) in bundle.lov_all_values


def canonical_connection_type(raw: str) -> Optional[str]:
    """Maps a supplier connection spelling to its canonical value (1,472 -> 515)."""
    bundle = load_reference_bundle()
    return bundle.connection_map.get(_norm_key(raw))


def canonical_material(raw: str) -> Optional[str]:
    """Maps a supplier material spelling to the simplified list (464 -> 113)."""
    bundle = load_reference_bundle()
    return bundle.material_map.get(_norm_key(raw))
