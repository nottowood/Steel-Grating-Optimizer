# DESIGN BASIS DOCUMENT — PHASE 3: MATERIAL RECOVERY ENGINE

**Document:** DBD_PHASE3_REV0.1  
**Project:** Steel Grating Optimizer (SGO)  
**Baseline:** v1.0.0-FROZEN (commit 5ece4d2)  
**Branch:** v1.1.0-dev  
**Date:** 2026-06-21  
**Status:** DRAFT — Awaiting Design Approval

---

## 1. OBJECTIVES

Phase-3 adds a Material Recovery Engine on top of the frozen Phase-1 (Rule Engine) and Phase-2 (Project Optimizer) layers.

**Primary Goal:**  
Recover usable material from reduction waste and match it to expansion demand within the same project, reducing raw material consumption.

**Secondary Goals:**
- Track all scrap pieces with full traceability (source mark, dimensions, classification)
- Provide auditable recovery decisions with explainable matching logic
- Measure yield improvement attributable to material recovery
- Establish the commercial IP layer for future SaaS monetization

**Non-Goals (Phase-3 does NOT include):**
- Cross-project material pooling
- Cutting stock optimization (nesting multiple panels from one stock sheet)
- Saw scheduling or production sequencing
- Inventory persistence across sessions (future phase)

---

## 2. SCOPE

### In Scope

| # | Feature | Description |
|---|---------|-------------|
| 1 | Reusable Strip Engine | Classify reduction strips as REUSABLE or SCRAP |
| 2 | Scrap Inventory | Collect, track, and report all waste pieces per project |
| 3 | Expansion Matching Engine | Match reusable strips to expansion-requiring panels |
| 4 | Recovery Optimization | Select best match when multiple candidates exist |
| 5 | Yield Impact Calculation | Measure yield improvement from recovery |
| 6 | UI Reporting | Streamlit sections for recovery results |

### Out of Scope

- Modifications to Phase-1 Rule Engine
- Modifications to Phase-2 Scoring Engine
- Modifications to frozen KPI formulas
- Multi-project inventory management
- Stock sheet nesting / cutting stock algorithms

### Frozen Interfaces (Read-Only Access)

Phase-3 will READ the following from Phase-1/Phase-2 but will NOT modify them:

| Source | Data Used |
|--------|-----------|
| `FabricatedPanel` | `mark`, `product_code`, `fabricated_width`, `fabricated_length`, `qty`, `standard_width`, `expansion_width`, `reduction_width`, `needs_expansion`, `needs_reduction` |
| `ProjectSummary` | `yield_percent`, `scrap_percent`, all area totals |
| `Pattern` | `rod_qty`, `start_length` (for traceability only) |

---

## 3. DEFINITIONS

| Term | Definition |
|------|------------|
| **Reduction Strip** | The material removed when Fab Width < Standard Width. Width = Standard Width − Fab Width. Length = Fab Length. |
| **Reusable Strip** | A Reduction Strip that passes reusability criteria (width > 200mm AND length > 200mm AND area >= 0.20 m²) |
| **Dead Scrap** | A Reduction Strip that fails reusability criteria |
| **Expansion Demand** | The additional width required when Fab Width > Standard Width. Width = Fab Width − Standard Width. |
| **Recovery Match** | A pairing of one Reusable Strip to one Expansion Demand where the strip can physically satisfy the demand |
| **Recovered Area** | The area of expansion demand satisfied by a reusable strip instead of new raw material |
| **Trim Waste** | The leftover strip width after a recovery match (Strip Width − Expansion Width needed) |
| **Yield Before Recovery** | Phase-1/Phase-2 yield (frozen calculation) |
| **Yield After Recovery** | Adjusted yield accounting for recovered material |

---

## 4. REUSABLE STRIP CLASSIFICATION

### Existing Rule (from `rule_engine.py`)

The `classify_scrap()` function already implements:

```
Reusable IF:
  width > 200 mm
  AND area >= 0.20 m²
```

