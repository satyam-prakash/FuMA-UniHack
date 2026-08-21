# Member 3 — Locked Interface Contract

Every Member 3 module is written against this document. Do not invent
alternative names, shapes or field spellings; other modules are written in
parallel against exactly these signatures.

## 0. Repo facts

- Repo root: `/Users/ashutoshyadav/Desktop/Hackathon/FuMA-UniHack`
- Python venv: `.venv/bin/python` (fastapi, uvicorn, pandas, openpyxl, rapidfuzz, pydantic, python-multipart, pytest, httpx all installed)
- Run tests from repo root: `.venv/bin/python -m pytest member3/tests -q`
- Member 1 package: `fuma_rules` (do NOT modify)
- Member 2 package: `fuma_engine` (do NOT modify)
- Member 3 package: `member3` (all our work lives here)
- Datasets committed at `member3/data/sample_input_1000.csv` and `member3/data/expected_delivery_format.csv`

## 1. Upstream engines (read-only, already verified working)

Member 1 normalization:

```python
from fuma_rules.stage1_master_data import MasterDataPipelineStage
stage = MasterDataPipelineStage()          # construct once, reuse (loads brand catalog)
normalized = stage.process_item(raw_row)   # dict -> dict
```

`process_item` returns `dict(raw_row)` plus these added keys:
`CLEAN_DESC`, `MANUFACTURER_NAME`, `BRAND_NAME`, `MANUFACTURER_PART_NUMBER`,
`STANDARDIZED_DIMENSIONS`, `STAGE1_STATUS`.

Member 2 enrichment:

```python
from fuma_engine.pipeline_interface import enrich_single_item
enriched = enrich_single_item(normalized)  # dict -> dict (ProductRecord.model_dump())
```

`ProductRecord` fields (`fuma_engine/schema.py`): `mfg_part_num`, `part_desc_raw`,
`manufacturer_name`, `brand_name`, `series`, `classpath`, `unspsc`, `product_name`,
`attributes` (list of `{label, value, uom}`), `features` (list of str),
`invoice_desc` (max 40), `mobile_desc` (max 85), `short_desc`, `long_desc1`,
`retail_desc`, `confidence_score` (float 0-100), `needs_review` (bool),
`review_reasons` (list of str).

Verified: 1000 rows through M1+M2 in 0.11 s, 0 exceptions.

## 2. Delivery layer — `member3/delivery/`

### `columns.py` (ALREADY WRITTEN AND VERIFIED — do not edit)

```python
DELIVERY_COLUMNS: List[str]      # exactly 252, exact order, verified == reference CSV header
DELIVERY_COLUMN_COUNT = 252
ATTRIBUTE_SLOTS = 50
LEADING_COLUMNS: List[str]       # 55 columns before the attribute block
TRAILING_COLUMNS: List[str]      # 47 columns after the attribute block
```

### `mapper.py`

```python
def map_record_to_delivery(enriched: dict, raw: dict) -> Tuple[Dict[str, str], List[str]]:
    """enriched = ProductRecord.model_dump(); raw = original CSV row dict.
    Returns (row, warnings). `row` has EXACTLY the 252 DELIVERY_COLUMNS keys,
    every value a str (blank string for unknown). `warnings` lists export
    warnings such as attribute overflow."""
```

Mapping rules (blank = `""`, never invent a value):

| Delivery column                                                                    | Source                                                         |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `Mfg_Part_Num`, `Part_Desc`, `E1_Brand`, `Unilog_Brand`, `DIB_Brand`, `Part_Manuf` | passthrough from `raw` (same key)                              |
| `PART_NUMBER`, `Dept`, `Class`, `Fine`, `SKU - MY_PART_NUMBER`                     | passthrough from `raw` if the key exists, else `""`            |
| `MFR URL`, `Ref URL 1..5`                                                          | `""` (no scraping in scope)                                    |
| `MANUFACTURER_NAME`                                                                | `enriched["manufacturer_name"]`                                |
| `BRAND_NAME`                                                                       | `enriched["brand_name"]`                                       |
| `TRADE_NAME`                                                                       | `""` (blank in ground truth)                                   |
| `MANUFACTURER_PART_NUMBER`                                                         | `enriched["mfg_part_num"]`                                     |
| `ALTERNATE_PART_NUMBER`                                                            | `""`                                                           |
| `Classpath`                                                                        | `enriched["classpath"]`                                        |
| `MOBILE_DESC` / `INVOICE_DESC` / `SHORT_DESC` / `LONG_DESC1` / `RETAIL_DESC`       | matching `enriched` field                                      |
| `MARKETING_DESCRIPTION`                                                            | `""`                                                           |
| `ITEM_FEATURES_1..20`                                                              | `enriched["features"]` in order; extras dropped with a warning |
| `With`, `Standard/Approvals`, `Prop 65`, `Application`, `Includes`                 | `""`                                                           |
| `Product Name`                                                                     | `enriched["product_name"]`                                     |
| `ATTRIBUTE_LABEL/VALUE/UOM n`                                                      | `enriched["attributes"][n-1]` fields, n = 1..50                |
| `UNSPSC`                                                                           | `enriched["unspsc"]`                                           |
| everything else in `TRAILING_COLUMNS`                                              | `""`                                                           |

