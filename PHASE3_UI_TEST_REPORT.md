# PHASE-3 UI TEST REPORT

**Date:** 2026-06-22  
**Branch:** v1.1.0-dev  
**Baseline:** v1.0.0-FROZEN (commit 5ece4d2)  
**Scope:** app.py — Phase-3 UI integration (Sections 11-15)  
**Result:** **ALL PASS**

---

## 1. CHANGES MADE

| File | Action | Lines Added | Lines Modified |
|------|--------|-------------|----------------|
| `app.py` | Added imports, Phase-3 button, Sections 11-15 | ~175 | 3 (button layout, version string) |
| `depth_map.json` | New file — runtime depth configuration | 3 | — |
| `processor.py` | Previously approved | 28 | 0 |

### Frozen Lines Modified in app.py

| Line | Before | After | Justification |
|------|--------|-------|--------------|
| Import line | `from processor import process_panels, process_panels_optimized` | Added `, process_panels_with_recovery` | Additive import |
| Sidebar title | `SGO v1.0.0-RC1` | `SGO v1.1.0-dev` | Version update |
| Button layout | `st.columns(2)` | `st.columns(3)` | Add Phase-3 button |

**All other existing code unchanged.** Sections 1-10 not modified.

---

## 2. SCREENS RENDERED

### 2.1 Login Page

**Status: UNCHANGED**

- Username/password form
- Version string on login page still shows `Version 1.0.0` (cosmetic, login page is separate)

### 2.2 Sidebar

**Changes:**

| Element | Before | After |
|---------|--------|-------|
| Title | `SGO v1.0.0-RC1` | `SGO v1.1.0-dev` |
| Navigation | `Import & Process`, `Product Catalog` | Unchanged |

### 2.3 Import Page — Button Row

**Before:**

```
[Phase-1: Individual]  [Phase-2: Optimize Project]
```

**After:**

```
[Phase-1: Individual]  [Phase-2: Optimize]  [Phase-3: Recovery]
```

Phase-3 button uses `type="primary"` (highlighted).

### 2.4 Section 11: Recovery Status (Visible by Default)

Rendered immediately after Phase-3 divider.

**Banner:**

```
VALID — 12 / 12 PASS
```

or

```
INVALID — 11 / 12 PASS
```

**Metrics Row 1:**

| Frozen Yield | Recovery Rate | Validation |
|-------------|---------------|------------|
| 92.89% | 100.00% | 12/12 PASS |

**Metrics Row 2:**

| Recovered Area | Dead Scrap Area | Remaining Stock |
|---------------|-----------------|-----------------|
| 1.7400 m² | 0.9375 m² | 3.9150 m² |

**Metrics Row 3:**

| Total Matches | Unmatched Demands |
|--------------|-------------------|
| 1 | 0 |

### 2.5 Section 12: Scrap Inventory (Inside Expander)

**Expander label:** `12. Scrap Inventory`

**Summary metrics:** Stock Pieces=1, Available=1, Depleted=0, Dead Scrap=1

**Stock Pieces table:**

| Piece ID | Source Mark | Product | MCK | Original Width | Remaining Width | Length | Qty | Status |
|----------|-----------|---------|-----|---------------|----------------|--------|-----|--------|
| SP-G04-001 | G04 | TA325/1 | (30.0, 25.0, 5.0) | 390.0 | 270.0 | 1450.0 | 10 | AVAILABLE |

**Dead Scrap table:**

| Scrap ID | Source Mark | Width | Length | Area | Qty | Origin | Reason |
|----------|-----------|-------|--------|------|-----|--------|--------|
| DS-G03-001 | G03 | 30.0 | 1250.0 | 0.0375 | 25 | REDUCTION | Width 30.0mm < 200mm minimum |

### 2.6 Section 13: Recovery Matching (Inside Expander)

**Expander label:** `13. Recovery Matching`

**Matched Demands table:**

| Demand Mark | Product | Expansion | Length | Qty | Stock Piece | Source | Width Before | Width After | Trim | Post Class | Candidates | Decision |
|-------------|---------|-----------|--------|-----|-------------|--------|-------------|-------------|------|-----------|------------|----------|
| G01 | TA325/1 | 120.0 | 1450.0 | 10 | SP-G04-001 | G04 | 390.0 | 270.0 | 270.0 | REUSABLE | 1 | Only compatible stock piece available |

