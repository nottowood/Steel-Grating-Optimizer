# PHASE-3 REGRESSION TEST REPORT

**Date:** 2026-06-22  
**Branch:** v1.1.0-dev  
**Baseline:** v1.0.0-FROZEN (commit 5ece4d2)  
**Scope:** processor.py integration — `process_panels_with_recovery()` added  
**Result:** **ALL PASS**

---

## Changes Made

| File | Action | Lines Added | Lines Modified |
|------|--------|-------------|----------------|
| `processor.py` | Added 3 imports + 1 new function | 28 | 0 |
| `models.py` | — | 0 | 0 |
| `product_master.py` | — | 0 | 0 |
| `rule_engine.py` | — | 0 | 0 |
| `project_optimizer.py` | — | 0 | 0 |
| `app.py` | — | 0 | 0 |

**Zero frozen lines modified.**

---

## Test 1: Phase-1 Baseline (`process_panels`)

Verifies Phase-1 still works independently.

| KPI | Value |
|-----|-------|
| Yield | 92.89% |
| Scrap | 7.11% |
| Sold Area | 86.19 m² |
| Raw Material Area | 92.7825 m² |
| Expansion Count | 10 |
| Reduction Count | 35 |
| Warnings | [] |

**Result: PASS**

---

## Test 2: Phase-2 Baseline (`process_panels_optimized`)

Verifies Phase-2 still works independently.

| KPI | Value |
|-----|-------|
| Yield | 92.89% |
| Scrap | 7.11% |
| Overall Consistency | 100.0% |
| Yield Individual | 92.89% |
| Yield Optimized | 92.89% |
| Warnings | [] |

### Scenario Ranking (Floor Group: TA325/1)

| # | Start | Score | Selected | Rejection |
|---|-------|-------|----------|-----------|
| 1 | 20.0 | 1053.44 | **YES** | — |
| 2 | 70.0 | 1052.94 | no | Lower avg rod qty (13.0 vs 14.0) |
| 3 | 120.0 | 1052.44 | no | Lower avg rod qty (12.0 vs 14.0) |
| 4 | 170.0 | 1051.94 | no | Lower avg rod qty (11.0 vs 14.0) |
| 5 | 220.0 | 1051.44 | no | Lower avg rod qty (10.0 vs 14.0) |
| 6 | 270.0 | 1050.94 | no | Lower avg rod qty (9.0 vs 14.0) |
| 7 | 320.0 | 1050.44 | no | Lower avg rod qty (8.0 vs 14.0) |
| 8 | 370.0 | 1049.94 | no | Lower avg rod qty (7.0 vs 14.0) |
| 9 | 420.0 | 1049.44 | no | Lower avg rod qty (6.0 vs 14.0) |
| 10 | 470.0 | 1048.94 | no | Lower avg rod qty (5.0 vs 14.0) |
| 11 | 520.0 | 1048.44 | no | Lower avg rod qty (4.0 vs 14.0) |
| 12 | 570.0 | 1047.94 | no | Lower avg rod qty (3.0 vs 14.0) |
| 13 | 620.0 | 133.64 | no | Coverage 28.6% < selected 100.0% |
| 14 | 670.0 | 133.14 | no | Coverage 28.6% < selected 100.0% |

**Result: PASS**

---

## Test 3: Phase-3 with `depth_map=None` (R19 Fail-Closed)

Verifies graceful handling when no depth data is provided.

| KPI | Value |
|-----|-------|
| Frozen Yield | 92.89% |
| Recovery Rate | 0.0% |
| Matches | 0 |
| Unmatched | 1 (R19 fail-closed) |
| Validation Passed | True |
| Warnings | [] |

**Result: PASS** — No crash, no exceptions, R19 correctly rejects all matches.

---

## Test 4: Phase-3 with `depth_map` Provided

Verifies recovery engine works correctly with depth data.

| KPI | Value |
|-----|-------|
| Frozen Yield | 92.89% |
| Recovery Rate | 100.0% |
| Matches | 1 |
| Unmatched | 0 |
| Recovered Area | 1.74 m² |
| Dead Scrap Area | 0.9375 m² |
| Remaining Stock | 3.915 m² |