Overflow warnings (exact strings):

- `f"attribute overflow: {n} attributes extracted, only first 50 exported"`
- `f"feature overflow: {n} features extracted, only first 20 exported"`

### `validators.py`

```python
class DeliveryValidationError(Exception): ...

def validate_delivery_headers(headers: Sequence[str]) -> None:
    """Raises DeliveryValidationError unless list(headers) == DELIVERY_COLUMNS."""

def validate_delivery_rows(rows: Sequence[Mapping[str, str]]) -> None:
    """Raises DeliveryValidationError if any row's key set != set(DELIVERY_COLUMNS)."""

def check_delivery(rows: Sequence[Mapping[str, str]]) -> Tuple[bool, List[str]]:
    """Non-raising form for the API. Returns (ok, errors)."""
```

### `csv_exporter.py`

```python
def rows_to_csv_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    """UTF-8 with BOM (so Excel keeps ® and ™), CRLF, 252 columns, header first.
    Calls validate_delivery_rows first."""
```

### `xlsx_exporter.py`

```python
def rows_to_xlsx_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    """OpenPyXL, sheet name "Delivery Format", bold header, frozen header row,
    autofilter over the full 252-column range. Calls validate_delivery_rows first."""
```

## 3. Backend — `member3/backend/`

### `services/pipeline_service.py`

```python
def enrich_raw_row(raw_row: dict, row_id: int) -> dict:   # returns RowResult
def new_pipeline() -> "Pipeline"                          # holds the reusable MasterDataPipelineStage
```

`RowResult` shape (exact keys — the frontend and metrics both depend on it):

```python
{
  "row_id": int,                        # 1-based
  "status": "success" | "review" | "error",
  "mpn": str,                           # convenience for tables
  "part_desc": str,                     # raw description, convenience
  "brand_name": str,
  "product_name": str,
  "classpath": str,
  "confidence_score": float,
  "raw": dict,                          # original CSV row
  "normalized": dict,                   # ONLY the keys M1 added (6 keys)
  "enriched": dict | None,              # ProductRecord.model_dump(), None on error
  "delivery_row": dict | None,          # 252-key delivery row, None on error
  "validation": {
      "schema_valid": bool,
      "schema_errors": list[str],
      "invoice_len": int,
      "invoice_pass": bool,             # 0 < len <= 40 and isupper()
      "mobile_len": int,
      "schema_mobile_pass": bool,       # len <= 85  (what ProductRecord enforces)
      "mobile_target_pass": bool,       # 60 <= len <= 80  (the stricter project target)
      "attribute_count": int,
      "feature_count": int,
      "generic_classpath": bool,        # "General Hardware" in classpath or blank
      "export_warnings": list[str],
  },
  "review": {
      "needs_review": bool,
      "reasons": list[str],
      "categories": list[str],          # subset of REVIEW_CATEGORIES below
      "decision": None | {"action": str, "comment": str, "at": str},
  },
  "error": None | {"code": str, "message": str, "stage": str},
}
```

`REVIEW_CATEGORIES` (exact literals, used by the review filters UI):
`"low_confidence"`, `"schema_failure"`, `"no_attributes"`, `"generic_taxonomy"`,
`"description_issue"`, `"export_issue"`, `"processing_error"`.

Rules:

- Wrap M1, M2, schema validation and delivery mapping each in try/except. On
  exception set `status="error"`, fill `error` with `stage` in
  `{"member1","member2","schema","delivery"}`, add category `"processing_error"`,
  and STILL return a RowResult. Never raise out of `enrich_raw_row`.