**Unmatched:** `All expansion demands matched.` (st.success)

### 2.7 Section 14: Recovery Validation (Visible by Default)

**Banner:**

```
VALID — 12 / 12 PASS
```

**Validation table:**

| Rule | Description | Status | Detail |
|------|-------------|--------|--------|
| R10 | Strip Classification Complete | PASS | 2 reduction marks, all classified |
| R11 | No Over-Consumption | PASS | 1 stock pieces checked |
| R12 | MCK Verified | PASS | 1 matches verified |
| R13 | Qty Balanced | PASS | 1 stock pieces checked |
| R14 | Recovered Area Consistent | PASS | Sum=1.74 == Total=1.74 |
| R15 | Recovery Rate Bounded | PASS | Recovery Rate = 100.0% |
| R16 | Inventory Balanced | PASS | Total=1, Depleted=0, Available=1 |
| R17 | Dead Scrap Accounted | PASS | Total=1 (REDUCTION=1) |
| R18 | Frozen KPI Unchanged | PASS | Frozen Yield = 92.89% |
| R19 | MCK 3-Field Validation | PASS | 1 matches have complete MCK |
| R20 | Post Consumption Classification | PASS | 1 consumption events validated |
| R21 | Recovery Bounds | PASS | Recovered=1.74 <= Demand=1.74 |

### 2.8 Section 15: Recovery Explainability (Inside Expander)

**Expander label:** `15. Recovery Explainability`

**Entries (each in nested expander):**

```
MATCH APPROVED: G01 -> SP-G04-001
  └─ [st.code block with full MCK check, width check, decision trace]
```

---

## 3. USER WORKFLOW

### Phase-1 Workflow (unchanged)

```
Upload CSV → Click [Phase-1: Individual] → Sections 3-6 → Download CSV
```

### Phase-2 Workflow (unchanged)

```
Upload CSV → Click [Phase-2: Optimize] → Sections 3-10 → Download CSV
```

### Phase-3 Workflow (new)

```
Upload CSV → Click [Phase-3: Recovery] → Sections 3-15 → Download CSV
```

Phase-3 includes all Phase-1 + Phase-2 sections (3-10) plus Phase-3 sections (11-15). Users see the full pipeline in one view.

### Button Behavior

| Button Clicked | Clears Session State | Calls | Sections Shown |
|---------------|---------------------|-------|---------------|
| Phase-1 | All 7 keys | `process_panels()` | 3-6 |
| Phase-2 | All 7 keys | `process_panels_optimized()` | 3-10 |
| Phase-3 | All 7 keys | `process_panels_with_recovery()` | 3-15 |

Switching between phases always clears all session state to prevent stale data.

---

## 4. VALIDATION DISPLAY

### Location

Section 14 — visible by default (not inside expander).

### Display Pattern

Matches existing Phase-2 Validation (Section 10):

1. **Banner** — `st.success("VALID — 12 / 12 PASS")` or `st.error("INVALID — 11 / 12 PASS")`
2. **Table** — `st.dataframe()` with Rule, Description, Status, Detail columns

### VALID vs INVALID Logic

```python
if val_data["all_passed"]:
    st.success(f"**VALID** — {passed} / {total} PASS")
else:
    st.error(f"**INVALID** — {passed} / {total} PASS")
```

Determined by `ValidationReport.all_passed` property (True when `failed == 0`).

---

## 5. RECOVERY DISPLAY

### Visibility Rules

| Section | Default State | Rationale |
|---------|--------------|-----------|
| 11. Recovery Status | **Visible** | Primary status — user needs to see immediately |
| 12. Scrap Inventory | **Expander (collapsed)** | Detail data — expand on demand |
| 13. Recovery Matching | **Expander (collapsed)** | Detail data — expand on demand |
| 14. Recovery Validation | **Visible** | Critical status — user needs to see immediately |
| 15. Recovery Explainability | **Expander (collapsed)** | Audit trail — expand on demand |

