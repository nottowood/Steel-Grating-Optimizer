# DESIGN BASIS DOCUMENT — PHASE 3: MATERIAL RECOVERY ENGINE

**Document:** DBD_PHASE3_REV0.3  
**Project:** Steel Grating Optimizer (SGO)  
**Baseline:** v1.0.0-FROZEN (commit 5ece4d2)  
**Branch:** v1.1.0-dev  
**Date:** 2026-06-22  
**Status:** FINAL DRAFT — Design Review Version

### Revision History

| Rev | Date | Changes |
|-----|------|---------|
| 0.1 | 2026-06-21 | Initial draft |
| 0.2 | 2026-06-21 | (1) Matching by manufacturing compatibility instead of Product Code. (2) Stock Piece inventory model replaces one-time strip matching. (3) Phase-3.2 Bin Packing roadmap added. (4) Separate Recovery KPIs — frozen yield untouched. (5) Complete Scrap Inventory data model. (6) Cross-Project Recovery concept in Future Extensions. |
| 0.3 | 2026-06-22 | (1) MCK expanded to 3-field key (pitch, depth, thickness) — depth determines visible profile height. (2) Post Consumption Classification — mandatory reclassification after every consumption event. (3) Validation Rules VR-19 and VR-20 added. (4) Explainability examples for Approved, Rejected, and Reclassified scenarios. (5) Freeze Readiness Checklist (Appendix D). |

---

## 1. OBJECTIVES

Phase-3 adds a Material Recovery Engine on top of the frozen Phase-1 (Rule Engine) and Phase-2 (Project Optimizer) layers.

**Primary Goal:**  
Recover usable material from reduction waste and match it to expansion demand within the same project, reducing raw material consumption.

**Secondary Goals:**
- Track all scrap and stock pieces with full traceability (source mark, dimensions, classification)
- Provide auditable recovery decisions with explainable matching logic
- Measure material recovery as a separate KPI domain — never modifying frozen yield
- Establish the commercial IP layer for future SaaS monetization

**Non-Goals (Phase-3.1 does NOT include):**
- Cross-project material pooling (concept defined in Section 13)
- Bin packing / cutting stock optimization (roadmap defined in Section 14)
- Saw scheduling or production sequencing
- Inventory persistence across sessions (future phase)

---

## 2. SCOPE

### Phase-3.1 — Material Recovery Engine (This Document)

| # | Feature | Description |
|---|---------|-------------|
| 1 | Stock Piece Engine | Classify reduction strips into reusable Stock Pieces or Dead Scrap |
| 2 | Scrap Inventory | Complete inventory of all waste — stock pieces, dead scrap, trim waste |
| 3 | Expansion Matching Engine | Match stock pieces to expansion demands by manufacturing compatibility (MCK) |
| 4 | Recovery Optimization | Select best match when multiple candidates exist; consume stock incrementally |
| 5 | Recovery KPI | Separate KPI domain for material recovery (does not touch frozen yield) |
| 6 | UI Reporting | Streamlit sections for inventory, matching, and recovery results |

### Phase-3.2 — Bin Packing / Cutting Stock (Future — See Section 14)

| # | Feature | Description |
|---|---------|-------------|
| 1 | Multi-Panel Nesting | Cut multiple panels from one stock sheet |
| 2 | Stock Length Optimization | Optimize cutting patterns along the 6000mm stock length |
| 3 | Kerf-Aware Packing | Account for 6mm saw kerf between cuts |
| 4 | Remnant Tracking | Track usable remnants from stock length cuts |

### Out of Scope (All Phases)

- Modifications to Phase-1 Rule Engine
- Modifications to Phase-2 Scoring Engine
- Modifications to frozen KPI formulas
- Multi-project inventory management (concept only in Section 13)

### Frozen Interfaces (Read-Only Access)

Phase-3 will READ the following from Phase-1/Phase-2 but will NOT modify them:

| Source | Data Used |
|--------|-----------|
| `FabricatedPanel` | `mark`, `product_code`, `fabricated_width`, `fabricated_length`, `qty`, `series`, `product_type`, `standard_width`, `load_bar_thickness`, `load_bar_pitch` (via product lookup), `expansion_width`, `reduction_width`, `needs_expansion`, `needs_reduction` |
| `ProjectSummary` | `yield_percent`, `scrap_percent`, all area totals |
| `Pattern` | `rod_qty`, `start_length` (for traceability only) |

---

## 3. DEFINITIONS

| Term | Definition |
|------|------------|
| **Reduction Strip** | The raw material removed when Fab Width < Standard Width. Width = Standard Width − Fab Width. Length = Fab Length. |
| **Stock Piece** | A Reduction Strip that passes reusability criteria and enters inventory as a consumable piece of material. Can be partially consumed. |
| **Dead Scrap** | A Reduction Strip (or remainder) that fails reusability criteria. No recovery possible. |
| **Expansion Demand** | The additional width required when Fab Width > Standard Width. Width = Fab Width − Standard Width. |
| **MCK (Manufacturing Compatibility Key)** | A 3-field tuple `(load_bar_pitch, load_bar_depth, load_bar_thickness)` that determines weld compatibility between two pieces. See Section 4. |
| **Manufacturing Compatibility** | Two pieces are weld-compatible when they share the same MCK. This guarantees identical bar spacing, bar profile height, and bar cross-section. |
| **Recovery Match** | A pairing of one Stock Piece to one Expansion Demand where the piece is MCK-compatible and dimensionally sufficient |
| **Trim Remainder** | The leftover width after cutting a stock piece for a match. Trim Remainder = Stock Piece Width − Expansion Width. The remainder stays in inventory if it meets reusability criteria. |
| **Post Consumption Classification** | Mandatory reclassification of a stock piece remainder after every consumption event. See Section 5. |
| **Recovered Area** | The area of expansion demand satisfied by a stock piece instead of new raw material |
| **Frozen Yield** | Phase-1/Phase-2 yield (NEVER modified by Phase-3) |
| **Material Recovery Rate** | Phase-3 KPI measuring how much expansion demand was satisfied by recovered material |

---

## 4. MANUFACTURING COMPATIBILITY KEY (MCK)

### Rev 0.1 Issue

Rev 0.1 used Product Code matching (`strip.source_product_code == demand.product_code`). This is overly restrictive — it prevents matching between TA325/1 and TB325/1, which have identical load bar structure and are fully weld-compatible in the width direction.