### Validation Results (R10-R21)

| Rule | Status | Detail |
|------|--------|--------|
| R10 | PASS | 2 reduction marks, all classified |
| R11 | PASS | 1 stock pieces checked |
| R12 | PASS | 1 matches verified |
| R13 | PASS | 1 stock pieces checked |
| R14 | PASS | Sum=1.74 == Total=1.74 |
| R15 | PASS | Recovery Rate = 100.0% |
| R16 | PASS | Total=1, Depleted=0, Available=1 |
| R17 | PASS | Total=1 (REDUCTION=1) |
| R18 | PASS | Frozen Yield = 92.89% |
| R19 | PASS | 1 matches have complete MCK |
| R20 | PASS | 1 consumption events validated |
| R21 | PASS | Recovered=1.74 <= Demand=1.74 |

**Result: PASS** — 12/12 validation rules pass.

---

## Test 5: Frozen KPI Bit-Exact Comparison

All frozen KPIs compared across Phase-1, Phase-2, Phase-3 (None), Phase-3 (depth).

| KPI | P1 | P2 | P3 (None) | P3 (depth) | Match |
|-----|----|----|-----------|------------|-------|
| yield_percent | 92.89 | 92.89 | 92.89 | 92.89 | **PASS** |
| scrap_percent | 7.11 | 7.11 | 7.11 | 7.11 | **PASS** |
| total_sold_area | 86.19 | 86.19 | 86.19 | 86.19 | **PASS** |
| total_production_area | 86.19 | 86.19 | 86.19 | 86.19 | **PASS** |
| total_raw_material_area | 92.7825 | 92.7825 | 92.7825 | 92.7825 | **PASS** |

**Result: PASS** — All 5 KPIs bit-exact across all 4 processing modes.

---

## Test 6: Scoring and Ranking Unchanged

Phase-2 optimization scores and selections compared between `process_panels_optimized()` and `process_panels_with_recovery()`.

| Check | P2 | P3 | Match |
|-------|----|----|-------|
| Common Start | 20.0 | 20.0 | **PASS** |
| Coverage | 100.0% | 100.0% | **PASS** |
| Scenario 1 (start=20.0) score | 1053.44 | 1053.44 | **PASS** |
| Scenario 1 selected | True | True | **PASS** |
| All 14 scenarios scores | identical | identical | **PASS** |
| All 14 scenarios selected | identical | identical | **PASS** |

**Result: PASS** — All 14 scenario scores and selections are bit-exact.

---

## Test 7: Warnings Unchanged

| Source | Warnings |
|--------|----------|
| Phase-1 | [] |
| Phase-2 | [] |
| Phase-3 (None) | [] |
| Phase-3 (depth) | [] |

**Result: PASS** — All identical.

---

## Test 8: Return Structure

| Key | Present |
|-----|---------|
| `processed` | YES |
| `summary` | YES |
| `opt_summary` | YES |
| `warnings` | YES |
| `recovery_summary` | YES |
| `validation_report` | YES |
| `recovery_report` | YES |

**Result: PASS** — Flat dict with 7 keys as specified.

---

## REGRESSION SUMMARY

| # | Test | Result |
|---|------|--------|
| 1 | Phase-1 Baseline | **PASS** |
| 2 | Phase-2 Baseline | **PASS** |
| 3 | Phase-3 depth_map=None | **PASS** |
| 4 | Phase-3 depth_map provided | **PASS** |
| 5 | Frozen KPI Bit-Exact | **PASS** |
| 6 | Scoring/Ranking Unchanged | **PASS** |
| 7 | Warnings Unchanged | **PASS** |
| 8 | Return Structure | **PASS** |

### Final Verdict

**ALL PASS — 8/8 tests passed. Zero regressions detected.**

Frozen yield (92.89%), frozen scoring (14 scenarios), frozen rankings (start=20.0 selected), and frozen warnings (none) are all unchanged across all processing modes.

---

**Test Script:** `test_regression.py`  
**END OF REPORT**