### depth_map.json

| Item | Value |
|------|-------|
| File | `depth_map.json` |
| Location | Project root (same directory as app.py) |
| Format | `{"product_code": depth_mm}` |
| Current content | `{"TA325/1": 25.0}` |
| Missing file handling | Returns `None` → R19 fail-closed (0 matches) |
| Invalid format handling | Returns `None` → R19 fail-closed |

---

## 6. REGRESSION CONFIRMATION

### 6.1 Frozen KPI Bit-Exact (re-verified after app.py changes)

| KPI | Phase-1 | Phase-2 | Phase-3 (None) | Phase-3 (depth) | Match |
|-----|---------|---------|----------------|-----------------|-------|
| yield_percent | 92.89 | 92.89 | 92.89 | 92.89 | **PASS** |
| scrap_percent | 7.11 | 7.11 | 7.11 | 7.11 | **PASS** |
| total_sold_area | 86.19 | 86.19 | 86.19 | 86.19 | **PASS** |
| total_production_area | 86.19 | 86.19 | 86.19 | 86.19 | **PASS** |
| total_raw_material_area | 92.7825 | 92.7825 | 92.7825 | 92.7825 | **PASS** |

### 6.2 Frozen Ranking (re-verified)

| Scenario | Start | Score | Selected | Match |
|----------|-------|-------|----------|-------|
| 1 | 20.0 | 1053.44 | YES | **PASS** |
| 2 | 70.0 | 1052.94 | no | **PASS** |
| 3-12 | 120-570 | 1052.44-1047.94 | no | **PASS** |
| 13 | 620.0 | 133.64 | no | **PASS** |
| 14 | 670.0 | 133.14 | no | **PASS** |

All 14 scenario scores and selections bit-exact between Phase-2 and Phase-3.

### 6.3 Frozen Scoring Weights (unchanged in code)

| Weight | Value | Verified |
|--------|-------|----------|
| W_COVERAGE | 1000 | Not modified |
| W_PREFERRED | 500 | Not modified |
| W_ROD | 0.5 | Not modified |
| W_YIELD | 50 | Not modified |
| W_FALLBACK | -100 | Not modified |

### 6.4 Warnings (unchanged)

All 4 processing modes produce `[]` (empty warnings). **PASS.**

### 6.5 App Syntax

```
python -c "import ast; ast.parse(open('app.py').read())" → PASS
```

### 6.6 Streamlit Server

```
curl http://localhost:8501 → HTTP 200 OK
```

### 6.7 UI Data Pipeline (10 programmatic tests)

| Test | Description | Result |
|------|-------------|--------|
| 1 | depth_map.json loads correctly | **PASS** |
| 2 | `_load_depth_map()` returns correct dict | **PASS** |
| 3 | Report has all 7 sections | **PASS** |
| 4 | Executive summary fields correct | **PASS** |
| 5 | Inventory summary balanced | **PASS** |
| 6 | Match summary has correct data | **PASS** |
| 7 | Validation 12/12 PASS | **PASS** |
| 8 | Explainability entries present | **PASS** |
| 9 | Unmatched empty with depth_map | **PASS** |
| 10 | depth_map=None → R19 fail-closed | **PASS** |

---

## 7. LIMITATION

Browser screenshots could not be captured in this session (Chrome extension not connected). All verification was done programmatically:

- Streamlit server starts and responds HTTP 200
- app.py parses without syntax errors
- All report data structures verified correct
- All regression tests pass

**Manual verification recommended:** Open `http://localhost:8501`, log in (admin/1234), upload `sample_data.csv`, click Phase-3: Recovery, and visually confirm Sections 11-15 render correctly.

---

## 8. FILES DELIVERED

| File | Purpose |
|------|---------|
| `app.py` | Updated with Phase-3 UI (Sections 11-15) |
| `depth_map.json` | Runtime depth configuration |
| `processor.py` | Previously approved — `process_panels_with_recovery()` |
| `test_regression.py` | Regression test script |
| `PHASE3_REGRESSION_TEST_REPORT.md` | Processor integration regression report |
| `PHASE3_UI_TEST_REPORT.md` | This document |

---

**END OF REPORT**
