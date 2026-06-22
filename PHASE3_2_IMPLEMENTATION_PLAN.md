# PHASE-3.2 IMPLEMENTATION PLAN

**Date:** 2026-06-22  
**Author:** Claude (AI)  
**Status:** APPROVED (with comments incorporated)  
**Reference:** DBD_PHASE3.2_REV0.4 (APPROVED)  
**Baseline:** v1.1.0-RC1 (commit ac1750a, branch v1.1.0-dev)

---

## 0. PHASE SEPARATION

Phase-3.2 is split into two independent sub-phases for traceability and reduced regression risk:

| Sub-Phase | Scope | Status |
|-----------|-------|--------|
| **Phase-3.2A** | Length Packing Engine (F1) | **IN PROGRESS** |
| **Phase-3.2B** | Match Improvement (F2) | PENDING (after 3.2A complete) |

Phase-3.2B will NOT be implemented until Phase-3.2A is complete, tested, and approved.

### Phase-3.2A Scope

| Step | Module | Type |
|------|--------|------|
| 1 | `packing_models.py` | NEW |
| 2 | `packing_engine.py` | NEW |
| 3 | `packing_validation.py` | NEW |
| 4 | `packing_report.py` | NEW |
| 5 | `recovery_models.py` | MODIFY (+5 lines) |
| 6 | `processor.py` | MODIFY (+10 lines) |
| 7 | `app.py` | MODIFY (+120 lines) |
| 8 | `test_regression_p32a.py` | NEW |

### Phase-3.2B Scope (DEFERRED)

| Step | Module | Type |
|------|--------|------|
| B1 | `recovery_engine.py` | MODIFY (multi-pass + partial qty) |
| B2 | `packing_validation.py` | MODIFY (add R30-R32) |
| B3 | `test_regression_p32b.py` | NEW |

### Validation Rule Assignment

| Sub-Phase | Rules |
|-----------|-------|
| Phase-3.2A | R22-R29 (8 packing rules including R29 Packing Conservation) |
| Phase-3.2B | R30-R32 (3 match improvement rules) |

---

## 1. MODULE ORDER

Nine implementation steps, each with a review gate before proceeding to the next.

| Step | Module | Type | Est. Lines | Dependencies |
|------|--------|------|-----------|-------------|
| 1 | `packing_models.py` | NEW | ~80 | dataclasses only |
| 2 | `packing_engine.py` | NEW | ~150 | models, packing_models, product_master (RO) |
| 3 | `packing_validation.py` | NEW | ~200 | models, packing_models, recovery_models |
| 4 | `packing_report.py` | NEW | ~120 | models, packing_models |
| 5 | `recovery_engine.py` | MODIFY | ~+40 | recovery_models, scrap_inventory |
| 6 | `recovery_models.py` | MODIFY | ~+5 | packing_models |
| 7 | `processor.py` | MODIFY | ~+15 | packing_engine, packing_validation, packing_report |
| 8 | `app.py` | MODIFY | ~+120 | processor |
| 9 | `test_regression_p32.py` | NEW | ~200 | all above |

**Total new code:** ~550 lines (4 new modules)  
**Total modified code:** ~+180 lines across 4 existing modules (0 frozen lines changed)

---

## 2. MODULE DETAILS

### Step 1: packing_models.py (NEW)

**Purpose:** Data classes and constants for length packing.

**Contents:**

```
Constants:
  PACKING_REUSABLE_MIN_LENGTH = 200.0     # mm (configurable, independent)
  PACKING_REUSABLE_MIN_AREA   = 0.20      # m² (configurable, independent)
  ALGORITHM_ID                = "FFD"     # baseline reference

Data classes:
  CutPlanEntry(mark, product_code, fabricated_length, position_start, kerf_after)
  CutPlan(bin_id, stock_width, stock_length, mck, panels, total_used, remnant_length, remnant_classification, remnant_area_m2)
  LengthRemnant(remnant_id, bin_id, stock_width, remnant_length, remnant_area_m2, classification, mck)
  PackingSummary(total_bins, total_items_packed, total_marks_packed, stock_lengths_before, stock_lengths_after, stock_savings, stock_savings_percent, stock_utilization_rate, total_length_waste_m2, total_reusable_remnant_m2, total_exact_fit_bins, algorithm, cut_plans, length_remnants)

Functions:
  classify_length_remnant(remnant_length, stock_width) → str
```

