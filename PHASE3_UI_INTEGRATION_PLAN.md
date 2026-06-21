# PHASE-3 UI INTEGRATION PLAN

**Date:** 2026-06-22  
**Branch:** v1.1.0-dev  
**Scope:** app.py — Add Phase-3 Material Recovery sections  
**Constraint:** No dashboard redesign. No Plotly. No Phase-3.2 features.

---

## 1. NEW SECTIONS TO ADD

Five new sections (11-15), following the existing numbering (Sections 1-10 are frozen).

| Section | Title | Data Source | Purpose |
|---------|-------|-------------|---------|
| 11 | Recovery Status | `recovery_report["executive_summary"]` | Top-level VALID/INVALID banner + key recovery metrics |
| 12 | Scrap Inventory | `recovery_report["inventory_summary"]` | Stock pieces and dead scrap tables |
| 13 | Recovery Matching | `recovery_report["match_summary"]` + `["unmatched_summary"]` | Match results and unmatched demands |
| 14 | Recovery Validation | `recovery_report["validation_summary"]` | R10-R21 rule results table |
| 15 | Recovery Explainability | `recovery_report["explainability"]` | Worked examples in expandable blocks |

---

## 2. PLACEMENT IN EXISTING UI

### Current Layout

```
render_import_page()
│
├── 1. Upload CSV
├── 2. Raw Data Preview
├── [Phase-1] / [Phase-2: Optimize] / [Phase-3: Recovery]   ← ADD BUTTON
├── Warnings
├── 3. Project KPI Summary
├── 4. Detailed Results
├── 5. Pattern Audit
├── 6. Pattern Details — All Candidates
├── 7. Project Optimization Summary        (Phase-2 only)
├── 8. Floor Group Detail Report           (Phase-2 only)
├── 9. Scenario Comparison                 (Phase-2 only)
├── 10. Phase-2 Validation                 (Phase-2 only)
│
├── ─── NEW DIVIDER ───                    (Phase-3 only)
│
├── 11. Recovery Status                    (Phase-3 only)  ← NEW
├── 12. Scrap Inventory                    (Phase-3 only)  ← NEW
├── 13. Recovery Matching                  (Phase-3 only)  ← NEW
├── 14. Recovery Validation                (Phase-3 only)  ← NEW
├── 15. Recovery Explainability            (Phase-3 only)  ← NEW
│
└── Download Results CSV
```

### Button Layout Change

Current:

```python
col_btn1, col_btn2 = st.columns(2)
# [Phase-1: Individual]  [Phase-2: Optimize Project]
```

Proposed:

```python
col_btn1, col_btn2, col_btn3 = st.columns(3)
# [Phase-1: Individual]  [Phase-2: Optimize]  [Phase-3: Recovery]
```

The Phase-3 button calls `process_panels_with_recovery()` and stores the recovery results in `st.session_state`. Phase-3 always includes Phase-2 (it calls `process_panels_optimized()` internally), so Sections 7-10 also appear.

### Visibility Rules

| Condition | Sections Shown |
|-----------|---------------|
| Phase-1 clicked | 3-6 |
| Phase-2 clicked | 3-10 |
| Phase-3 clicked | 3-15 |

Phase-3 sections are gated by:

```python
if "recovery_report" in st.session_state:
    # Sections 11-15
```

---

## 3. STREAMLIT COMPONENTS TO USE

All components match existing patterns already used in Sections 1-10.

| Component | Usage | Existing Precedent |
|-----------|-------|--------------------|
| `st.subheader()` | Section headers (11-15) | Sections 3-10 |
| `st.metric()` | Recovery KPIs (recovery rate, areas) | Section 3, 7 |
| `st.dataframe()` | Tables (inventory, matches, validation) | Sections 4, 5, 9, 10 |
| `st.success()` / `st.error()` | VALID/INVALID banner | Section 10 |
| `st.expander()` | Expandable explainability blocks | Section 8 |
| `st.columns()` | Metric layout | Sections 3, 7, 8 |
| `st.caption()` | Footnotes and formulas | Sections 3, 6, 9 |
| `st.markdown()` | Inline text and formatting | Throughout |
| `st.info()` / `st.warning()` | Contextual alerts | Catalog page |
| `st.divider()` or `st.markdown("---")` | Phase-3 separator | Between sections |

**No new dependencies.** No Plotly. No custom CSS. No JavaScript.

---

## 4. BACKWARD COMPATIBILITY IMPACT