### Phase-3 Extension

Phase-3 will use this existing classification but add structured tracking:

```
ReusableStrip:
    strip_id            — unique identifier (auto-generated)
    source_mark         — which panel produced this strip
    source_product_code — product code of source panel
    width               — strip width (mm) = reduction_width
    length              — strip length (mm) = fabricated_length
    area_m2             — width × length (m²)
    qty                 — same qty as source panel
    classification      — REUSABLE | DEAD_SCRAP
    status              — AVAILABLE | MATCHED | PARTIALLY_USED
    matched_to          — target mark (if matched)
    trim_waste_width    — remaining width after match (mm)
```

### Classification Rules

| Condition | Classification |
|-----------|---------------|
| width > 200 AND length > 200 AND area >= 0.20 m² | REUSABLE |
| Otherwise | DEAD_SCRAP |

**Note:** The length condition (> 200mm) is added in Phase-3. The existing `classify_scrap()` checks width > 200 AND area >= 0.20 but does not explicitly check length. Since area = width × length, a 200mm width requires length >= 1000mm to reach 0.20 m², so in practice all current panels pass the length check. However, for correctness and future-proofing, Phase-3 will enforce all three conditions explicitly.

---

## 5. SCRAP INVENTORY MODEL

### Data Model

```
ScrapInventory:
    project_id          — project identifier
    total_strips        — total reduction strips generated
    reusable_strips     — count classified as REUSABLE
    dead_scrap_strips   — count classified as DEAD_SCRAP
    total_reusable_area — sum of reusable strip areas (m²)
    total_dead_area     — sum of dead scrap areas (m²)
    strips              — list[ReusableStrip]
```

### Generation Logic

For every panel where `needs_reduction = True`:

```
strip_width  = panel.reduction_width
strip_length = panel.fabricated_length
strip_area   = (strip_width / 1000) × (strip_length / 1000)
strip_qty    = panel.qty

classification = REUSABLE if (width > 200 AND length > 200 AND area >= 0.20)
                 else DEAD_SCRAP
```

### Sample Data Expectation

Using `sample_data.csv`:

| Mark | Std Width | Fab Width | Reduction | Fab Length | Area (m²) | Qty | Classification |
|------|-----------|-----------|-----------|------------|-----------|-----|----------------|
| G03 | 995 | 965 | 30 mm | 1250 | 0.0375 | 25 | DEAD_SCRAP (width 30 < 200) |
| G04 | 995 | 605 | 390 mm | 1450 | 0.5655 | 10 | REUSABLE |

---

## 6. EXPANSION MATCHING LOGIC

### Problem Statement

When a panel requires expansion (Fab Width > Standard Width), an expansion strip must be welded to the standard panel. Currently, this strip is always assumed to come from new raw material.

Phase-3 introduces the possibility of sourcing expansion strips from reduction waste of other panels in the same project.

### Matching Constraints

A Reusable Strip can match an Expansion Demand when:

| Constraint | Rule | Rationale |
|------------|------|-----------|
| **C1: Same Product Code** | strip.source_product_code == demand.product_code | Load bar pitch and thickness must match for welding compatibility |
| **C2: Width Sufficient** | strip.width >= demand.expansion_width | Strip must cover the required expansion |
| **C3: Length Compatible** | strip.length >= demand.fabricated_length | Strip must be at least as long as the panel it will expand |
| **C4: Strip Available** | strip.status == AVAILABLE | Strip has not already been matched |

### Matching Process

```
FOR each expansion panel (sorted by expansion_width descending — largest demand first):
    Find all AVAILABLE reusable strips matching C1, C2, C3, C4
    IF candidates exist:
        Select best match (see Section 7)
        Mark strip as MATCHED
        Record trim waste = strip.width - expansion_width
        Record recovery
    ELSE:
        Mark as UNMATCHED — requires new raw material
```

### Why Largest-First?

Larger expansion demands are harder to satisfy. Processing them first maximizes the chance of finding a suitable match before strips are consumed by smaller demands.