### Rev 0.2 Issue

Rev 0.2 introduced manufacturing compatibility with a 2-field key `(pitch, thickness)`. This improved matching scope but missed a critical physical constraint: **Load Bar Depth**. Two bars with the same pitch and thickness but different depth create a visible step at the weld joint, which is a manufacturing defect.

### Rev 0.3 Design — MCK (3-Field Key)

Matching is based on the **Manufacturing Compatibility Key (MCK)**, a 3-field tuple that captures all physical properties affecting weld compatibility:

#### MCK Formal Definition

```
MCK = (load_bar_pitch, load_bar_depth, load_bar_thickness)
```

Two pieces are manufacturing-compatible if and only if:

```
piece_A.MCK == piece_B.MCK
```

That is:

```
piece_A.load_bar_pitch     == piece_B.load_bar_pitch     AND
piece_A.load_bar_depth     == piece_B.load_bar_depth     AND
piece_A.load_bar_thickness == piece_B.load_bar_thickness
```

#### Why Each Field Matters

| Field | Physical Meaning | What Happens If Mismatched |
|-------|-----------------|---------------------------|
| **Load Bar Pitch** | Spacing between adjacent load bars (mm) | Bars don't align at weld joint — weld impossible |
| **Load Bar Depth** | Height of load bar profile (mm) — the vertical dimension visible from the side | Creates a visible step at weld joint — manufacturing defect. Even 5mm difference is visible and unacceptable. |
| **Load Bar Thickness** | Width of load bar cross-section (mm) | Bar cross-sections don't match — structural discontinuity at weld |

#### Properties That Do NOT Affect Width-Direction Compatibility

| Property | Why It Doesn't Matter |
|----------|----------------------|
| Cross Bar Pitch (Type A vs B) | Cross bars run perpendicular to the expansion joint — they don't need to align |
| Series number | Series is derived from pitch — it's already captured by Load Bar Pitch |
| Product Code | Multiple codes can share the same physical structure |

#### Data Model Impact

`load_bar_depth` does **NOT** exist in the current `ProductMaster` or `FabricatedPanel` data model. Phase-3 implementation must:

1. Add `load_bar_depth` field to the product data model (data-only extension, no logic change)
2. Populate depth values for all supported products
3. Make depth available through the product lookup path

This is a **data extension**, not a logic modification. It does not change any frozen calculation.

#### MCK Examples

| Strip Source | Demand Target | Pitch | Depth | Thickness | MCK Match? |
|-------------|---------------|-------|-------|-----------|------------|
| TA325/1 | TA325/1 | 60=60 | 5=5 | 25=25 | **YES** — identical MCK |
| TA325/1 | TB325/1 | 60=60 | 5=5 | 25=25 | **YES** — same MCK, different cross bar type |
| TA325/1 | TA330/1 | 60=60 | 5=5 | 25≠30 | **NO** — thickness mismatch |
| TA325/1 | TA225/2 | 60≠40 | 5=5 | 25=25 | **NO** — pitch mismatch (different series) |
| 30×5×25 | 30×3×25 | 30=30 | 5≠3 | 25=25 | **NO** — depth mismatch creates visible step at weld |

---

## 5. STOCK PIECE MODEL

### Rev 0.1 Issue

Rev 0.1 treated strips as one-time matchable items — once matched, the entire strip is consumed regardless of how much was actually needed. This wastes material when a 390mm strip satisfies a 120mm demand — the remaining 270mm disappears.

### Rev 0.2 Design

Strips enter inventory as **Stock Pieces**. When a stock piece is used to fill an expansion demand, only the required width is consumed. The remainder stays in inventory as a new stock piece (if it meets reusability criteria) or is reclassified as dead scrap.

### Stock Piece Lifecycle

```
REDUCTION detected
    → Classify strip
        → IF reusable: create Stock Piece (status = AVAILABLE)
        → IF dead scrap: create Dead Scrap record

MATCHING phase
    → Stock Piece consumed for expansion demand
        → Deduct expansion_width from stock piece
        → Remainder = stock_piece.remaining_width - expansion_width
        → Post Consumption Classification (MANDATORY — see below)

No more demands
    → Remaining AVAILABLE stock pieces stay in inventory
    → Reported as "Available Stock" (future use or cross-project recovery)
```

### Post Consumption Classification (Rev 0.3)

After **every** consumption event, the remaining stock piece **must** be reclassified. This is not optional — it is a mandatory step in the consumption flow.

#### Classification Rule

```
AFTER consumption:
    remaining_width = stock_piece.remaining_width - expansion_width

    IF remaining_width == 0:
        → Classification: EXACT_FIT
        → Status: DEPLETED
        → No remainder to record

    ELIF remaining_width > 200 AND length > 200 AND (remaining_width × length) >= 0.20 m²:
        → Classification: REUSABLE
        → Status: stays AVAILABLE
        → remaining_width updated
        → Piece remains in inventory for further matching

    ELSE:
        → Classification: DEAD_SCRAP
        → Status: DEPLETED
        → Create DeadScrapPiece record for remainder
        → Remainder width and area recorded in dead scrap
```

#### Why This Is Mandatory

Without mandatory reclassification, a stock piece could retain AVAILABLE status after being consumed to a width that is physically unusable (e.g., 30mm remaining). The next matching cycle would consider it as a candidate, waste computation, and produce an incorrect match. Post Consumption Classification prevents this by enforcing an immediate status decision.

### Stock Piece Data Model

```
StockPiece:
    piece_id              — unique identifier (auto: SP-{mark}-{seq})
    source_mark           — which panel produced this piece
    source_product_code   — product code of source panel
    load_bar_pitch        — mm (MCK field 1)
    load_bar_depth        — mm (MCK field 2) — NEW in Rev 0.3
    load_bar_thickness    — mm (MCK field 3)
    original_width        — mm (as initially cut from reduction)
    remaining_width       — mm (decreases as piece is consumed)
    length                — mm (= fabricated_length of source panel)
    original_area_m2      — original_width × length
    remaining_area_m2     — remaining_width × length
    qty                   — how many identical pieces (= source panel qty)
    status                — AVAILABLE | DEPLETED
    consumption_log       — list[ConsumptionRecord]
```