| Concern | Impact |
|---------|--------|
| Existing `process_panels` import | **UNCHANGED** — still imported, still used by Phase-1 button |
| Existing `process_panels_optimized` import | **UNCHANGED** — still imported, still used by Phase-2 button |
| New import: `process_panels_with_recovery` | **ADDITIVE** — new import from processor.py |
| Session state keys | **ADDITIVE** — new keys (`recovery_summary`, `validation_report`, `recovery_report`). Existing keys (`processed`, `summary`, `opt_summary`, `warnings`) unchanged. |
| Phase-1 button behavior | **UNCHANGED** — calls `process_panels()`, shows Sections 3-6 |
| Phase-2 button behavior | **UNCHANGED** — calls `process_panels_optimized()`, shows Sections 3-10 |
| CSV export | **UNCHANGED** — exports same `df_result` regardless of phase |
| Login page | **UNCHANGED** |
| Catalog page | **UNCHANGED** |
| `_run_validation()` | **UNCHANGED** — Phase-2 validation (Rules 1-9) |
| Version string | Update sidebar: `SGO v1.0.0-RC1` → `SGO v1.1.0-dev` |

### Session State Map

```
Existing (frozen):              New (additive):
  st.session_state["processed"]   st.session_state["recovery_summary"]
  st.session_state["summary"]     st.session_state["validation_report"]
  st.session_state["warnings"]    st.session_state["recovery_report"]
  st.session_state["opt_summary"] st.session_state["depth_map"]
```

When a new processing button is clicked, ALL session state keys (existing + new) are cleared before re-processing. This prevents stale Phase-3 data from persisting when switching to Phase-1.

---

## 5. USER WORKFLOW IMPACT

### Current Workflow

```
Upload CSV → Click Phase-1 or Phase-2 → View Results → Download CSV
```

### New Workflow

```
Upload CSV → Click Phase-1 or Phase-2 or Phase-3 → View Results → Download CSV
```

The only change is a third button. Users who never click Phase-3 see zero difference.

### depth_map Input

Phase-3 requires `depth_map` to produce actual matches. Two options for providing it:

**Option A: Hardcoded depth_map for known products (Recommended for Phase-3.1)**

```python
DEPTH_MAP = {
    "TA325/1": 25.0,
    # Add more as needed
}
```

Stored as a module-level constant in app.py. Simple, deterministic, no UI needed.

**Option B: UI input (deferred to Phase-3.2)**

A sidebar input or expander where users enter depth per product code. More flexible but more complex.

**Recommendation:** Use Option A for Phase-3.1. The depth_map is a small known set. Add a `st.info()` note explaining that depth data is configured, with the current mapping displayed.

---

## 6. VALIDATION DISPLAY STRATEGY

### Location

Section 14, after Recovery Matching (Section 13).

### Layout

Mirrors the existing Phase-2 Validation display (Section 10):

```
st.subheader("14. Recovery Validation (R10-R21)")

if all_passed:
    st.success("RECOVERY VALIDATION: ALL PASS (12/12)")
else:
    st.error(f"RECOVERY VALIDATION: {passed}/{total} PASSED")

st.dataframe(validation_table)  # Rule ID | Description | Status | Detail
```

### Table Columns

| Column | Source |
|--------|-------|
| Rule | `rule_id` (R10-R21) |
| Description | `description` |
| Status | `status` (PASS/FAIL) |
| Detail | `detail` |

### Color Coding

No custom styling — the existing `st.dataframe()` pattern is sufficient. The banner (`st.success` / `st.error`) provides the visual signal.

---

## 7. RECOVERY STATUS DISPLAY STRATEGY

### Location

Section 11, immediately after the Phase-3 divider. This is the first thing users see in the Phase-3 section.

### Layout

```
st.markdown("---")
st.header("Phase-3: Material Recovery Report")

st.subheader("11. Recovery Status")

# Banner
if status == "VALID":
    st.success("RECOVERY STATUS: VALID — All validation rules passed")
else:
    st.error("RECOVERY STATUS: INVALID — Validation failures detected")

# Key Metrics Row 1
col1, col2, col3 = st.columns(3)
col1.metric("Frozen Yield", "92.89%")
col2.metric("Recovery Rate", "100.0%")
col3.metric("Validation", "12/12 PASS")

# Key Metrics Row 2
col4, col5, col6 = st.columns(3)
col4.metric("Recovered Area", "1.74 m²")
col5.metric("Dead Scrap Area", "0.9375 m²")
col6.metric("Remaining Stock", "3.915 m²")

# Key Metrics Row 3
col7, col8 = st.columns(2)
col7.metric("Total Matches", "1")
col8.metric("Unmatched Demands", "0")
```

### Design Principle

Frozen Yield is displayed first to emphasize that it has not changed. Recovery metrics are shown alongside but clearly separate.

---

## 8. EXPLAINABILITY DISPLAY STRATEGY

### Location

Section 15, the final Phase-3 section.

### Layout

Each explainability entry is rendered inside an `st.expander()`, grouped by type:

```
st.subheader("15. Recovery Explainability")

# Group by type
for entry in explainability_entries:
    if entry["type"] == "MATCH_APPROVED":
        icon = "✅"
    elif entry["type"] == "MATCH_REJECTED":
        icon = "❌"
    elif entry["type"] == "INVENTORY_RECLASSIFIED":
        icon = "♻️"
    elif entry["type"] == "UNMATCHED":
        icon = "⚠️"

    label = f"{icon} {entry['type']}: {entry['demand_mark']}"
    if entry.get("stock_piece_id"):
        label += f" ↔ {entry['stock_piece_id']}"

    with st.expander(label):
        st.code(entry["text"], language=None)
```