### Sample Data Expectation

| Demand | Expansion Width | Source Strip | Strip Width | Match? | Trim Waste |
|--------|----------------|-------------|-------------|--------|------------|
| G01 (1115mm, needs 120mm expansion) | 120 mm | G04 (390mm strip) | 390 mm | YES (C1: both TA325/1, C2: 390>=120, C3: 1450>=1450) | 270 mm |

**Important:** G01 has qty=10 and G04 has qty=10. Each G04 panel produces one 390mm strip, and each G01 panel needs one 120mm expansion strip. So 10 strips can satisfy 10 demands exactly.

---

## 7. RECOVERY OPTIMIZATION ALGORITHM

### Objective

When multiple reusable strips can satisfy a single expansion demand, select the one that minimizes waste.

### Selection Criteria (Priority Order)

| Priority | Criterion | Rationale |
|----------|-----------|-----------|
| **R1** | Minimum Trim Waste | Smallest (strip.width − expansion_width) wastes least material |
| **R2** | Same Length Preferred | strip.length == demand.fabricated_length avoids cutting |
| **R3** | Smallest Strip First | When trim waste is equal, use the smallest available strip to preserve larger strips for bigger demands |

### Decision Formula

```
Best Match = MIN(strip.width - expansion_width)
             THEN PREFER(strip.length == demand.fabricated_length)
             THEN MIN(strip.width)
```

### Explainability

Every match decision must record:

```
RecoveryDecision:
    demand_mark         — panel needing expansion
    expansion_width     — width needed (mm)
    matched_strip_id    — which strip was selected
    source_mark         — which panel produced the strip
    strip_width         — original strip width (mm)
    trim_waste          — strip_width - expansion_width (mm)
    candidate_count     — how many strips were considered
    rejection_reasons   — why other candidates were not selected
    decision_reason     — why this candidate was selected
```

---

## 8. YIELD IMPACT CALCULATION

### Concept

When a recovery match is made, the expansion panel no longer needs new raw material for the expansion strip. This reduces the effective Raw Material Area.

### Formula

**Without Recovery (current frozen formula):**
```
Raw Material Area = Standard Width Used × Fab Length × Qty
                  where Standard Width Used = Standard Width + Expansion Width (if expanded)
```

**With Recovery:**
```
For matched panels:
    Recovered Raw Material Area = Standard Width × Fab Length × Qty
    (Expansion strip comes from existing reduction waste, not new material)

For unmatched panels:
    Raw Material Area unchanged (frozen formula applies)
```

### KPI Extension

| KPI | Formula |
|-----|---------|
| Yield Before Recovery | Frozen Phase-1/Phase-2 yield (DO NOT MODIFY) |
| Recovered Area (m²) | Sum of (expansion_width / 1000 × fab_length / 1000 × qty) for matched panels |
| Adjusted Raw Material Area | Original Raw Material Area − Recovered Area |
| Yield After Recovery | Production Area / Adjusted Raw Material Area × 100 |
| Yield Improvement | Yield After Recovery − Yield Before Recovery |
| Recovery Rate | Matched Expansion Panels / Total Expansion Panels × 100 |

### Critical Rule

**The frozen Yield (Phase-1/Phase-2) is NEVER modified.** Phase-3 calculates an *additional* "Yield After Recovery" metric that is displayed alongside the original yield. Both values are shown in the UI for comparison.

### Sample Data Expectation

```
Before Recovery:
  Raw Material Area = 92.7825 m²
  Yield = 92.89%

G01 matched to G04 strip (10 panels × 120mm expansion recovered):
  Recovered Area = (120 / 1000) × (1450 / 1000) × 10 = 1.74 m²
  Adjusted Raw Material = 92.7825 - 1.74 = 91.0425 m²
  Yield After Recovery = 86.19 / 91.0425 × 100 = 94.67%
  Yield Improvement = +1.78%
```

---

## 9. VALIDATION RULES