```
ConsumptionRecord:
    consumed_by_mark      — which panel consumed this piece
    width_consumed        — mm taken from this piece
    width_before          — mm before consumption
    width_after           — mm after consumption
    qty_consumed          — pieces consumed
    purpose               — EXPANSION_MATCH
    post_classification   — REUSABLE | DEAD_SCRAP | EXACT_FIT (Rev 0.3)
```

---

## 6. SCRAP INVENTORY DATA MODEL

### Complete Inventory Structure

The Scrap Inventory tracks every piece of material that is not part of a finished panel.

```
ScrapInventory:
    project_name              — project identifier
    generation_timestamp      — when inventory was generated

    # --- Source Counts ---
    total_reduction_marks     — count of marks with needs_reduction = True
    total_reduction_panels    — sum of qty for reduction marks
    total_expansion_marks     — count of marks with needs_expansion = True
    total_expansion_panels    — sum of qty for expansion marks

    # --- Stock Pieces ---
    stock_pieces              — list[StockPiece]
    total_stock_pieces        — count of pieces created (before matching)
    available_stock_pieces    — count with status = AVAILABLE (after matching)
    depleted_stock_pieces     — count with status = DEPLETED
    total_stock_area_m2       — sum of original areas
    remaining_stock_area_m2   — sum of remaining areas (after matching)

    # --- Dead Scrap ---
    dead_scrap_pieces         — list[DeadScrapPiece]
    total_dead_scrap_pieces   — count
    total_dead_scrap_area_m2  — sum of areas

    # --- Trim Waste (from matching) ---
    trim_waste_pieces         — list[TrimWastePiece]
    total_trim_waste_m2       — sum of trim waste areas
    trim_reusable_count       — how many trim pieces met reusability criteria
    trim_dead_count           — how many did not

    # --- Summary ---
    total_waste_area_m2       — dead_scrap + remaining_stock + trim_waste (total non-recovered material)
    total_recovered_area_m2   — area recovered through matching
```

### Dead Scrap Piece

```
DeadScrapPiece:
    scrap_id              — unique identifier (auto: DS-{mark}-{seq})
    source_mark           — which panel produced this scrap
    source_product_code   — product code
    width                 — mm
    length                — mm
    area_m2               — width × length
    qty                   — count
    origin                — REDUCTION | TRIM_WASTE | POST_CONSUMPTION (Rev 0.3)
    reason                — why classified as dead scrap
                            e.g. "Width 30mm < 200mm minimum"
                            e.g. "Post-consumption remainder 140mm < 200mm" (Rev 0.3)
```

### Trim Waste Piece

```
TrimWastePiece:
    trim_id               — unique identifier (auto: TW-{piece_id}-{seq})
    source_piece_id       — which stock piece produced this trim
    source_mark           — original source mark
    width                 — mm (remainder after consumption)
    length                — mm
    area_m2               — width × length
    qty                   — count
    classification        — REUSABLE | DEAD_SCRAP
    reusability_reason    — why classified this way
```

### Classification Rules

| Condition | Classification |
|-----------|---------------|
| width > 200 AND length > 200 AND area >= 0.20 m² | REUSABLE → becomes/stays Stock Piece |
| remaining_width == 0 after consumption | EXACT_FIT → DEPLETED (no remainder) |
| Otherwise | DEAD_SCRAP → recorded in Dead Scrap |

### Sample Data Inventory

Using `sample_data.csv` (before matching):

| Type | Source | Width | Length | Area (m²) | Qty | Classification |
|------|--------|-------|--------|-----------|-----|----------------|
| Reduction | G03 | 30 mm | 1250 mm | 0.0375 | 25 | DEAD_SCRAP (30 < 200) |
| Reduction | G04 | 390 mm | 1450 mm | 0.5655 | 10 | STOCK_PIECE (AVAILABLE) |

---

## 7. EXPANSION MATCHING LOGIC

### Problem Statement

When a panel requires expansion (Fab Width > Standard Width), an expansion strip must be welded to the standard panel. Currently, this strip is always assumed to come from new raw material.

Phase-3 introduces the possibility of sourcing expansion strips from stock pieces produced by reduction of other panels in the same project.

### Matching Constraints

A Stock Piece can satisfy an Expansion Demand when:

| Constraint | Rule | Rationale |
|------------|------|-----------|
| **C1: MCK Compatible** | stock.MCK == demand.MCK (all 3 fields must match) | Load bars must align (pitch), profile height must match (depth), and bar cross-section must match (thickness) for welding |
| **C2: Width Sufficient** | stock.remaining_width >= demand.expansion_width | Piece must have enough remaining width |
| **C3: Length Compatible** | stock.length >= demand.fabricated_length | Piece must be at least as long as the panel |
| **C4: Piece Available** | stock.status == AVAILABLE | Piece has not been fully consumed |
| **C5: Qty Available** | stock.qty >= demand.qty (or partial matching allowed) | Sufficient quantity of identical pieces |

### Quantity Matching

Each stock piece record represents `qty` identical physical pieces. Each expansion demand also has a `qty`. Matching must account for this:

```
IF stock.qty >= demand.qty:
    Consume demand.qty pieces from stock
    stock.qty_consumed += demand.qty
    Fully matched.
ELIF stock.qty > 0:
    Partial match: consume stock.qty pieces
    Remaining demand = demand.qty - stock.qty
    Continue searching for more stock pieces to fill remaining demand.
```

### Matching Process

```
FOR each expansion demand (sorted by expansion_width descending — largest first):
    remaining_demand_qty = demand.qty
    
    WHILE remaining_demand_qty > 0:
        Find all stock pieces matching C1, C2, C3, C4
        IF candidates exist:
            Select best match (see Section 8)
            pieces_to_use = MIN(best.qty_available, remaining_demand_qty)
            Consume: deduct expansion_width from best.remaining_width
            Record consumption log entry
            remaining_demand_qty -= pieces_to_use
            
            → Post Consumption Classification (MANDATORY)
                IF remaining_width == 0 → EXACT_FIT, mark DEPLETED
                ELIF remainder meets reusability → REUSABLE, stays AVAILABLE
                ELSE → DEAD_SCRAP, mark DEPLETED, create DeadScrapPiece
        ELSE:
            Mark remaining demand as UNMATCHED
            BREAK
```

### Why MCK Instead of Product Code?