### Design Principles

1. **Collapsed by default** — Users expand only the entries they want to audit.
2. **`st.code()` for monospace** — The explainability text is pre-formatted with alignment. Monospace preserves the layout.
3. **Type-based icons** — Quick visual scanning without reading the text.
4. **No filtering** — For Phase-3.1, all entries are shown. Filtering is Phase-3.2.

---

## 9. SECTION DETAIL SPECIFICATIONS

### Section 12: Scrap Inventory

Two sub-tables inside one section.

```
st.subheader("12. Scrap Inventory")

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Stock Pieces", total_stock)
col2.metric("Available", available)
col3.metric("Depleted", depleted)
col4.metric("Dead Scrap Pieces", dead_scrap_count)

# Stock Pieces table
st.markdown("**Stock Pieces**")
st.dataframe(stock_pieces_df)

# Dead Scrap table (inside expander to reduce visual noise)
with st.expander(f"Dead Scrap ({dead_scrap_count} pieces)"):
    st.dataframe(dead_scrap_df)
```

**Stock Pieces Table Columns:**

| Column | Source |
|--------|-------|
| Piece ID | `piece_id` |
| Source Mark | `source_mark` |
| Product | `product_code` |
| MCK | `mck` (formatted as string) |
| Original Width (mm) | `original_width` |
| Remaining Width (mm) | `remaining_width` |
| Length (mm) | `length` |
| Qty | `qty` |
| Status | `status` |

**Dead Scrap Table Columns:**

| Column | Source |
|--------|-------|
| Scrap ID | `scrap_id` |
| Source Mark | `source_mark` |
| Width (mm) | `width` |
| Length (mm) | `length` |
| Area (m²) | `area_m2` |
| Qty | `qty` |
| Origin | `origin` |
| Reason | `reason` |

### Section 13: Recovery Matching

Two sub-sections: Matches and Unmatched.

```
st.subheader("13. Recovery Matching")

# Matches table
st.markdown("**Matched Demands**")
st.dataframe(matches_df)

# Unmatched table (if any)
if unmatched:
    st.markdown("**Unmatched Demands**")
    st.dataframe(unmatched_df)
else:
    st.success("All expansion demands matched.")
```

**Matches Table Columns:**

| Column | Source |
|--------|-------|
| Demand Mark | `demand_mark` |
| Product | `demand_product_code` |
| Expansion Width (mm) | `expansion_width` |
| Length (mm) | `demand_length` |
| Qty | `demand_qty` |
| Stock Piece | `stock_piece_id` |
| Source Mark | `source_mark` |
| Width Before (mm) | `stock_width_before` |
| Width After (mm) | `stock_width_after` |
| Trim Waste (mm) | `trim_waste` |
| Post Classification | `post_consumption_class` |
| Candidates | `candidate_count` |
| Decision | `decision_reason` |

**Unmatched Table Columns:**

| Column | Source |
|--------|-------|
| Mark | `mark` |
| Product | `product_code` |
| Expansion Width (mm) | `expansion_width` |
| Length (mm) | `fabricated_length` |
| Qty | `qty` |
| Reason | `reason` |

---

## 10. IMPLEMENTATION CHECKLIST

| # | Change | Lines of Code (est.) | Risk |
|---|--------|---------------------|------|
| 1 | Add `process_panels_with_recovery` import | 1 | NONE |
| 2 | Add Phase-3 button (3-column layout) | 5 | LOW |
| 3 | Add Phase-3 session state handling | 10 | LOW |
| 4 | Add session state cleanup on button click | 3 | LOW |
| 5 | Section 11: Recovery Status | ~25 | LOW |
| 6 | Section 12: Scrap Inventory | ~40 | LOW |
| 7 | Section 13: Recovery Matching | ~35 | LOW |
| 8 | Section 14: Recovery Validation | ~20 | LOW |
| 9 | Section 15: Recovery Explainability | ~25 | LOW |
| 10 | Version string update | 1 | NONE |
| 11 | depth_map constant | 3 | NONE |

**Estimated total: ~170 new lines. Zero frozen lines modified.**

---

## 11. WHAT IS NOT IN SCOPE

| Feature | Status | Notes |
|---------|--------|-------|
| Plotly charts | NOT IN SCOPE | No visualization library changes |
| Dashboard redesign | NOT IN SCOPE | Sections 1-10 unchanged |
| Phase-3.2 features (Cross-Project, Bin Packing) | NOT IN SCOPE | Deferred |
| depth_map UI input | NOT IN SCOPE | Hardcoded for Phase-3.1 |
| Recovery CSV export | NOT IN SCOPE | Existing CSV export unchanged |
| Custom styling / CSS | NOT IN SCOPE | Uses standard Streamlit components |
| Sidebar navigation changes | NOT IN SCOPE | Same two pages |

---

**END OF PLAN**