**Dependencies:** `dataclasses` only. No imports from frozen modules.

**Validation after step:** Import module, instantiate all classes, verify classify_length_remnant against threshold boundary cases.

---

### Step 2: packing_engine.py (NEW)

**Purpose:** Grouping rules (G1-G3) and FFD packing algorithm.

**Contents:**

```
Functions:
  group_panels_for_packing(panels, catalog) → dict[tuple, list[dict]]
    - Groups by (standard_width, MCK)
    - Applies G1-G3 filters
    - Returns groups keyed by (std_width, mck)

  expand_to_units(group) → list[dict]
    - Expands qty into individual items
    - Each item: {mark, product_code, fabricated_length}

  run_length_packing(panels, catalog, depth_map) → PackingSummary
    - Groups → expand → sort descending → FFD
    - Kerf model: N cuts for N panels
    - Builds CutPlan per bin
    - Classifies remnants
    - Calculates KPIs
```

**Key logic — FFD inner loop:**

```python
for item in sorted_items:
    placed = False
    for bin in open_bins:
        needed = item.length + SAW_KERF
        if bin.remaining >= needed:
            assign(item, bin)
            placed = True
            break
    if not placed:
        new_bin = open_new_bin(STOCK_LENGTH)
        # First panel: consumes length + kerf
        new_bin.remaining = STOCK_LENGTH - item.length - SAW_KERF
        assign(item, new_bin)
```

**Dependencies:** `models.FabricatedPanel`, `product_master.build_product_catalog`, `packing_models.*`, `rule_engine.STOCK_LENGTH`, `rule_engine.SAW_KERF`. All read-only.

**Validation after step:** Run FFD on sample data (G01-G04). Verify:
- G01 excluded (expansion, G3)
- 60 items packed into 15 bins
- Each bin: total_used <= 6000mm
- Remnant classification correct

---

### Step 3: packing_validation.py (NEW)

**Purpose:** Validation rules R22-R28 for packing, R29-R31 for match improvement.

**Contents:**

```
Functions:
  validate_packing(packing_summary, panels, summary) → dict
    - R22: No Bin Overflow
    - R23: Kerf Accounted (N cuts = N panels)
    - R24: Panel Coverage
    - R25: Remnant Classification Consistent
    - R26: Stock Savings Non-Negative
    - R27: Packing Utilization Bounded
    - R28: Frozen KPI Unchanged

  validate_matching_improvement(recovery, panels, summary) → dict
    - R29: Multi-Pass Convergence
    - R30: No Duplicate Match
    - R31: Partial Qty Balanced
```

**Output format:** Same structure as `recovery_validation.py` — list of rule results with rule_id, description, status, detail. `all_passed` property.

**Dependencies:** `models`, `packing_models`, `recovery_models`.

**Validation after step:** Run all R22-R31 against Step 2 output. All PASS on sample data.

---

### Step 4: packing_report.py (NEW)

**Purpose:** Structured report dict for packing results + explainability.

**Contents:**

```
Functions:
  generate_packing_report(packing_summary, validation, panels) → dict
    - Section: Executive Summary (bins, savings, utilization)
    - Section: Cut Plans (per-bin panel positions)
    - Section: Remnant Summary (classification breakdown)
    - Section: Validation Results (R22-R31)
    - Section: Explainability (per-bin allocation trace)
```

**Dependencies:** `models`, `packing_models`.

**Validation after step:** Verify report has all sections, all fields populated, no None values in required fields.

---

### Step 5: recovery_engine.py (MODIFY)