- `status="review"` when `review["needs_review"]` and no error.
- `low_confidence` when `confidence_score < 80`.
- `description_issue` when not `invoice_pass` or not `mobile_target_pass`.

### `services/batch_service.py`

```python
JOB_STATUSES = ("uploaded","queued","processing","completed","completed_with_review","failed")

def create_job(filename: str, rows: list[dict]) -> dict          # the Job dict, status "uploaded"
def get_job(job_id: str) -> dict | None
def start_job(job_id: str) -> dict                               # sets queued, launches worker thread
def _run_job(job_id: str) -> None                                # worker; updates counters live
```

`Job` dict keys: `job_id` (`f"job_{YYYYmmdd}_{nnn}"`), `filename`, `mode`,
`status`, `total`, `processed`, `success`, `review`, `errors`, `progress` (int 0-100),
`created_at`, `started_at`, `finished_at`, `elapsed_seconds`, `rows` (raw dicts),
`results` (list[RowResult]), `stages` (list of `{"key","label","state"}` where state is
`"pending"|"active"|"done"`), `export` (dict, see below).

`stages` keys in order: `input_validation`, `member1`, `member2`, `descriptions`,
`validation`, `delivery_mapping` with labels
`"Input validation"`, `"Member 1 normalization"`, `"Member 2 extraction"`,
`"Description generation"`, `"Validation"`, `"Delivery mapping"`.

In-memory store (module-level dict + `threading.Lock`). No database.

### `services/metrics_service.py`

```python
def build_metrics(job: dict) -> dict
```

Returns:

```python
{
  "job_id": str,
  "totals": {"total":int,"processed":int,"success":int,"review":int,"errors":int},
  "avg_confidence": float,
  "elapsed_seconds": float | None,
  "rows_per_second": float | None,
  "compliance": {
      # each: {"label":str,"rate":float,"passed":int,"total":int,"target":float,"status":"PASS"|"FAIL"}
      "invoice_char_limit": {...},        # target 100.0
      "invoice_all_caps": {...},         # target 100.0
      "schema_mobile": {...},            # target 100.0  (<= 85, what the schema enforces)
      "mobile_target_60_80": {...},      # target 90.0   (the stricter project target)
      "schema_validation": {...},        # target 100.0
      "attribute_presence": {...},       # target 90.0
      "classpath_specific": {...},       # target 95.0
  },
  "controlled_value_compliance": None,    # honest null: no LOV validator is wired in
  "distributions": {
      "status": [{"label":str,"count":int}],
      "confidence": [{"label":str,"count":int}],     # buckets 0-59,60-79,80-89,90-99,100
      "review_reasons": [{"label":str,"count":int}], # top 8
      "classpaths": [{"label":str,"count":int}],     # top 8
  },
  "export": {"columns":252,"validation":"PASS"|"FAIL","rows_ready":int,"rows_needing_review":int,"errors":list[str]},
  "benchmark": None | {
      "matched_rows": int,
      "fields": [{"field":str,"matched":int,"total":int,"rate":float}],
      "overall_rate": float,
  },
}
```

### `services/review_service.py`

```python
REVIEW_ACTIONS = ("approve","reject","override","mark_reviewed")

def list_review_rows(job: dict, category: str = "all") -> list[dict]
def record_decision(job: dict, row_id: int, action: str, comment: str = "") -> dict
```

`list_review_rows` returns compact dicts:
`{"row_id","mpn","part_desc","brand_name","confidence_score","reasons","categories","status","decision"}`.

`record_decision` raises `ValueError` on unknown action or row.

### `services/export_service.py`

```python
def collect_delivery_rows(job: dict, include_review: bool = True) -> list[dict]
def export_status(job: dict) -> dict           # the metrics["export"] block
def build_csv(job: dict) -> bytes
def build_xlsx(job: dict) -> bytes
```

`build_*` raise `DeliveryValidationError` if validation fails; routes turn that
into HTTP 409.

### `services/benchmark_service.py`

```python
GROUND_TRUTH_PATH = Path("member3/data/expected_delivery_format.csv")
BENCHMARK_FIELDS = ["MANUFACTURER_NAME","BRAND_NAME","Classpath","MOBILE_DESC",
                    "INVOICE_DESC","SHORT_DESC","LONG_DESC1","RETAIL_DESC","Product Name"]

def load_ground_truth() -> dict[str, dict]     # keyed by Mfg_Part_Num, {} if file missing
def score_against_ground_truth(job: dict) -> dict | None
```