Phase-3 adds validation rules that run alongside the existing 9 rules (Rules 1-9 are frozen).

| Rule | Description | Check |
|------|-------------|-------|
| R10 | Strip Classification Consistent | Every reduction panel produces exactly one strip record |
| R11 | No Duplicate Matches | Each strip is matched to at most one expansion demand |
| R12 | Match Constraints Verified | Every match satisfies C1 (product), C2 (width), C3 (length) |
| R13 | Recovered Area Calculated | Recovered Area > 0 when matches exist |
| R14 | Yield After Recovery >= Yield Before | Recovery can only improve or maintain yield |
| R15 | Trim Waste Non-Negative | strip.width − expansion_width >= 0 for all matches |
| R16 | Total Scrap Accounted | Dead Scrap + Reusable = Total Reduction Strips |

---

## 10. EXPLAINABILITY REQUIREMENTS

Phase-3 must maintain the same explainability standard as Phase-2.

### Required Reports

| Report | Content |
|--------|---------|
| **Scrap Inventory** | All reduction strips with classification, dimensions, source mark |
| **Expansion Demand** | All expansion panels with required width, matched status |
| **Recovery Matching** | Each match with source strip, target panel, trim waste, decision reason |
| **Unmatched Report** | Expansion demands that could not be matched, with reasons |
| **Recovery KPI Summary** | Yield Before/After, Recovered Area, Recovery Rate, Improvement |
| **Trim Waste Report** | All trim waste from matched strips, with reusability classification |

### Audit Trail

Every recovery decision must be traceable:
```
Panel G01 (expansion 120mm)
  ← Matched to Strip from G04 (390mm, REUSABLE)
  → Trim Waste: 270mm (REUSABLE: 270 > 200, area = 0.3915 m²)
  → Candidates considered: 1
  → Decision: Only available match
```

---

## 11. DATA MODEL

### New Files

| File | Purpose |
|------|---------|
| `recovery_models.py` | Data models for strips, matches, inventory, recovery summary |
| `recovery_engine.py` | Strip classification, expansion matching, recovery optimization |

### New Data Classes

```python
@dataclass
class ReusableStrip:
    strip_id: str
    source_mark: str
    source_product_code: str
    width: float               # mm
    length: float              # mm
    area_m2: float
    qty: int
    classification: str        # REUSABLE | DEAD_SCRAP
    status: str                # AVAILABLE | MATCHED | PARTIALLY_USED
    matched_to: str            # target mark or ""
    trim_waste_width: float    # mm

@dataclass
class RecoveryMatch:
    demand_mark: str
    demand_product_code: str
    expansion_width: float     # mm needed
    demand_length: float       # mm
    demand_qty: int
    strip_id: str
    source_mark: str
    strip_width: float         # mm available
    strip_length: float        # mm
    trim_waste: float          # mm
    trim_classification: str   # REUSABLE | DEAD_SCRAP
    candidate_count: int
    decision_reason: str

@dataclass
class RecoverySummary:
    total_reduction_strips: int
    reusable_strips: int
    dead_scrap_strips: int
    total_reusable_area_m2: float
    total_dead_scrap_area_m2: float
    total_expansion_demands: int
    matched_demands: int
    unmatched_demands: int
    recovery_rate: float              # %
    recovered_area_m2: float
    yield_before_recovery: float      # % (frozen)
    yield_after_recovery: float       # %
    yield_improvement: float          # %
    adjusted_raw_material_area: float # m²
    matches: list[RecoveryMatch]
    strips: list[ReusableStrip]
    trim_waste_total_m2: float
    trim_reusable_count: int
    trim_dead_count: int
```

### Integration Point

```python
# In processor.py — new function (Phase-1 and Phase-2 functions unchanged)
def process_panels_with_recovery(panels):
    processed, summary, opt_summary, warnings = process_panels_optimized(panels)
    recovery_summary = run_recovery_engine(processed, summary)
    return processed, summary, opt_summary, recovery_summary, warnings
```