**Purpose:** Multi-pass matching + partial qty continuation (F2).

**Changes:**

| Location | Before | After |
|----------|--------|-------|
| `_match_demands()` | Single pass, single candidate per demand | Multi-pass loop until no new matches |
| Match loop inner | `pieces_to_use = min(best.qty, demand_qty)` then move to next demand | Inner while loop: continue searching if remaining_demand_qty > 0 |
| New function | — | `_match_demands_multipass()` wrapping existing logic |

**Strategy: Wrap, don't replace.**

The existing `_match_demands()` function becomes the inner pass. A new `_match_demands_multipass()` calls it in a loop:

```python
def _match_demands_multipass(demands, inventory, depth_map, catalog):
    all_matches = []
    all_unmatched = list(demands)
    pass_number = 0

    while True:
        pass_number += 1
        new_matches, still_unmatched = _match_demands_single_pass(
            all_unmatched, inventory, depth_map, catalog, pass_number
        )
        if not new_matches:
            break
        all_matches.extend(new_matches)
        all_unmatched = still_unmatched

    return all_matches, all_unmatched, pass_number
```

**Critical constraint:** The existing `_match_demands()` is renamed to `_match_demands_single_pass()` — its internal logic (C1-C5, R1-R4, R19) is NOT modified. Multi-pass is purely an outer loop.

**Partial qty change:** Inside `_match_demands_single_pass()`, the demand loop continues searching for more candidates after a partial match:

```python
# Before:
pieces_to_use = min(best.qty, demand_qty)
# ... record match, move to next demand

# After:
remaining_qty = demand_qty
while remaining_qty > 0:
    candidates = _find_candidates(...)
    if not candidates:
        break
    best = candidates[0]
    pieces_to_use = min(best.qty, remaining_qty)
    # ... record match
    remaining_qty -= pieces_to_use
# Only remaining_qty > 0 goes to unmatched
```

**Lines changed:** ~40 lines added/modified. 0 frozen lines. Matching rules C1-C5, R1-R4, R19 untouched.

**Validation after step:**
- Run with sample data → same result as Phase-3.1 (single pass sufficient)
- Run with synthetic multi-demand data → verify multi-pass activates
- R10-R21 all PASS (existing validation unchanged)
- Frozen KPIs unchanged

---

### Step 6: recovery_models.py (MODIFY)

**Purpose:** Add `packing_summary` field to `RecoverySummary`.

**Changes:**

```python
# Add to RecoverySummary:
packing_summary: object = None   # PackingSummary | None
```

**Why `object` not `PackingSummary`:** Avoids circular import between recovery_models and packing_models. Type is checked at runtime via duck typing. Alternative: use `TYPE_CHECKING` guard if preferred.

**Lines changed:** ~5 lines.

**Validation after step:** Existing R10-R21 still PASS. RecoverySummary instantiation with and without packing_summary works.

---

### Step 7: processor.py (MODIFY)

**Purpose:** Integrate packing engine into `process_panels_with_recovery()`.

**Changes:**

```python
# New imports:
from packing_engine import run_length_packing
from packing_validation import validate_packing, validate_matching_improvement
from packing_report import generate_packing_report

# Inside process_panels_with_recovery(), after recovery:
packing = run_length_packing(processed, catalog, depth_map)
packing_validation = validate_packing(packing, processed, summary)
matching_validation = validate_matching_improvement(recovery, processed, summary)
packing_report = generate_packing_report(packing, packing_validation, processed)

# Extended return dict:
return {
    # ... existing 7 keys unchanged ...
    "packing_summary": packing,
    "packing_validation": packing_validation,
    "matching_validation": matching_validation,
    "packing_report": packing_report,
}
```

**Lines changed:** ~15 lines added. 0 existing lines modified.

**Validation after step:**
- Regression test: all 8 existing tests PASS
- New: return dict has 11 keys (7 existing + 4 new)
- Frozen KPIs bit-exact

---

### Step 8: app.py (MODIFY)

