# FuMA Member 3 — API, Dashboard & 252-Column Delivery Implementation Plan

> **For agentic workers:** implement your assigned task only. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship the Member 3 layer of FuMA: a FastAPI backend that orchestrates Member 1 (`fuma_rules`) then Member 2 (`fuma_engine`), a validated exact-252-column CSV/XLSX exporter, and an Industrial-Modernist React dashboard with diff viewer, review queue, metrics and export center.

**Architecture:** `raw row -> M1 normalize -> M2 enrich -> ProductRecord validate -> quality/review -> 252-col map -> CSV/XLSX`. Jobs live in an in-process registry. The frontend is a Vite + React + TS SPA calling `/api`.

**Tech Stack:** FastAPI, uvicorn, pydantic v2, pandas, openpyxl, pytest, httpx; Vite + React 19 + TypeScript + Tailwind v3 (CDN-free build), Recharts.

## Global Constraints

- Member 3 code lives **only** under `member3/`. Never edit `fuma_rules/` or `fuma_engine/`.
- Delivery export is **exactly 252 columns**, exact names, exact order, from `member3/delivery/columns.py` (already generated, verified byte-equal to `member3/data/expected_delivery_format.csv`). Never hand-edit it.
- Attribute block is fixed at **50 slots** (`ATTRIBUTE_LABEL/VALUE/UOM 1..50`). More than 50 attributes -> keep first 50, add review reason, never add a 253rd column.
- UTF-8 everywhere; `®` and `™` must survive export.
- One bad row must never abort a batch.
- Two separate mobile KPIs, no conflation: `schema_mobile_pass` (<= 85, the current `ProductRecord` limit) and `mobile_target_60_80_pass` (strict 60-80 target).
- Design system is `DESIGN.md` Industrial Modernist: **0px radius everywhere**, no gradients, no glows, no blur. Cream `#fcf9f2` base, charcoal `#34332F` ink, terracotta `#994422` accent used sparingly. Fonts: Instrument Serif (headlines), Manrope (body/UI), IBM Plex Mono (all data/labels). Depth = 1px borders + hard offset shadow `2px 2px 0 #171715`, never soft shadows.
- Python entry: `python -m uvicorn member3.backend.main:app`. Run everything with `.venv/bin/python` from repo root.
- Commit after each task with the `feat(m3): ...` prefix.

---

## Frozen Interfaces (all tasks depend on these exact names)