Comparison is case-insensitive with collapsed whitespace. Return `None` when no
job row matches a ground-truth MPN so the dashboard can hide the panel instead
of showing a fake score.

### `models/api_models.py`

Pydantic v2 models: `HealthResponse`, `UploadResponse`, `EnrichRequest`,
`EnrichResponse`, `JobStatusResponse`, `ResultsPage`, `ReviewDecisionRequest`,
`ApiError`.

### Routes — exact paths

```
GET  /api/health
POST /api/upload                                  multipart field name: "file"
POST /api/enrich                                  body {"job_id": str, "mode": "demo"|"full"}
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/results?page=1&page_size=50&status=all&search=
GET  /api/jobs/{job_id}/results/{row_id}
GET  /api/jobs/{job_id}/metrics
GET  /api/jobs/{job_id}/review?category=all
POST /api/jobs/{job_id}/review/{row_id}           body {"action": str, "comment": str}
GET  /api/jobs/{job_id}/export.csv
GET  /api/jobs/{job_id}/export.xlsx
POST /api/demo/sample                             loads member3/data/sample_input_1000.csv, returns UploadResponse
```

`/results` response: `{"job_id","page","page_size","total","pages","rows":[<compact row>]}`
where compact row = `{"row_id","mpn","part_desc","brand_name","product_name","classpath","confidence_score","status","needs_review","invoice_desc","mobile_desc"}`.

Upload validation: extension in `{.csv,.xlsx}`, size <= 25 MB, non-empty, and
required columns present: `Mfg_Part_Num`, `Part_Desc`, `E1_Brand`,
`Unilog_Brand`, `DIB_Brand`, `Part_Manuf`. Missing columns -> HTTP 422 with
`ApiError` body. Filenames are sanitised; job IDs are server-generated.

Error body shape everywhere:

```json
{ "error": { "code": "...", "message": "...", "row_id": null, "details": [] } }
```

### `main.py`

FastAPI app titled `"FuMA Delivery API"`, all routers under `/api`, CORS allowing
`http://localhost:5173` and `http://127.0.0.1:5173`. If
`member3/frontend/dist` exists, mount it at `/` as SPA static files (so one
process serves the demo). Run with:

```bash
.venv/bin/python -m uvicorn member3.backend.main:app --reload --port 8000
```

## 4. Frontend — `member3/frontend/`

React 18 + Vite + TypeScript (strict) + Tailwind CSS. Dev server proxies `/api`
to `http://localhost:8000`.

### Design system — non-negotiable (from `DESIGN.md`, Industrial Modernist)

Colors: `background/surface #fcf9f2`, `surface-bright #FBFAF7`,
`surface-container-low #f6f3ec`, `surface-container #f1eee7`,
`surface-variant #e5e2db`, `ink-graphite #34332F`, `on-surface #1c1c18`,
`primary #994422`, `primary-container #b85c38`, `on-primary #ffffff`,
`secondary #5f5e5b`, `tertiary #5b5f4d`, `border-subtle #D8D2C8`,
`error #ba1a1a`, `error-container #ffdad6`, `inverse-surface #31312c`,
`primary-fixed-dim #ffb59a`.

Type: `Instrument Serif` for display/headlines (`display-hero` 96px,
`headline-lg` 64px, `headline-md` 32px), `Manrope` for body (`body-lg` 18px,
`body-md` 16px), `IBM Plex Mono` for all data/labels (`data-mono` 14px/0.02em,
`label-caps` 12px/600/0.08em uppercase, `annotation` 11px).

Hard rules:

- **Border radius 0 everywhere.** No rounded corners, ever.
- No gradients, no blurs, no frosted glass, no neon glow.
- Depth via tonal layering + 1px `border-subtle` outlines; the only shadow
  allowed is the hard stamp `shadow-[2px_2px_0px_0px_#171715]`.
- Every numeric/alphanumeric value renders in IBM Plex Mono.
- Cards are "technical plates": 1px border + an `IDX-nn` serial in the top-right
  corner in `annotation` mono.
- Primary button: solid `primary` + `on-primary` `label-caps` uppercase + hard shadow.
  Secondary button: 1px `ink-graphite` border, transparent fill.
- Tables: horizontal hairlines only, `label-caps` headers, mono numerics.
- Checkboxes/radios square; active fill `primary`.
- Grid: 12 columns, 32px gutter, 64px desktop margins, 8px rhythm.
- `member3/../stitch_fuma_industrial_data_foundry/code.html` is the reference
  implementation for the shell, nav, plates and console log. Match it.