Real-world example:

```
Project has:
  - Mark A: TA325/1 (Series 3, Type A, 25mm) — needs 120mm expansion
  - Mark B: TB325/1 (Series 3, Type B, 25mm) — has 300mm reduction

Rev 0.1: NO MATCH (different product code: TA325/1 ≠ TB325/1)
Rev 0.2: MATCH (same pitch=60mm, same thickness=25mm → weld compatible)
Rev 0.3: MATCH (same MCK: pitch=60, depth=5, thickness=25 → weld compatible)
```

The physical constraint is bar alignment (pitch), profile height (depth), and bar cross-section (thickness). Cross bar configuration does not affect width-direction weld compatibility.

### Sample Data Expectation

| Demand | Exp Width | Stock Source | Stock Width | MCK (pitch,depth,thick) | C2 | C3 | Match |
|--------|-----------|-------------|-------------|-------------------------|----|----|-------|
| G01 (120mm exp) | 120 mm | G04 (390mm stock) | 390 mm | (60,5,25)=(60,5,25) YES | 390>=120 YES | 1450>=1450 YES | MATCHED |

After matching:
- G04 stock piece: remaining_width = 390 − 120 = 270mm
- Post Consumption Classification: width 270 > 200, length 1450 > 200, area 0.3915 >= 0.20 → **REUSABLE** → stays AVAILABLE in inventory

---

## 8. RECOVERY OPTIMIZATION ALGORITHM

### Objective

When multiple stock pieces can satisfy a single expansion demand, select the one that minimizes waste while preserving larger pieces for harder-to-match future demands.

### Selection Criteria (Priority Order)

| Priority | Criterion | Rationale |
|----------|-----------|-----------|
| **R1** | Minimum Trim Waste | Smallest (remaining_width − expansion_width) wastes least material |
| **R2** | Exact Length Match | stock.length == demand.fabricated_length avoids length-direction cutting |
| **R3** | Smallest Remaining Width | When trim waste is equal, use the piece with least remaining width to preserve larger pieces |
| **R4** | Highest Qty Available | Prefer pieces that can fully satisfy the demand qty in one match |

### Decision Sort Key

```
sort_key = (
    stock.remaining_width - demand.expansion_width,    # R1: min trim waste (ascending)
    0 if stock.length == demand.fabricated_length else 1,  # R2: exact length first
    stock.remaining_width,                              # R3: smallest piece first (ascending)
    -stock.qty_available,                               # R4: highest qty first (descending)
)
```

### Explainability

Every match decision must record:

```
RecoveryMatch:
    demand_mark             — panel needing expansion
    demand_product_code     — product code of demand panel
    expansion_width         — width needed (mm)
    demand_length           — panel length (mm)
    demand_qty              — panels matched in this record
    stock_piece_id          — which stock piece was used
    source_mark             — which panel originally produced the stock piece
    stock_original_width    — original stock piece width (mm)
    stock_width_before      — remaining width before this match (mm)
    stock_width_after       — remaining width after this match (mm)
    trim_waste              — width_before - expansion_width (mm)
    trim_classification     — REUSABLE | DEAD_SCRAP | EXACT_FIT (Rev 0.3)
    post_consumption_class  — REUSABLE | DEAD_SCRAP | EXACT_FIT (Rev 0.3)
    candidate_count         — how many stock pieces were considered
    decision_reason         — why this piece was selected
    rejection_log           — list of (piece_id, reason) for rejected candidates
    mck                     — (pitch, depth, thickness) — the MCK used for this match (Rev 0.3)
```

---

## 9. RECOVERY KPI — SEPARATE FROM FROZEN YIELD

### Rev 0.1 Issue

Rev 0.1 defined "Yield After Recovery" which recalculated Raw Material Area after deducting recovered material. Although the frozen yield value was preserved alongside it, the concept of a second yield number invites confusion — users may not know which yield to report, and the "adjusted" yield implicitly modifies the frozen KPI meaning.

### Rev 0.2 Design

Phase-3 introduces a **completely separate KPI domain** for material recovery. The frozen Yield is never recalculated, reinterpreted, or displayed with an alternative value.

### Recovery KPI Definitions

| KPI | Formula | Unit |
|-----|---------|------|
| **Total Reduction Area** | Sum of (reduction_width × fab_length × qty) for all reduction panels | m² |
| **Total Expansion Demand Area** | Sum of (expansion_width × fab_length × qty) for all expansion panels | m² |
| **Recovered Area** | Sum of (expansion_width × fab_length × matched_qty) for matched demands | m² |
| **Unrecovered Area** | Total Expansion Demand Area − Recovered Area | m² |
| **Recovery Rate** | Recovered Area / Total Expansion Demand Area × 100 | % |
| **Stock Utilization Rate** | Area consumed from stock pieces / Total Stock Piece Area × 100 | % |
| **Dead Scrap Area** | Sum of all dead scrap piece areas | m² |
| **Remaining Stock Area** | Sum of remaining_area for AVAILABLE stock pieces | m² |
| **Material Recovery Score** | (Recovered Area / Total Reduction Area) × 100 | % |

### What Each KPI Tells You

| KPI | Business Meaning |
|-----|-----------------|
| Recovery Rate | "What fraction of our expansion needs did we satisfy from waste?" |
| Stock Utilization Rate | "How much of our usable waste did we actually use?" |
| Material Recovery Score | "How much of our total reduction waste did we recover?" |
| Dead Scrap Area | "How much material is truly wasted with no recovery possible?" |
| Remaining Stock Area | "How much usable material is left over for future use?" |

### Frozen KPI — Untouched

The following KPIs remain exactly as calculated by Phase-1/Phase-2. They are displayed in their existing UI locations. Phase-3 does NOT add alternative values, adjusted values, or "after recovery" variants.

| Frozen KPI | Location | Phase-3 Impact |
|------------|----------|----------------|
| Sold Area | Section 3 | NONE |
| Production Area | Section 3 | NONE |
| Raw Material Area | Section 3 | NONE |
| Yield | Section 3 | NONE |
| Scrap | Section 3 | NONE |

### Sample Data Expectation

