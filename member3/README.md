# FuMA — Member 3: API, Dashboard & 252-Column Delivery

Member 3 is the integration and delivery layer. It turns the Member 1
(`fuma_rules`) and Member 2 (`fuma_engine`) engines into one working system: a
REST API that orchestrates them in the correct order, a dashboard a judge can
drive end to end, and a delivery exporter that emits the client's exact
252-column format.

```
raw row -> M1 normalize -> M2 enrich -> ProductRecord validate
        -> quality/review grading -> 252-column map -> CSV / XLSX
```

## Quick start

```bash
# 1. Environment (keep it OFF an iCloud-synced folder; see Notes)
python3 -m venv ~/.fuma-venv/v1
~/.fuma-venv/v1/bin/pip install -r member3/requirements.txt

# 2. Run the API + dashboard on one process
cd <repo root>
PYTHONPATH=. ~/.fuma-venv/v1/bin/python -m uvicorn member3.backend.main:app --port 8000

# 3. Open http://127.0.0.1:8000/  -> "Use bundled 1,000-row sample" -> Start
```

Frontend development (hot reload, proxies `/api` to port 8000):

```bash
cd member3/frontend && npm install && npm run dev     # http://localhost:5173
npm run build                                          # emits dist/, served by FastAPI at /
```

## Verification

```bash
PYTHONPATH=. ~/.fuma-venv/v1/bin/python -m pytest member3/tests/ -q   # 92 passed
PYTHONPATH=. ~/.fuma-venv/v1/bin/python -m member3.scripts.run_benchmark
```

Measured on the bundled 1,000-row supplier dataset:

| Metric | Result |
|---|---|
| Rows processed / errors | 1000 / **0** |
| Throughput | ~10,000 rows/s |
| `INVOICE_DESC` ≤ 40 chars | **100.0%** |
| `INVOICE_DESC` ALL CAPS | **100.0%** |
| `MOBILE_DESC` schema (0 < len ≤ 85) | **100.0%** |
| `MOBILE_DESC` target 60–80 | 36.6% |
| `ProductRecord` schema validation | **100.0%** |
| Specific (non-generic) classpath | 6.2% |
| Attribute coverage | 44.0% |
| Delivery columns | **252, exact order** |
| Ground-truth master data (brand/mfg/MPN/classpath/product name) | **100% exact** |

### Review policy

A row enters the human-review queue if and only if it carries at least one
review reason. Reasons are assigned for every documented quality gap: Member 2
review flags, missing required fields (`Mfg_Part_Num`, `Part_Desc`,
`Part_Manuf` — such rows never reach the engines and never ship), invoice
length/case violations, mobile descriptions outside the 60–80 client window,
zero extracted attributes, and generic taxonomy fallback. On the bundled
dataset that policy flags **953 / 1000 rows** for review and 47 ship clean —
the queue and the reasons column are therefore always mutually consistent, and
a row with a documented problem can never silently pass as a clean success.

The low numbers are reported, not hidden. Member 2's rule-based extractor
covers a handful of categories in depth, so most of the 1,000 rows fall back to
a generic classpath and carry no attributes. Those rows are flagged for human
review rather than shipped as if they were complete, which is the honest
behaviour the brief asks for.

### Two mobile KPIs, on purpose

`ProductRecord` allows `mobile_desc` up to 85 characters while the client target
is 60–80. Reporting one number would overstate compliance, so the API and the
dashboard expose both `schema_mobile_pass` and `mobile_target_60_80_pass` as
separately labelled figures. An empty mobile description passes neither metric.

## Layout

```
member3/
├── backend/
│   ├── main.py                     FastAPI app; serves /api + the built SPA (containment-checked)
│   ├── models/api_models.py        request bodies (responses are plain dicts)
│   ├── routes/api.py               all 13 endpoints
│   └── services/
│       ├── pipeline_service.py     M1 -> M2 -> validate, per-row error isolation
│       ├── batch_service.py        job store + threaded batch runner
│       └── metrics_service.py      KPIs, histograms, ground-truth benchmark
├── delivery/
│   ├── columns.py                  the 252-header contract (generated, do not edit)
│   ├── mapper.py                   record -> delivery row, fixed 50 attribute slots
│   ├── validators.py               header/row gate, blocks malformed exports
│   ├── csv_exporter.py             utf-8-sig CSV
│   └── xlsx_exporter.py            OpenPyXL, bold header, freeze panes, autofilter
├── frontend/                       Vite + React + TS, Industrial Modernist UI
├── scripts/run_benchmark.py        the pitch scorecard
├── tests/                          92 tests: pipeline, delivery, metrics, security, end-to-end
└── data/                           bundled sample + expected delivery format
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + delivery column count |
| POST | `/api/upload` | multipart CSV/XLSX, validates the six required columns |
| POST | `/api/demo/sample` | load the bundled 1,000-row dataset |
| POST | `/api/enrich` | start the batch (returns immediately) |
| GET | `/api/jobs/{id}` | status and counters for progress polling |
| GET | `/api/jobs/{id}/results` | paginated rows (`page`, `page_size`, `status`, `search`) |
| GET | `/api/jobs/{id}/results/{row_id}` | one row + ground truth when known |
| GET | `/api/jobs/{id}/metrics` | KPIs, charts, benchmark |
| GET | `/api/jobs/{id}/review` | the human-review queue |
| POST | `/api/jobs/{id}/review/{row_id}` | `approve` / `reject` / `override` / `mark_reviewed` |
| GET | `/api/jobs/{id}/export/status` | pre-download validation gate |
| GET | `/api/jobs/{id}/export.csv` | validated 252-column CSV |
| GET | `/api/jobs/{id}/export.xlsx` | validated 252-column XLSX |

Errors use one shape: `{"error": {"code", "message", "row_id", "details"}}`.

## Design guarantees

- **252 columns, always.** Every row starts as `{col: "" for col in DELIVERY_COLUMNS}`, so the width is structural rather than a thing the mapper has to remember. `columns.py` is generated from `data/expected_delivery_format.csv` and asserts its own length and uniqueness at import.
- **Fixed 50 attribute slots.** More than 50 attributes keeps the first 50 and records a warning; a 253rd column is impossible by construction.
- **Nothing invented.** Columns with no source (`UPC`, `Warranty`, `Country Of Origin`, ...) stay empty instead of being filled with plausible-looking values. Rows missing a required business field (`Mfg_Part_Num`, `Part_Desc`, `Part_Manuf`) are queued for review with confidence 0 and are **excluded from the delivery file** — a blank-MPN row can never ship.
- **`®` and `™` survive.** CSV is written `utf-8-sig` so Excel renders trademarks correctly; XLSX writes every cell as text.
- **One bad row never kills a batch.** Each stage is wrapped; a failure becomes an `error` row with the reason attached and the run continues.
- **The queue never lies.** `needs_review` is true exactly when a review reason exists, so the review queue, the reasons column and the category filters always agree.

## Notes

- Member 3 never edits `fuma_rules/` or `fuma_engine/`, and does not duplicate brand, UOM, taxonomy or description logic.
- Keep the venv and `npm run build` off iCloud-synced folders such as `~/Desktop`. File-provider sync makes `import openpyxl` and Vite builds take minutes there; from a local path they take under a second.