### Structure

```
member3/frontend/
  index.html                 # loads the 3 Google fonts + Material Symbols Outlined
  package.json  vite.config.ts  tsconfig.json  tailwind.config.js  postcss.config.js
  src/
    main.tsx  App.tsx  index.css
    types/api.ts             # TS mirrors of every response in section 3
    services/api.ts          # typed fetch client, one function per endpoint
    hooks/useJobPolling.ts   # polls GET /api/jobs/{id} every 400ms while processing
    components/
      Shell.tsx SideRail.tsx TopBar.tsx
      Plate.tsx              # bordered plate + IDX serial + optional hard shadow
      Button.tsx StatCard.tsx StatusChip.tsx DataTable.tsx
      BarChart.tsx DonutChart.tsx        # hand-rolled SVG, no chart library
      ProgressBar.tsx StageStepper.tsx ConsoleLog.tsx Skeleton.tsx
    pages/
      UploadPage.tsx ProcessingPage.tsx DashboardPage.tsx
      ProductDetailPage.tsx ReviewPage.tsx ExportPage.tsx
```

Routing: hash-free client state in `App.tsx` (`useState` view + jobId + rowId).
Do not add react-router — one state variable covers the six screens.

Charts are hand-rolled SVG (`BarChart`, `DonutChart`) — square terminals, 1.5px
strokes, `primary`/`tertiary`/`secondary` fills only. No chart library, because
rounded default themes would violate the design system.

Loading states use skeleton blocks (`Skeleton.tsx`), never spinners.

### Screens

1. **UploadPage** — `display-hero` "FuMA" wordmark, one-line value prop, square
   drag-and-drop plate, `Browse` + `Load 1,000-row sample` buttons, file name +
   row count + required-column check list, `Start Enrichment` primary button.
   States: empty / selected / validating / invalid / ready.
2. **ProcessingPage** — big mono `processed / total`, square progress bar,
   `StageStepper` over the six stage keys, live success/review/error counters,
   `ConsoleLog` streaming stage transitions.
3. **DashboardPage** — 5 KPI plates (Total, Processed, Success Rate, Needs
   Review, Avg Confidence), 4 quality plates (Invoice, Mobile 60–80, Schema,
   Controlled values — the last renders `N/A — no LOV validator wired`),
   status donut + confidence bar + review-reason bar charts, benchmark panel when
   `metrics.benchmark` is non-null, then the results table (MPN, Part Desc,
   Brand, Product Type, Classpath, Confidence, Status) with search + status
   filter + pagination. Row click opens ProductDetailPage.
4. **ProductDetailPage** — three plates: RAW INPUT | GENERATED | GROUND TRUTH
   (third only when present, else two-up), a quality plate listing every
   validation flag with PASS/FAIL chips, the attribute table, and the five
   descriptions each with a live character counter (`38/40` style) coloured by
   pass state.
5. **ReviewPage** — category filter chips (All + the 7 `REVIEW_CATEGORIES`),
   table of MPN / Confidence / Reasons / Status / Decision, and Approve /
   Reject / Override / Mark Reviewed buttons that POST the decision and update
   the row in place.
6. **ExportPage** — plate showing `Delivery schema: 252 columns`,
   `Validation: PASS|FAIL`, rows ready, rows needing review; Download CSV and
   Download XLSX buttons disabled while validation is FAIL.

## 5. Tests — `member3/tests/`

- `test_delivery.py` — 252 header count, exact order, no duplicates, row width,
  attribute slot mapping, 60-attribute overflow produces a warning and still 252
  columns, ® survives the CSV round-trip, XLSX opens with 252 columns.
- `test_pipeline.py` — happy path on `PDSH4816AF Dishwasher SS - Display Only`,
  M1-before-M2 ordering, forced M2 exception becomes an error RowResult without
  raising, batch of 3 with one poisoned row still returns 3 results.
- `test_api.py` — health 200, valid CSV upload, bad extension rejected, missing
  required column rejected 422, enrich + poll to completion, results pagination,
  row detail, metrics shape, review listing and decision, CSV and XLSX download
  headers and byte prefix.
- `test_review.py` — category filtering, each of the 4 actions, unknown action
  raises.

Every test uses the real `fuma_rules` / `fuma_engine` engines (they are fast and
deterministic — no mocking needed).