```python
# member3/delivery/columns.py  (DONE, do not modify)
DELIVERY_COLUMNS: List[str]      # exactly 252, exact order
DELIVERY_COLUMN_COUNT = 252
ATTRIBUTE_SLOTS = 50
LEADING_COLUMNS: List[str]
TRAILING_COLUMNS: List[str]

# member3/backend/services/pipeline_service.py   (Task 1)
def enrich_raw_row(raw_row: dict, row_id: int = 0) -> dict
# returns RowResult-shaped dict:
# {
#   "row_id": int,
#   "status": "success" | "review" | "error",
#   "raw": dict,                # original input row
#   "normalized": dict,         # M1 output (JSON-safe)
#   "enriched": dict,           # ProductRecord.model_dump() or {}
#   "validation": {"schema_valid": bool, "errors": [str],
#                  "invoice_len": int, "invoice_caps": bool,
#                  "mobile_len": int, "schema_mobile_pass": bool,
#                  "mobile_target_pass": bool, "attribute_count": int},
#   "review": {"needs_review": bool, "reasons": [str],
#              "decision": None | "approve" | "reject" | "override" | "mark_reviewed",
#              "comment": str},
#   "confidence": float,
# }
REQUIRED_INPUT_COLUMNS: list[str]   # ["Mfg_Part_Num","Part_Desc","E1_Brand","Unilog_Brand","DIB_Brand","Part_Manuf"]
def validate_input_columns(fieldnames: list[str]) -> list[str]   # returns missing columns

# member3/delivery/mapper.py   (Task 2)
def map_to_delivery_row(result: dict) -> dict          # dict keyed by DELIVERY_COLUMNS, 252 keys
def map_rows(results: list[dict]) -> list[dict]

# member3/delivery/validators.py   (Task 2)
class DeliveryValidationError(Exception)
def validate_delivery_headers(headers: list[str]) -> None       # raises on mismatch
def validate_delivery_rows(rows: list[dict]) -> dict            # {"valid": bool, "errors": [str], "row_count": int}

# member3/delivery/csv_exporter.py / xlsx_exporter.py   (Task 2)
def export_csv(rows: list[dict]) -> bytes
def export_xlsx(rows: list[dict]) -> bytes

# member3/backend/services/batch_service.py   (Task 3)
class JobStore:  # singleton via get_job_store()
    def create_job(filename: str, rows: list[dict]) -> dict
    def get(job_id: str) -> dict | None
    def run_job(job_id: str) -> dict
    def list_results(job_id, page, page_size, status, search) -> dict
    def get_result(job_id, row_id) -> dict | None
    def set_review(job_id, row_id, action, comment) -> dict
def get_job_store() -> JobStore

# member3/backend/services/metrics_service.py   (Task 3)
def compute_metrics(results: list[dict]) -> dict
def compute_benchmark(results: list[dict], ground_truth: list[dict]) -> dict

# API base path: /api   (Task 4)
GET  /api/health
POST /api/upload                        -> {job_id, filename, rows, status}
POST /api/enrich   {job_id, mode}       -> {job_id, status}
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/results?page&page_size&status&search
GET  /api/jobs/{job_id}/results/{row_id}
GET  /api/jobs/{job_id}/metrics
GET  /api/jobs/{job_id}/review
POST /api/jobs/{job_id}/review/{row_id} {action, comment}
GET  /api/jobs/{job_id}/export.csv
GET  /api/jobs/{job_id}/export.xlsx
POST /api/demo/sample                   -> loads bundled 1000-row sample as a job
```

Job status values: `uploaded | queued | processing | completed | completed_with_review | failed | exported`.

---

### Task 1: Pipeline orchestration service

**Files:** Create `member3/backend/services/pipeline_service.py`, `member3/tests/test_pipeline.py`

M1 is `MasterDataPipelineStage().process_item(raw)` from `fuma_rules.stage1_master_data`, returning the raw dict plus `CLEAN_DESC / MANUFACTURER_NAME / BRAND_NAME / MANUFACTURER_PART_NUMBER / STANDARDIZED_DIMENSIONS / STAGE1_STATUS`. M2 is `enrich_single_item(normalized)` from `fuma_engine.pipeline_interface`, which reads `MANUFACTURER_NAME`/`BRAND_NAME` keys, so M1 output feeds straight in. Wrap each stage in try/except; on exception return `status="error"` with the reason in `review.reasons`, never raise. Re-validate the M2 dict through `ProductRecord(**enriched)` and record schema errors.

Tests: happy path on `PDSH4816AF Dishwasher SS - Display Only` asserts brand `FRIGIDAIRE®`, invoice <= 40 and uppercase, schema_valid True; a monkeypatched exploding M2 yields `status="error"` and does not raise; `validate_input_columns` reports missing columns.

### Task 2: Delivery mapper, validators, CSV + XLSX exporters

**Files:** Create `member3/delivery/mapper.py`, `validators.py`, `csv_exporter.py`, `xlsx_exporter.py`, `member3/tests/test_delivery.py`

Mapper starts from `{col: "" for col in DELIVERY_COLUMNS}` so width is structurally guaranteed. Fill passthrough raw columns (`Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf` and `Dept/Class/Fine/SKU - MY_PART_NUMBER/PART_NUMBER` when present in raw), then M1/M2 fields: `MANUFACTURER_NAME, BRAND_NAME, MANUFACTURER_PART_NUMBER, Classpath, UNSPSC, MOBILE_DESC, INVOICE_DESC, SHORT_DESC, LONG_DESC1, RETAIL_DESC, Product Name`, features into `ITEM_FEATURES_1..20`, attributes into the 50 slots. Unknown/unsourced columns stay empty strings, never invented. XLSX via openpyxl with bold header, freeze `A2`, autofilter; force text write so `®` survives. `export_csv` uses `utf-8-sig` so Excel opens it correctly.