```
Total Reduction Area     = (30/1000 × 1250/1000 × 25) + (390/1000 × 1450/1000 × 10)
                         = 0.9375 + 5.655 = 6.5925 m²

Total Expansion Demand   = 120/1000 × 1450/1000 × 10 = 1.74 m²

Recovered Area           = 1.74 m² (G01 fully matched to G04 stock)
Unrecovered Area         = 0.00 m²
Recovery Rate            = 1.74 / 1.74 × 100 = 100%

Stock Piece Area (G04)   = 390/1000 × 1450/1000 × 10 = 5.655 m²
Area Consumed            = 120/1000 × 1450/1000 × 10 = 1.74 m²
Stock Utilization Rate   = 1.74 / 5.655 × 100 = 30.77%

Remaining Stock Area     = 270/1000 × 1450/1000 × 10 = 3.915 m² (still AVAILABLE)
Dead Scrap Area          = 30/1000 × 1250/1000 × 25 = 0.9375 m²

Material Recovery Score  = 1.74 / 6.5925 × 100 = 26.39%
```

---

## 10. VALIDATION RULES

Phase-3 adds validation rules that run alongside the existing 9 rules (Rules 1-9 are FROZEN).

### Existing Rules (R10–R18 from Rev 0.2)

| Rule | Description | Check |
|------|-------------|-------|
| R10 | Strip Classification Complete | Every reduction panel produces exactly one inventory record (StockPiece or DeadScrap) |
| R11 | No Over-Consumption | stock.remaining_width >= 0 for all stock pieces after matching |
| R12 | MCK Verified | Every match satisfies C1 (all 3 MCK fields must match) |
| R13 | Qty Balanced | Sum of matched qty <= source strip qty for every stock piece |
| R14 | Recovered Area Consistent | Sum of individual match recovered areas == total recovered area |
| R15 | Recovery Rate Bounded | 0% <= Recovery Rate <= 100% |
| R16 | Inventory Balanced | Stock Pieces Created = Depleted + Available (status accounting) |
| R17 | Dead Scrap Accounted | Dead Scrap from classification + Dead Scrap from trim + Dead Scrap from post-consumption = Total Dead Scrap |
| R18 | Frozen KPI Unchanged | Phase-3 yield_percent == Phase-1/Phase-2 yield_percent (bit-exact) |

### New Rules (Rev 0.3)

| Rule | Description | Check |
|------|-------------|-------|
| **R19** | **MCK 3-Field Validation** | Every recovery match must have all 3 MCK fields (pitch, depth, thickness) verified. A match where ANY field differs is REJECTED. Specifically: `stock.load_bar_pitch == demand.load_bar_pitch AND stock.load_bar_depth == demand.load_bar_depth AND stock.load_bar_thickness == demand.load_bar_thickness`. If `load_bar_depth` is NULL or missing for either side, the match is REJECTED (fail-closed). |
| **R20** | **Post Consumption Classification Validation** | Every consumption event must produce exactly one classification result: REUSABLE, DEAD_SCRAP, or EXACT_FIT. The classification must be consistent with the remaining dimensions: (a) EXACT_FIT requires remaining_width == 0; (b) REUSABLE requires width > 200 AND length > 200 AND area >= 0.20 m²; (c) DEAD_SCRAP requires the piece fails the REUSABLE criteria AND remaining_width > 0. Any consumption event without a classification is a validation failure. |

---

## 11. EXPLAINABILITY REQUIREMENTS

Phase-3 must maintain the same explainability standard as Phase-2.

### Required UI Sections

| Section | Content |
|---------|---------|
| **11. Scrap Inventory** | All reduction strips with classification, dimensions, source mark, status |
| **12. Stock Piece Inventory** | Available stock pieces with remaining width, consumption history |
| **13. Expansion Demand** | All expansion panels with required width, matched/unmatched status |
| **14. Recovery Matching** | Each match with source piece, target panel, width consumed, remainder, decision reason |
| **15. Recovery KPI Summary** | All Recovery KPIs from Section 9 |

### Audit Trail

Every recovery decision must be fully traceable:

```
Panel G01 (expansion 120mm, qty=10)
  ← Matched to Stock Piece SP-G04-001 (original 390mm, remaining 390mm)
  → Width consumed: 120mm
  → Remainder: 270mm
  → Post Consumption Classification: REUSABLE (270>200, 1450>200, 0.3915≥0.20)
  → Candidates considered: 1
  → Decision: Only compatible stock piece available
  → MCK: (60, 5, 25)
```

```
Stock Piece SP-G04-001 (from G04, qty=10)
  Original: 390mm × 1450mm = 0.5655 m²
  MCK: (pitch=60, depth=5, thickness=25)
  Consumption #1: 120mm for G01 (10 pieces)
  Post Consumption: REUSABLE
  Remaining: 270mm × 1450mm = 0.3915 m² (AVAILABLE)
```

### Explainability Examples (Rev 0.3)

#### Example 1: Match Approved

```
MATCH APPROVED
  Demand:  G01, expansion_width=120mm, length=1450mm, qty=10
  Stock:   SP-G04-001, remaining_width=390mm, length=1450mm, qty=10
  MCK Check:
    Pitch:     60 == 60  ✓
    Depth:      5 == 5   ✓
    Thickness: 25 == 25  ✓
  Width Check:  390 >= 120  ✓
  Length Check: 1450 >= 1450  ✓
  Result: MATCHED
  Width Consumed: 120mm
  Remainder: 270mm → Post Consumption Classification: REUSABLE
```

#### Example 2: Match Rejected — Load Bar Depth Mismatch

```
MATCH REJECTED
  Demand:  G10, expansion_width=100mm, length=1200mm, qty=5
  Stock:   SP-G20-001, remaining_width=350mm, length=1200mm, qty=8
  MCK Check:
    Pitch:     30 == 30  ✓
    Depth:      5 ≠  3   ✗  ← REJECTED
    Thickness: 25 == 25  ✓
  Result: REJECTED — Load Bar Depth mismatch (5mm vs 3mm)
  Reason: Depth difference creates visible step at weld joint
```

#### Example 3: Inventory Reclassified After Consumption

```
POST CONSUMPTION CLASSIFICATION
  Stock Piece: SP-G15-001
  Before Consumption: remaining_width=250mm, length=1000mm
  Width Consumed: 110mm (for G12 expansion)
  After Consumption: remaining_width=140mm
  Classification Check:
    Width:  140mm < 200mm  ✗  ← FAILS minimum width
  Result: DEAD_SCRAP
  Action: Status changed to DEPLETED
          DeadScrapPiece created: DS-G15-001-T1
          Width=140mm, Length=1000mm, Area=0.14 m²
          Origin=POST_CONSUMPTION
          Reason="Post-consumption remainder 140mm < 200mm minimum"
```