**Purpose:** Add Sections 16-18 for packing display.

**Changes:**

| Section | Title | Visibility | Content |
|---------|-------|-----------|---------|
| 16 | Length Packing Summary | **Visible** | Stock savings banner, metrics: bins used, savings %, utilization rate |
| 17 | Cut Plans | **Expander** | Per-bin table with panel positions, remnant classification |
| 18 | Packing Validation | **Visible** | R22-R31 results table, VALID/INVALID banner |

**Session state additions:** 4 new keys (`packing_summary`, `packing_validation`, `matching_validation`, `packing_report`) cleared on button click.

**Lines changed:** ~120 lines added after Section 15. 0 existing lines modified except session state clear list.

**Validation after step:**
- Syntax check: `python -c "import ast; ast.parse(open('app.py').read())"`
- Streamlit server responds HTTP 200
- Programmatic: all report data structures present and populated
- All frozen KPIs unchanged

---

### Step 9: test_regression_p32.py (NEW)

**Purpose:** Comprehensive regression test covering Phase-3.2 + backward compatibility.

**Test matrix:**

| # | Test | Verifies |
|---|------|----------|
| T1 | Frozen KPI bit-exact | yield=92.89%, scrap=7.11%, all areas match |
| T2 | Frozen scoring/ranking | 14 scenarios, same scores and selection |
| T3 | Phase-3.1 recovery unchanged | Recovery rate, matches, validation R10-R21 |
| T4 | Packing grouping | G01 excluded, G02+G03+G04 grouped |
| T5 | FFD bin count | 15 bins for 60 packable items |
| T6 | Kerf model | total_used = Σ panels + N × 6mm per bin |
| T7 | Remnant classification | All 25 bins → REUSABLE_REMNANT (length >= 200mm) |
| T8 | Packing validation R22-R28 | All 7 rules PASS |
| T9 | Match improvement R29-R31 | All 3 rules PASS |
| T10 | Stock savings KPI | 70 → 25 stock lengths, 64.3% savings |
| T11 | Return structure | 11 keys in result dict |
| T12 | FFD algorithm ID | PackingSummary.algorithm == "FFD" |

---

## 3. INTEGRATION ORDER

```
              packing_models.py (Step 1)
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
  packing_engine  packing_   packing_
    (Step 2)      validation  report
                  (Step 3)    (Step 4)
          │         │         │
          ▼         ▼         ▼
     recovery_engine.py (Step 5) ← multi-pass improvement
          │
          ▼
     recovery_models.py (Step 6) ← add packing_summary field
          │
          ▼
     processor.py (Step 7) ← integrate all packing calls
          │
          ▼
     app.py (Step 8) ← Sections 16-18
          │
          ▼
     test_regression_p32.py (Step 9)
```

**Steps 2, 3, 4 are independent** — they all depend only on Step 1 (packing_models). They could be implemented in any order. However, implementing in order (engine → validation → report) allows validation to be tested against engine output immediately.

**Step 5 is independent** from Steps 2-4 — match improvement modifies recovery_engine, not packing. But it is placed after Step 4 so that all new modules are in place before modifying existing code.

---

## 4. VALIDATION STRATEGY

### 4.1 Per-Step Validation

Each step includes an inline validation before proceeding:

| Step | Validation | Method |
|------|-----------|--------|
| 1 | Import, instantiate, classify_length_remnant boundary cases | Python script |
| 2 | FFD on sample data: 15 bins, all bins ≤ 6000mm | Python script |
| 3 | R22-R28 all PASS on Step 2 output | Python script |
| 4 | Report structure: all sections present | Python script |
| 5 | R10-R21 PASS + sample data result unchanged | Python script |
| 6 | RecoverySummary with/without packing_summary | Python script |
| 7 | Return dict 11 keys + frozen KPIs bit-exact | Python script |
| 8 | Syntax + HTTP 200 + data pipeline | Python script |
| 9 | 12/12 regression tests PASS | test_regression_p32.py |