Tests: 252 headers exact and ordered; row width 252; no duplicate headers; 60 attributes keeps only 50 and returns an overflow warning; `®` round-trips through both CSV and XLSX.

### Task 3: Job store, batch runner, metrics + benchmark

**Files:** Create `member3/backend/services/batch_service.py`, `metrics_service.py`, `review_service.py`, `member3/tests/test_batch_metrics.py`

In-memory store keyed by `job_YYYYMMDD_HHMMSS_xxxx`. `run_job` iterates rows, calls `enrich_raw_row`, updates counters (`processed/success/review/errors/progress`), and finishes as `completed` or `completed_with_review`. Metrics return: totals, success rate, avg confidence, `invoice_char_pass`, `invoice_caps_pass`, `schema_mobile_pass`, `mobile_target_60_80_pass`, `schema_pass_rate`, `classpath_specific_rate`, `attribute_coverage`, confidence histogram (buckets of 10), review-reason counts, status distribution, elapsed seconds. Benchmark joins generated rows to ground truth by `Mfg_Part_Num` and reports per-field exact + normalized match rates for the 11 core fields.

### Task 4: FastAPI app, routes, API models

**Files:** Create `member3/backend/main.py`, `member3/backend/models/api_models.py`, `member3/backend/routes/{health,upload,enrich,results,metrics,review,export,demo}.py`, `member3/tests/test_api.py`

CORS open for `localhost:5173`. Upload: reject non-`.csv/.xlsx`, reject empty, reject missing required columns with the documented error envelope, cap at 8 MB, sanitize filename, server-generated job ids. Export routes 409 when the delivery validator fails. Static-mount the built frontend at `/` when `member3/frontend/dist` exists so one process serves everything.

### Task 5: Frontend — shell, design tokens, upload, processing

**Files:** `member3/frontend/` Vite scaffold, `tailwind.config.js` (tokens copied verbatim from `DESIGN.md` front-matter), `src/api/client.ts`, `src/types.ts`, `src/App.tsx`, `src/components/{AppShell,SideNav,TopBar,Plate,StatChip}.tsx`, `src/pages/{UploadPage,ProcessingPage}.tsx`

Match `stitch_fuma_industrial_data_foundry/code.html`: collapsible 80px->256px left rail, 64px top bar, technical plates with `IDX-nn` serials, mono labels, hard shadows. Drag-and-drop upload with the five states, row-count preview, required-column validation, and a "Use bundled 1,000-row sample" action. Processing page shows the stage stepper and live counters by polling `/api/jobs/{id}`.

### Task 6: Frontend — dashboard, diff viewer, review queue, export center

**Files:** `src/pages/{DashboardPage,ProductDetailPage,ReviewPage,ExportPage}.tsx`, `src/components/{KpiGrid,QualityGrid,ResultsTable,ConfidenceChart,StatusChart,DiffPanel,ReviewFilters}.tsx`

Dashboard: KPI plates, quality plates (both mobile KPIs labelled distinctly), Recharts bar/histogram in palette colors only, searchable paginated results table (7 columns max). Detail: raw | generated | ground-truth三-column when GT exists, changed fields marked with a terracotta left rule, attribute table, review reasons, full 252-column drawer. Review: filter chips by reason, approve/override/mark-reviewed posting to the API. Export: 252-column validation banner, row counts, CSV + XLSX download buttons disabled on validation failure.

### Task 7: End-to-end verification, benchmark run, README

**Files:** `member3/tests/test_e2e.py`, `member3/README.md`, `member3/scripts/run_benchmark.py`

Boot the API with httpx ASGI transport, upload the bundled 1,000-row CSV, enrich, assert 1000 processed with zero unhandled crashes, pull metrics, download CSV + XLSX, re-parse both and assert 252 columns and 1000 data rows. Benchmark script prints the scorecard against the 2 bundled ground-truth rows.