---

## 12. DATA MODEL

### New Files

| File | Purpose |
|------|---------|
| `recovery_models.py` | Data models for stock pieces, dead scrap, matches, inventory, recovery summary |
| `recovery_engine.py` | Stock piece generation, MCK matching, recovery optimization |

### Existing Files Modified

| File | Change |
|------|--------|
| `processor.py` | Add `process_panels_with_recovery()` function — new entry point, existing functions untouched |
| `app.py` | Add Sections 11-15 for recovery reporting — existing sections untouched |
| `models.py` | Add `load_bar_depth` field to `ProductMaster` — data-only extension |
| `product_master.py` | Add depth values to product catalog — data-only extension |

### Data Classes

```python
@dataclass
class StockPiece:
    piece_id: str                   # SP-{mark}-{seq}
    source_mark: str
    source_product_code: str
    load_bar_pitch: float           # mm — MCK field 1
    load_bar_depth: float           # mm — MCK field 2 (NEW Rev 0.3)
    load_bar_thickness: float       # mm — MCK field 3
    original_width: float           # mm
    remaining_width: float          # mm (decreases on consumption)
    length: float                   # mm
    original_area_m2: float
    remaining_area_m2: float
    qty: int
    status: str                     # AVAILABLE | DEPLETED
    consumption_log: list = field(default_factory=list)

    @property
    def mck(self) -> tuple:
        """Manufacturing Compatibility Key — 3-field tuple."""
        return (self.load_bar_pitch, self.load_bar_depth, self.load_bar_thickness)


@dataclass
class ConsumptionRecord:
    consumed_by_mark: str
    width_consumed: float           # mm
    width_before: float             # mm
    width_after: float              # mm
    qty_consumed: int
    purpose: str                    # EXPANSION_MATCH
    post_classification: str        # REUSABLE | DEAD_SCRAP | EXACT_FIT (Rev 0.3)


@dataclass
class DeadScrapPiece:
    scrap_id: str                   # DS-{mark}-{seq}
    source_mark: str
    source_product_code: str
    width: float                    # mm
    length: float                   # mm
    area_m2: float
    qty: int
    origin: str                     # REDUCTION | TRIM_WASTE | POST_CONSUMPTION
    reason: str                     # e.g. "Width 30mm < 200mm minimum"


@dataclass
class RecoveryMatch:
    demand_mark: str
    demand_product_code: str
    expansion_width: float          # mm
    demand_length: float            # mm
    demand_qty: int
    stock_piece_id: str
    source_mark: str
    stock_original_width: float     # mm
    stock_width_before: float       # mm
    stock_width_after: float        # mm
    trim_waste: float               # mm
    trim_classification: str        # REUSABLE | DEAD_SCRAP | EXACT_FIT
    post_consumption_class: str     # REUSABLE | DEAD_SCRAP | EXACT_FIT (Rev 0.3)
    candidate_count: int
    decision_reason: str
    mck: tuple                      # (pitch, depth, thickness) — Rev 0.3
    rejection_log: list = field(default_factory=list)


@dataclass
class ScrapInventory:
    project_name: str
    total_reduction_marks: int
    total_reduction_panels: int
    total_expansion_marks: int
    total_expansion_panels: int
    stock_pieces: list[StockPiece]       = field(default_factory=list)
    dead_scrap_pieces: list[DeadScrapPiece] = field(default_factory=list)
    total_stock_pieces: int = 0
    available_stock_pieces: int = 0
    depleted_stock_pieces: int = 0
    total_stock_area_m2: float = 0.0
    remaining_stock_area_m2: float = 0.0
    total_dead_scrap_pieces: int = 0
    total_dead_scrap_area_m2: float = 0.0
    total_waste_area_m2: float = 0.0


@dataclass
class RecoverySummary:
    # --- Inventory ---
    inventory: ScrapInventory

    # --- Matching Results ---
    matches: list[RecoveryMatch]        = field(default_factory=list)
    unmatched_demands: list[dict]       = field(default_factory=list)

    # --- Recovery KPIs ---
    total_reduction_area_m2: float = 0.0
    total_expansion_demand_m2: float = 0.0
    recovered_area_m2: float = 0.0
    unrecovered_area_m2: float = 0.0
    recovery_rate: float = 0.0          # %
    stock_utilization_rate: float = 0.0  # %
    dead_scrap_area_m2: float = 0.0
    remaining_stock_area_m2: float = 0.0
    material_recovery_score: float = 0.0 # %

    # --- Frozen KPI Reference (read-only, for display) ---
    frozen_yield: float = 0.0           # % (copied from Phase-1/2, never recalculated)
```

### Integration Point

```python
# In processor.py — new function (Phase-1 and Phase-2 functions UNCHANGED)
def process_panels_with_recovery(panels):
    processed, summary, opt_summary, warnings = process_panels_optimized(panels)
    recovery_summary = run_recovery_engine(processed, summary)
    return processed, summary, opt_summary, recovery_summary, warnings
```

---

## 13. FUTURE EXTENSION: CROSS-PROJECT RECOVERY

### Concept

In production, multiple projects run concurrently or sequentially. Stock pieces left over from Project A may satisfy expansion demands in Project B.

### Architecture Concept

```
Project A runs → produces Stock Pieces → unmatched pieces enter Global Stock Pool
Project B runs → checks Global Stock Pool before requesting new raw material
```

### Requirements for Future Implementation

| Requirement | Phase-3.1 Foundation |
|-------------|---------------------|
| Unique piece identification across projects | `piece_id` format supports project prefix: `SP-{project}-{mark}-{seq}` |
| Compatibility matching across projects | MCK `(pitch, depth, thickness)` is product-agnostic |
| Stock piece status tracking | `status` field (AVAILABLE/DEPLETED) already supports pool queries |
| Consumption audit trail | `consumption_log` records which project consumed each piece |
| Persistence | Requires database/file storage — NOT in Phase-3.1 scope |

### Why Not Now