### 4.2 Cross-Phase Validation

After all steps complete:

| Check | Expected | Method |
|-------|----------|--------|
| Frozen Yield | 92.89% | Bit-exact comparison |
| Frozen Scrap | 7.11% | Bit-exact comparison |
| Frozen Scenario Scores | 14 values bit-exact | Compare all 14 |
| Recovery Rate | 100% | Same as Phase-3.1 |
| R10-R21 | 12/12 PASS | recovery_validation |
| R22-R28 | 7/7 PASS | packing_validation |
| R29-R31 | 3/3 PASS | packing_validation |
| Total validation rules | 22/22 PASS | Combined |

### 4.3 FFD Baseline Verification

Per DBD Section 5.4, FFD is the baseline reference. Specific checks:

| Check | Expected |
|-------|----------|
| PackingSummary.algorithm | "FFD" |
| Bins for sample data | 15 (packable) + 10 (G01 solo) = 25 total |
| Stock savings | 70 → 25 = 45 saved (64.3%) |
| Per-bin total_used | ≤ 6000mm (R22) |
| Per-bin kerf | N × 6mm where N = panels in bin (R23) |

---

## 5. REGRESSION STRATEGY

### 5.1 Backward Compatibility

| Guarantee | Verification |
|-----------|-------------|
| Phase-1 `process_panels()` unchanged | T1: frozen KPIs bit-exact |
| Phase-2 `process_panels_optimized()` unchanged | T2: 14 scenario scores bit-exact |
| Phase-3.1 recovery results compatible | T3: recovery rate, match count, R10-R21 |
| Return structure backward compatible | T11: existing 7 keys still present |

### 5.2 Existing Test Continuity

`test_regression.py` (Phase-3.1, 8 tests) must still pass after all changes. This is verified in Step 9 before running new tests.

### 5.3 Regression Test Execution

```bash
# Phase-3.1 regression (existing)
python -X utf8 test_regression.py

# Phase-3.2 regression (new)
python -X utf8 test_regression_p32.py
```

Both must produce ALL PASS.

---

## 6. ROLLBACK STRATEGY

### 6.1 Per-Step Rollback

Each step is a separate commit. If a step fails validation:

1. **Revert the commit** for that step.
2. **All prior steps remain valid** — no cross-step dependencies within a step.
3. **Re-attempt** after diagnosis.

### 6.2 Full Phase-3.2 Rollback

If Phase-3.2 must be completely reverted:

| Action | Effect |
|--------|--------|
| Delete `packing_models.py` | Remove new data classes |
| Delete `packing_engine.py` | Remove FFD algorithm |
| Delete `packing_validation.py` | Remove R22-R31 |
| Delete `packing_report.py` | Remove packing report |
| Revert `recovery_engine.py` | Restore single-pass matching |
| Revert `recovery_models.py` | Remove packing_summary field |
| Revert `processor.py` | Remove packing integration (4 imports, ~10 lines) |
| Revert `app.py` | Remove Sections 16-18 (~120 lines) |
| Delete `test_regression_p32.py` | Remove new tests |

**Result:** Exact v1.1.0-RC1 behavior restored. Phase-3.1 (width recovery) continues to work. No frozen code was ever touched.

### 6.3 Partial Rollback — Packing Only

If only length packing (F1) must be reverted but match improvement (F2) should stay:

| Action | Effect |
|--------|--------|
| Delete `packing_*.py` (3 files) | Remove packing engine |
| Revert `processor.py` | Remove packing calls only |
| Revert `app.py` | Remove Sections 16-18 only |
| Keep `recovery_engine.py` changes | Multi-pass matching retained |

### 6.4 Partial Rollback — Match Improvement Only

If only match improvement (F2) must be reverted but packing (F1) should stay:

| Action | Effect |
|--------|--------|
| Revert `recovery_engine.py` | Restore single-pass matching |
| Keep all `packing_*.py` | Packing engine retained |

---

## 7. ESTIMATED EFFORT