---

## 12. FUTURE COMMERCIAL EXTENSIONS

The following are NOT in Phase-3 scope but the data model is designed to support them:

| Extension | Description | Phase-3 Foundation |
|-----------|-------------|-------------------|
| **Cross-Project Recovery** | Match strips across multiple projects | `strip_id` enables global strip tracking |
| **Persistent Inventory** | Save unused strips to database for future projects | `status` field tracks availability |
| **Multi-Strip Expansion** | Weld multiple narrow strips to satisfy one wide expansion | `PARTIALLY_USED` status |
| **Trim Cascade** | Reusable trim waste feeds back into strip inventory | `trim_classification` enables recursive matching |
| **Cost Engine** | Assign monetary value to recovered material | `recovered_area_m2` enables cost calculation |
| **SaaS Dashboard** | Customer-facing yield improvement analytics | `RecoverySummary` provides all needed metrics |

---

## APPENDIX A: SAMPLE DATA WALKTHROUGH

### Input (sample_data.csv)

| Mark | Product | Width | Length | Qty | Expansion | Reduction |
|------|---------|-------|--------|-----|-----------|-----------|
| G01 | TA325/1 | 1115 | 1450 | 10 | 120 mm | — |
| G02 | TA325/1 | 995 | 1250 | 25 | — | — |
| G03 | TA325/1 | 965 | 1250 | 25 | — | 30 mm |
| G04 | TA325/1 | 605 | 1450 | 10 | — | 390 mm |

### Step 1: Strip Classification

| Source | Strip Width | Strip Length | Area (m²) | Qty | Classification |
|--------|------------|-------------|-----------|-----|----------------|
| G03 | 30 mm | 1250 mm | 0.0375 | 25 | DEAD_SCRAP (30 < 200) |
| G04 | 390 mm | 1450 mm | 0.5655 | 10 | REUSABLE |

### Step 2: Expansion Matching

| Demand | Exp Width | Strip Source | Strip Width | C1 | C2 | C3 | Match |
|--------|-----------|-------------|-------------|----|----|----|----|
| G01 | 120 mm | G04 | 390 mm | TA325/1=TA325/1 YES | 390>=120 YES | 1450>=1450 YES | MATCHED |

### Step 3: Recovery Impact

```
Recovered Area         = 120/1000 × 1450/1000 × 10 = 1.74 m²
Trim Waste per panel   = 390 - 120 = 270 mm
Trim Waste Area        = 270/1000 × 1450/1000 × 10 = 3.915 m²
Trim Classification    = REUSABLE (270 > 200, 0.3915 >= 0.20)

Adjusted Raw Material  = 92.7825 - 1.74 = 91.0425 m²
Yield After Recovery   = 86.19 / 91.0425 × 100 = 94.67%
Yield Improvement      = +1.78%
Recovery Rate          = 10/10 = 100%
```

---

## APPENDIX B: DESIGN DECISIONS LOG

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Recovery is additive — does not modify frozen KPI | Preserves audit integrity of Phase-1/Phase-2 baseline |
| D2 | One strip per demand (no multi-strip welding) | Manufacturing simplicity for v1.1.0; multi-strip is future |
| D3 | Same Product Code constraint for matching | Different series have different load bar pitch — incompatible welding |
| D4 | Largest demand first matching order | Greedy heuristic; maximizes chance of satisfying hard-to-match demands |
| D5 | Trim waste is reclassified recursively | Trim from a match may itself be reusable for another demand |
| D6 | New files only — no modifications to existing files except `processor.py` and `app.py` | Minimizes regression risk to frozen baseline |

---

## APPROVAL

| Role | Name | Status | Date |
|------|------|--------|------|
| Project Owner | | PENDING | |
| Manufacturing Engineer | | PENDING | |
| QA Auditor | | PENDING | |

---

**END OF DOCUMENT**

DBD_PHASE3_REV0.1 — DRAFT — Awaiting Approval
