# 🏭 FuMA — Industrial Product Data Enrichment Engine
> **"From Messy Feeds to Master-Class Catalogs."**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Tests](https://img.shields.io/badge/Tests-98%20Passed-brightgreen.svg)]()
[![Schema](https://img.shields.io/badge/Delivery%20Contract-252%20Columns-orange.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

🌐 **Live Cloud Demo**: [https://fuma-8i7c.onrender.com/](https://fuma-8i7c.onrender.com/)  
📖 **Interactive API Swagger Docs**: [https://fuma-8i7c.onrender.com/docs](https://fuma-8i7c.onrender.com/docs)

---

## 📌 Executive Summary

**FuMA** is an automated, enterprise-grade AI and deterministic NLP enrichment engine engineered specifically for industrial MRO (Maintenance, Repair, and Operations) catalogs. It converts messy, incomplete, and noisy distributor product feeds into fully structured, normalized, and audit-ready master catalogs.

### 🌟 Core Capabilities
1. **7-Tier Evidence-Ranked Entity Resolution**: Normalizes noisy supplier/distributor brands against a 27,000-brand master registry with canonical legal trademark handling (`®`, `™`).
2. **Universal Spec & Fraction Parsing**: Context-free mathematical token grammar extracts complex dimensions (`1/2"x18"`, `1-1/4"`, `0.375"`, `5"x.045"x7/8"`), engineering units (`V`, `A`, `W`, `HP`, `RPM`, `CFM`, `gpm`, `psi`, `dBA`), materials, and finishes.
3. **Hierarchical Taxonomy Classification**: Maps unstructured text to a 4-tier UNSPSC-compliant taxonomy hierarchy across 35+ industrial categories (**99.4% specific classpath rate**).
4. **Multi-Channel NLG Description Generation**:
   - `INVOICE_DESC`: **Guaranteed $\le 40$ characters & ALL CAPS** with deterministic abbreviation.
   - `MOBILE_DESC`: Adaptive 60–80 character search-optimized titles.
   - `SHORT_DESC` & `LONG_DESC1`: Clean structured specification chains.
   - `MARKETING_DESCRIPTION`: Grounded 2-sentence B2B summaries built strictly on verified facts.
   - `ITEM_FEATURES_1..20`: Structured bullet point extraction without synthetic filler claims.
5. **Strict 252-Column Delivery Contract**: Generates immutable 252-column tabular exports (CSV `utf-8-sig` & XLSX) with 50 dedicated attribute triplets.
6. **Human-in-the-Loop (HITL) Review Queue**: Scores confidence (0–100) per item and transparently routes ambiguous supplier records into an interactive review queue with 3-way visual diffing.

---

## 🏗️ Architecture & Pipeline Flow

```
                      RAW SUPPLIER CSV / XLSX
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────┐
 │ STEP 1: Normalization & Master Data (fuma_rules/)             │
 │ • 7-Tier Brand Matcher with Trademark Rules                   │
 │ • Distributor Suffix / Prefix Sanitization                    │
 │ • Standardized Units of Measure (UOM)                         │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────┐
 │ STEP 2: Enrichment & Classification (fuma_engine/)            │
 │ • 4-Tier UNSPSC Taxonomy Classifier                           │
 │ • Universal Fraction & Spec Information Extractor             │
 │ • Multi-Channel NLG Description & Feature Synthesizer         │
 │ • Verified First-Party Provenance URLs (MFR URL / Ref URLs)   │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────┐
 │ STEP 3: Quality Scoring & Delivery Contract (member3/)        │
 │ • Quality Confidence Evaluator (0–100 Score & Review Flags)   │
 │ • 252-Column Delivery Mapper (CSV utf-8-sig & XLSX Formatter) │
 │ • FastAPI Async Batch Service & Industrial Modernist React UI │
 └───────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quickstart: Running on Localhost

Judges can run the complete application locally using **one unified command** or in **development mode**.

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`

---

### 🚀 Recommended: Run Unified Full-Stack App (1 Command)

```bash
# 1. Clone the repository
git clone https://github.com/satyam-prakash/FuMA-UniHack.git
cd FuMA-UniHack

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Build the React frontend
cd member3/frontend
npm install
npm run build
cd ../..

# 4. Start the unified server (FastAPI serves both API and React UI)
uvicorn member3.backend.main:app --host 127.0.0.1 --port 8000
```

👉 Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!
- Click **"Use bundled 1,000-row sample"** $\to$ **"Start Enrichment"** to process the 1,000-row benchmark.
- Access API documentation directly at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

---

### 🛠️ Alternative: Run in Development Mode (Hot Reloading)

If you want live hot-reloading for frontend or backend development:

**Terminal 1 (FastAPI Backend)**:
```bash
uvicorn member3.backend.main:app --reload --port 8000
```

**Terminal 2 (React Frontend Dev Server)**:
```bash
cd member3/frontend
npm install
npm run dev -- --port 5173
```
👉 Open **[http://127.0.0.1:5173](http://127.0.0.1:5173)** in your browser.

---

## 🧪 Automated Verification & Pitch Benchmark

Run the full automated test suite (98 tests across schema, taxonomy, fractions, delivery columns, and API endpoints):

```bash
# Run pytest test suite
python -m pytest member3/tests/ -v

# Run the comprehensive benchmark scorecard across 1,000 rows
python -m member3.scripts.run_benchmark
```

### 📊 Benchmark Scorecard (1,000 Industrial Rows)

| Metric | Measured Value | Requirement / Benchmark Status |
|---|---|---|
| **Pipeline Stability** | **1,000 / 1,000 (0 errors)** | 🟢 **100% Pass** (Zero unhandled exceptions) |
| **`INVOICE_DESC` Compliance** | **100.0%** | 🟢 **100% Pass** ($\le 40$ chars & ALL CAPS) |
| **`MOBILE_DESC` Schema Compliance** | **100.0%** | 🟢 **100% Pass** ($\le 85$ chars) |
| **`MOBILE_DESC` Target Window** | **98.1%** | 🟢 **Pass** (60–80 chars, no synthetic filler) |
| **Specific Classpath Coverage** | **99.4%** | 🟢 **Pass** (Specific 4-tier leaf nodes) |
| **Attribute Coverage** | **100.0%** (5.4 attrs/row) | 🟢 **Pass** (Zero empty attribute records) |
| **Delivery Columns Contract** | **252 Columns Locked** | 🟢 **Pass** (CSV & XLSX exports) |
| **Throughput** | **~190 rows / second** | 🟢 **~5.2s for 1,000 rows** on standard CPU |

---

## 📁 Repository Structure

```text
FuMA-UniHack/
├── fuma_rules/                     # Member 1: Master Data & Entity Normalization
│   ├── brand_matcher.py            # 7-tier evidence-ranked brand entity resolver
│   ├── sanitizer.py                # Supplier token & prefix/suffix sanitizer
│   ├── uom_standardizer.py         # Engineering unit of measure standardizer
│   └── reference_data.py           # Master reference catalog loaders
│
├── fuma_engine/                    # Member 2: Classification, Extraction & NLG
│   ├── taxonomy_classifier.py      # 4-tier UNSPSC-compliant taxonomy engine
│   ├── attribute_extractor.py      # Universal dimension, fraction & spec parser
│   ├── description_builder.py      # Multi-channel NLG generator (Invoice, Mobile, etc.)
│   ├── sourcing_engine.py          # Verified 1st-party manufacturer provenance URLs
│   ├── confidence_evaluator.py     # Quality scoring & review reason heuristics
│   └── schema.py                   # Pydantic ProductRecord validation schema
│
├── member3/                        # Member 3: Delivery Contract, API & Dashboard
│   ├── backend/                    # FastAPI orchestration backend
│   │   ├── main.py                 # Application entrypoint & SPA static router
│   │   ├── routes/api.py           # Ingestion, enrichment, review & export endpoints
│   │   └── services/               # Batch job worker & quality metrics calculators
│   ├── delivery/                   # Strict 252-column tabular exporters
│   │   ├── mapper.py               # 252-column row constructor
│   │   ├── csv_exporter.py         # UTF-8-sig CRLF CSV generator
│   │   └── xlsx_exporter.py        # Openpyxl formatted workbook generator
│   ├── frontend/                   # Modernist React SPA (TailwindCSS + TypeScript)
│   │   └── src/                    # Ingest, diffing dashboard, review queue
│   ├── data/                       # Bundled 1,000-row sample & benchmark ground truth
│   └── tests/                      # 98 comprehensive automated unit & regression tests
│
├── Dockerfile                      # Multi-stage production container build
├── render.yaml                     # 1-click cloud deployment blueprint
└── requirements.txt                # Python dependencies
```

---

## 👥 Team & Architecture Roles

* **Member 1 (Master Data & Normalization)**: Brand entity resolution, legal trademark normalization, distributor code sanitization, UOM standardizer.
* **Member 2 (Enrichment Engine)**: Taxonomy classification, universal fraction & attribute extraction, multi-channel NLG, verified provenance URLs, confidence evaluator.
* **Member 3 (System Integration & Delivery)**: FastAPI async batch orchestration, 252-column CSV/XLSX delivery mapper, Industrial Modernist React UI, and test suite.

---
**FuMA** — Built for Hack2skill & Unilog Hackathon.