| Step | Module | Effort | Cumulative |
|------|--------|--------|-----------|
| 1 | packing_models.py | Small (data classes only) | Step 1 |
| 2 | packing_engine.py | Medium (FFD algorithm + grouping) | Steps 1-2 |
| 3 | packing_validation.py | Medium (10 validation rules) | Steps 1-3 |
| 4 | packing_report.py | Small (report structure) | Steps 1-4 |
| 5 | recovery_engine.py | Medium (multi-pass refactor, highest risk) | Steps 1-5 |
| 6 | recovery_models.py | Trivial (1 field) | Steps 1-6 |
| 7 | processor.py | Small (wire-up) | Steps 1-7 |
| 8 | app.py | Medium (3 new UI sections) | Steps 1-8 |
| 9 | test_regression_p32.py | Medium (12 test cases) | Steps 1-9 |

**Risk concentration:** Step 5 (recovery_engine.py modification) is the highest risk step — it modifies existing Phase-3.1 code. All other steps are additive (new files) or trivial (small additions to existing files).

**Mitigation for Step 5:** The `_match_demands()` function is renamed, not rewritten. Multi-pass is an outer loop wrapping the existing single-pass. The inner matching logic (C1-C5, R1-R4, R19) is not touched.

---

## 8. REVIEW GATES

| Gate | After Step | Approval Required For |
|------|-----------|----------------------|
| G1 | Step 1 | Data classes and constants correct |
| G2 | Step 2 | FFD produces correct bin allocation |
| G3 | Steps 3-4 | Validation + report correct |
| G4 | Step 5 | Multi-pass matching is safe (existing tests still pass) |
| G5 | Steps 6-7 | Integration wiring correct |
| G6 | Step 8 | UI sections render correctly |
| G7 | Step 9 | All 12 regression tests + 8 existing tests PASS |

**Proposed gate grouping:** Steps 1-2 can share a gate (engine depends on models). Steps 3-4 can share a gate (both read-only consumers). Steps 6-7 can share a gate (trivial changes). This reduces to 5 review cycles instead of 9.

| Cycle | Steps | Deliverable |
|-------|-------|-------------|
| 1 | 1 + 2 | packing_models.py + packing_engine.py |
| 2 | 3 + 4 | packing_validation.py + packing_report.py |
| 3 | 5 | recovery_engine.py (multi-pass) |
| 4 | 6 + 7 | recovery_models.py + processor.py |
| 5 | 8 + 9 | app.py + regression tests |

---

## 9. FILES SUMMARY

### New Files (4 modules + 1 test)

| File | Purpose |
|------|---------|
| `packing_models.py` | Data classes, constants, remnant classification |
| `packing_engine.py` | Grouping (G1-G3) + FFD packing |
| `packing_validation.py` | R22-R31 validation |
| `packing_report.py` | Structured report + explainability |
| `test_regression_p32.py` | 12-test regression suite |

### Modified Files (4 modules)

| File | Current Lines | Lines Added | Lines Changed | Risk |
|------|--------------|-------------|---------------|------|
| `recovery_engine.py` | 343 | ~40 | ~10 (rename) | MEDIUM |
| `recovery_models.py` | 158 | ~5 | 0 | LOW |
| `processor.py` | 90 | ~15 | 0 | LOW |
| `app.py` | 908 | ~120 | ~3 (session state) | LOW |

### Frozen Files (0 modifications)

| File | Lines | Status |
|------|-------|--------|
| `models.py` | 105 | FROZEN — NOT TOUCHED |
| `product_master.py` | 105 | FROZEN — NOT TOUCHED |
| `rule_engine.py` | 115 | FROZEN — NOT TOUCHED (constants read-only) |
| `pattern_engine.py` | — | FROZEN — NOT TOUCHED |
| `project_optimizer.py` | — | FROZEN — NOT TOUCHED |
| `optimizer_models.py` | — | FROZEN — NOT TOUCHED |

---

**END OF PLAN**
