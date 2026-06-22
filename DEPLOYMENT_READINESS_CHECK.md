# SGO v1.2.1 — DEPLOYMENT READINESS CHECK

**Date:** 2026-06-22
**Target:** Streamlit Community Cloud (Public Training/Demo)
**Status:** CONDITIONAL PASS

---

## CHECKLIST

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | requirements.txt complete | PASS | streamlit, pandas, reportlab, openpyxl |
| 2 | runtime.txt exists | PASS | python-3.12 |
| 3 | All imports resolve | PASS | 22 .py files, no missing dependencies |
| 4 | JSON data files committed | PASS | custom_products.json, hidden_products.json, depth_map.json |
| 5 | No hardcoded absolute paths | PASS | All use os.path.dirname(__file__) |
| 6 | Single set_page_config | PASS | Moved to main() — fixes B1 |
| 7 | Filesystem writes handled | PASS | product_store.py returns bool on write failure — fixes B2 |
| 8 | sample_data.csv available | PASS | Ships with repo for demo |
| 9 | .gitignore appropriate | PASS | __pycache__/, *.pyc, stderr.log |
| 10 | PDF export works | PASS | In-memory generation, no filesystem writes |
| 11 | Excel export works | PASS | In-memory generation, no filesystem writes |
| 12 | Login mechanism | CONDITIONAL | Hardcoded credentials — deferred as TD-006 |

---

## BLOCKER STATUS (from original audit)

| Blocker | Original Status | v1.2.1 Status | Resolution |
|---------|----------------|---------------|------------|
| B1: Dual set_page_config | FAIL | FIXED | Single call in main() |
| B2: Filesystem writes | FAIL | FIXED | try/except with bool return |
| B3: Plaintext credentials | FAIL | DEFERRED (TD-006) | Login kept per approval, not a deploy blocker for training/demo |

---

## DEPENDENCY AUDIT

### PyPI Packages

| Package | Required Version | Purpose | Streamlit Cloud Compatible |
|---------|-----------------|---------|---------------------------|
| streamlit | >=1.30.0 | UI framework | YES (native) |
| pandas | >=2.0.0 | Data handling | YES |
| reportlab | >=4.0 | PDF generation | YES (pure Python) |
| openpyxl | >=3.1.0 | Excel generation | YES (pure Python) |

### Python Stdlib (no install needed)

json, os, csv, io, re, dataclasses, typing, collections, datetime

### No native/C dependencies that would fail on Linux (Streamlit Cloud).

---

## FILE MANIFEST

### Required for Deployment (22 files)

| File | Type |
|------|------|
| app.py | Application entry point |
| processor.py | Pipeline orchestrator |
| models.py | Data models |
| product_master.py | Product catalog |
| product_store.py | Custom product persistence |
| csv_importer.py | CSV parser |
| rule_engine.py | Width optimization rules |
| pattern_engine.py | Rod pattern engine |
| clustering_engine.py | Floor grouping |
| optimizer_models.py | Optimization models |
| project_optimizer.py | Project optimizer |
| recovery_models.py | Recovery models |
| recovery_engine.py | Material recovery |
| recovery_validation.py | Recovery validation |
| recovery_report.py | Recovery reporting |
| scrap_inventory.py | Scrap inventory |
| packing_models.py | Packing models |
| packing_engine.py | FFD packing engine |
| packing_validation.py | Packing validation R22-R29 |
| packing_report.py | Packing report |
| export_pdf.py | PDF export |
| export_excel.py | Excel export |

### Required Data Files (3 files)

| File | Content |
|------|---------|
| custom_products.json | Custom product definitions (TA325/1) |
| hidden_products.json | Hidden product codes (empty) |
| depth_map.json | Load bar depth map (TA325/1: 25.0) |

### Required Config Files (2 files)

| File | Content |
|------|---------|
| requirements.txt | Python dependencies |
| runtime.txt | Python version (3.12) |

### Optional Files

| File | Purpose |
|------|---------|
| sample_data.csv | Demo data for users |
| test_regression.py | Regression tests (not needed in prod) |
| *.md | Documentation |
| .gitignore | Git config |

---

## STREAMLIT CLOUD DEPLOYMENT INSTRUCTIONS

### 1. Repository Setup

Push all required files to a GitHub repository (public or private).

### 2. Streamlit Cloud Configuration

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select repository, branch, and main file: `app.py`
4. Deploy

### 3. Streamlit Cloud Settings

No `.streamlit/secrets.toml` required for v1.2.1 (login uses hardcoded creds — TD-006).

### 4. Post-Deploy Verification

1. App loads login page
2. Login with admin/1234
3. Upload sample_data.csv
4. Run Phase-3.2A: Production Plan
5. Verify sections 16-18 render
6. Download PDF and Excel exports
7. Verify PDF opens and contains all pages
8. Verify Excel opens with 4 sheets

---

## KNOWN LIMITATIONS

| # | Limitation | Severity | Tracking |
|---|-----------|----------|----------|
| 1 | Login credentials hardcoded in source | LOW (training/demo) | TD-006 |
| 2 | Product catalog edits lost on cloud restart | LOW | By design (read-only FS) |
| 3 | Session state lost on app restart | LOW | By design (Streamlit) |
| 4 | Single concurrent user session | LOW | Streamlit Cloud limitation |

---

## VERDICT

**CONDITIONAL PASS** — Ready for Streamlit Cloud deployment as a training/demo application.

TD-006 (authentication refactor) should be resolved before any production or multi-user deployment.

---

**END OF REPORT**