Cross-project recovery requires:
1. Persistent storage (stock pieces must survive across sessions)
2. Concurrency control (two projects may compete for the same piece)
3. Age tracking (old stock pieces may be physically damaged or lost)
4. Physical location tracking (pieces must be findable in the factory)

These are infrastructure concerns that exceed Phase-3.1 scope. However, the data model is designed so that adding persistence later requires no structural changes — only adding a storage layer beneath the existing in-memory model.

---

## 14. FUTURE EXTENSION: PHASE-3.2 BIN PACKING / CUTTING STOCK

### Concept

Phase-3.1 recovers material in the width direction only (expansion strips from reduction waste). Phase-3.2 extends recovery to the length direction — optimizing how panels are cut from standard 6000mm stock lengths.

### Problem Statement

Currently, each panel is assumed to consume one full standard-width stock piece, regardless of length. A 1250mm panel wastes 4750mm of a 6000mm stock length. If two 1250mm panels can be cut from one stock length (with 6mm kerf), raw material consumption halves.

### Phase-3.2 Scope (Roadmap Only)

| Feature | Description |
|---------|-------------|
| **Length Nesting** | Pack multiple panels of the same width into one stock length |
| **Kerf Accounting** | Deduct 6mm per cut from available length |
| **Remnant Tracking** | Track usable remnants from partially-used stock lengths |
| **Width + Length Recovery** | Combine Phase-3.1 width recovery with Phase-3.2 length packing |
| **Optimization Algorithm** | First Fit Decreasing (FFD) or similar bin packing heuristic |

### Prerequisites from Phase-3.1

| Phase-3.1 Provides | Phase-3.2 Uses |
|--------------------|----------------|
| Stock Piece model with remaining dimensions | Input to bin packing algorithm |
| MCK | Constraint for which panels can share a stock length |
| Consumption log | Extended to track length-direction cuts |
| Scrap Inventory | Extended to include length-direction remnants |

### Constraints

```
Stock Length = 6000 mm
Saw Kerf = 6 mm
Usable Length per stock = 6000 - (N-1) × 6   where N = number of panels cut

Panel length for cutting = Fabricated Length (banding is part of the panel)
```

### Example

```
Two panels: Mark A (1250mm) and Mark B (1250mm), same MCK
Stock length: 6000mm
Cut plan: A(1250) + kerf(6) + B(1250) = 2506mm used
Remnant: 6000 - 2506 = 3494mm (large remnant, potentially reusable)
```

### Why Not Now

Bin packing is a fundamentally different optimization problem (NP-hard) that requires:
1. Different algorithm family (FFD, BFD, or constraint programming)
2. Interaction with Phase-2 common start selection (panels in a floor group may need identical patterns)
3. Stock length inventory management
4. More complex remnant tracking

Phase-3.1 establishes the inventory and tracking infrastructure. Phase-3.2 builds the optimization on top.

---

## APPENDIX A: SAMPLE DATA WALKTHROUGH (REV 0.3)

### Input (sample_data.csv)

| Mark | Product | Width | Length | Qty | Exp | Red | MCK (pitch,depth,thick) |
|------|---------|-------|--------|-----|-----|-----|-------------------------|
| G01 | TA325/1 | 1115 | 1450 | 10 | 120mm | — | (60, 5, 25) |
| G02 | TA325/1 | 995 | 1250 | 25 | — | — | (60, 5, 25) |
| G03 | TA325/1 | 965 | 1250 | 25 | — | 30mm | (60, 5, 25) |
| G04 | TA325/1 | 605 | 1450 | 10 | — | 390mm | (60, 5, 25) |

### Step 1: Stock Piece Generation

| Source | Width | Length | Area (m²) | Qty | Classification | Reason |
|--------|-------|--------|-----------|-----|----------------|--------|
| G03 | 30 mm | 1250 mm | 0.0375 | 25 | DEAD_SCRAP | Width 30mm < 200mm |
| G04 | 390 mm | 1450 mm | 0.5655 | 10 | STOCK_PIECE | Width 390>200, Length 1450>200, Area 0.5655>=0.20 |

### Step 2: Expansion Matching

```
Demand: G01, expansion=120mm, length=1450mm, qty=10
  MCK: (60, 5, 25)

Available stock:
  SP-G04-001: width=390mm, length=1450mm, qty=10, MCK=(60,5,25)
    C1 (MCK): (60,5,25)==(60,5,25) → PASS
    C2: 390 >= 120 → PASS
    C3: 1450 >= 1450 → PASS
    C4: AVAILABLE → PASS
    C5: 10 >= 10 → PASS

Match: G01 ← SP-G04-001
  Width consumed: 120mm
  Remaining: 390 - 120 = 270mm
```

### Step 3: Post Consumption Classification

```
SP-G04-001 after consumption:
  Remaining width: 270mm
  Length: 1450mm
  Check: 270 > 200 ✓ AND 1450 > 200 ✓ AND 0.3915 >= 0.20 ✓
  Classification: REUSABLE
  Action: stays AVAILABLE with remaining_width = 270mm
```

### Step 4: Final Inventory State

| Piece | Status | Original Width | Remaining Width | Area (m²) | MCK |
|-------|--------|---------------|-----------------|-----------|-----|
| SP-G04-001 | AVAILABLE | 390 mm | 270 mm | 0.3915 | (60,5,25) |
| DS-G03-001 | DEAD_SCRAP | 30 mm | — | 0.0375 | — |

### Step 5: Recovery KPIs

```
Total Reduction Area         = 0.9375 + 5.655 = 6.5925 m²
Total Expansion Demand       = 1.74 m²
Recovered Area               = 1.74 m²
Recovery Rate                = 100%
Stock Utilization Rate       = 1.74 / 5.655 = 30.77%
Material Recovery Score      = 1.74 / 6.5925 = 26.39%
Dead Scrap Area              = 0.9375 m²
Remaining Stock Area         = 3.915 m²

Frozen Yield (unchanged)     = 92.89%
```

---

## APPENDIX B: DESIGN DECISIONS LOG

| # | Decision | Rationale | Rev |
|---|----------|-----------|-----|
| D1 | Recovery is additive — frozen KPIs never modified | Preserves audit integrity of Phase-1/Phase-2 baseline | 0.1 |
| D2 | One strip per demand (no multi-strip welding in v1.1.0) | Manufacturing simplicity; multi-strip is future | 0.1 |
| D3 | ~~Same Product Code~~ → ~~(pitch, thickness)~~ → **MCK (pitch, depth, thickness)** | Product Code overly restrictive; 2-field key missed depth mismatch defect | **0.3** |
| D4 | Largest demand first matching order | Greedy heuristic; maximizes chance of satisfying hard-to-match demands | 0.1 |
| D5 | ~~One-time strip matching~~ → Consumable Stock Pieces with remainder tracking | One-time matching wastes the remainder of oversized strips | 0.2 |
| D6 | New files only — no modifications to existing files except `processor.py`, `app.py`, `models.py`, `product_master.py` | Minimizes regression risk to frozen baseline. `models.py` and `product_master.py` receive data-only extension (load_bar_depth). | **0.3** |
| D7 | Separate Recovery KPI domain — no "Yield After Recovery" | Avoids confusion with frozen yield; recovery is a different measurement axis | 0.2 |
| D8 | Phase-3.2 Bin Packing deferred — roadmap only | Different algorithm family (NP-hard), needs infrastructure from Phase-3.1 first | 0.2 |
| D9 | Cross-Project Recovery concept documented but deferred | Requires persistence layer, concurrency control, physical tracking | 0.2 |
| D10 | Post Consumption Classification is mandatory | Without it, depleted pieces remain AVAILABLE and pollute matching candidates | **0.3** |
| D11 | MCK fail-closed on missing depth | If load_bar_depth is NULL/missing, reject the match rather than assume compatibility | **0.3** |

---

## APPENDIX C: REVISION CHANGE SUMMARY

### Rev 0.1 → Rev 0.2

| Area | Rev 0.1 | Rev 0.2 | Reason |
|------|---------|---------|--------|
| Matching Constraint C1 | Same Product Code | Same (pitch, thickness) | TA/TB with same pitch+thickness are weld-compatible |
| Strip Model | One-time match; strip fully consumed | Stock Piece with remaining_width; incrementally consumed | Preserves usable remainder after partial consumption |
| Trim Waste | Recorded but not reused | Remainder stays in inventory if reusable | Eliminates material waste from oversized matches |
| Yield Impact | "Yield After Recovery" recalculates raw material area | Separate Recovery KPIs; frozen yield untouched | No confusion between frozen and adjusted metrics |
| Scrap Inventory | Minimal model (counts + areas) | Complete model: StockPiece, DeadScrapPiece, TrimWastePiece, ScrapInventory | Full traceability and audit coverage |
| Future Phases | Brief mention | Section 13 (Cross-Project) + Section 14 (Bin Packing roadmap) | Clear development pathway |

### Rev 0.2 → Rev 0.3

| Area | Rev 0.2 | Rev 0.3 | Reason |
|------|---------|---------|--------|
| Compatibility Key | 2-field `(pitch, thickness)` | 3-field MCK `(pitch, depth, thickness)` | Depth mismatch creates visible step at weld joint — manufacturing defect |
| Key Name | `compatibility_key` | `MCK` (Manufacturing Compatibility Key) | Formal name for 3-field tuple; used consistently throughout |
| Post Consumption | Informal check in lifecycle | Mandatory Post Consumption Classification with 3 outcomes (REUSABLE, DEAD_SCRAP, EXACT_FIT) | Prevents depleted pieces from polluting matching candidates |
| Validation | R10–R18 | R10–R20 (+R19 MCK 3-field, +R20 Post Consumption) | Ensures MCK completeness and classification consistency |
| Explainability | Audit trail only | Audit trail + 3 worked examples (Approved, Rejected, Reclassified) | Concrete illustrations of decision logic |
| Data Model | `load_bar_depth` absent | `load_bar_depth` added to StockPiece, referenced in MCK | Required for 3-field MCK validation |
| Modified Files | `processor.py`, `app.py` only | + `models.py`, `product_master.py` (data-only depth extension) | Depth field must exist in product data model |
| ConsumptionRecord | No classification field | `post_classification` field added | Records the outcome of mandatory post-consumption check |
| DeadScrapPiece origin | REDUCTION, TRIM_WASTE | + POST_CONSUMPTION | Tracks dead scrap created by post-consumption reclassification |

---

## APPENDIX D: FREEZE READINESS CHECKLIST

Before approving this DBD for Phase-3.1 implementation, verify all items:

- [ ] **Frozen KPI Isolation** — Recovery KPIs are completely separate from frozen yield. No "Yield After Recovery" or adjusted yield values exist. Frozen Yield, Sold Area, Production Area, Raw Material Area, and Scrap remain untouched.

- [ ] **Recovery KPI Completeness** — All 5 recovery KPIs are defined with formulas: Recovery Rate, Stock Utilization Rate, Material Recovery Score, Dead Scrap Area, Remaining Stock Area.

- [ ] **MCK 3-Field Definition** — Manufacturing Compatibility Key is formally defined as `(load_bar_pitch, load_bar_depth, load_bar_thickness)`. All 3 fields must match for weld compatibility. Fail-closed on missing depth.

- [ ] **Post Consumption Classification** — Mandatory reclassification after every consumption event. Three outcomes: REUSABLE (stays AVAILABLE), DEAD_SCRAP (DEPLETED + scrap record), EXACT_FIT (DEPLETED, no remainder).

- [ ] **Validation Rules R19–R20** — R19 validates MCK 3-field completeness (reject if any field missing or mismatched). R20 validates post-consumption classification consistency with remaining dimensions.

- [ ] **Explainability** — Three worked examples cover: Match Approved (MCK compatible), Match Rejected (depth mismatch), and Inventory Reclassified (post-consumption dead scrap).

- [ ] **Data Model Extension** — `load_bar_depth` identified as a NEW field not in current data model. Must be added to `ProductMaster`/`FabricatedPanel` as a data-only extension. No logic changes to frozen code.

- [ ] **Phase-3.2 Roadmap** — Bin Packing deferred with clear prerequisites from Phase-3.1. No commitment to specific algorithm or timeline.

---

## APPROVAL

| Role | Name | Status | Date |
|------|------|--------|------|
| Project Owner | | PENDING | |
| Manufacturing Engineer | | PENDING | |
| QA Auditor | | PENDING | |

---

**END OF DOCUMENT**

DBD_PHASE3_REV0.3 — FINAL DRAFT — Design Review Version
