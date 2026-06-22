# DESIGN BASIS DOCUMENT — PHASE-3.2

## Cutting Stock Optimization Engine

**Document ID:** DBD_PHASE3.2_REV0.4  
**Date:** 2026-06-22  
**Author:** Claude (AI)  
**Status:** APPROVED  
**Baseline:** v1.1.0-RC1 (commit ac1750a)  
**Design Authority:** DBD_PHASE3_REV0.3 (Phase-3.1)

---

## REVISION HISTORY

| Rev | Date | Author | Changes |
|-----|------|--------|---------|
| 0.1 | 2026-06-22 | Claude | Initial draft — feature evaluation, design proposal |
| 0.2 | 2026-06-22 | Claude | Resolved Q1-Q4: stock length model, optimization objective, remnant strategy, packing granularity. Rewrote Sections 3.1.1-3.1.6. Added Design Decisions appendix. |
| 0.3 | 2026-06-22 | Claude | Resolved Q5 (kerf model). Q3 updated: separate configurable thresholds for length remnants. Fixed arithmetic in sample walkthrough. |
| 0.4 | 2026-06-22 | Claude | Added FFD baseline reference (Section 5.4). Status → APPROVED. |

### Rev 0.4 Changes Summary

| # | Change | Section |
|---|--------|---------|
| C12 | Added FFD as baseline reference algorithm for validation and regression | 5.4 |
| C13 | Defined invariants for future algorithm additions | 5.4 |
| C14 | Status changed from DRAFT to APPROVED | Header |

### Rev 0.3 Changes Summary

| # | Change | Section |
|---|--------|---------|
| C7 | Added kerf model (Q5) — N cuts per N panels, total kerf = N × SAW_KERF | 3.1.5 |
| C8 | Length remnant thresholds now independent and configurable (not reusing width thresholds) | 3.1.6 |
| C9 | Fixed arithmetic in sample walkthrough (N-1 → N kerfs) | 10.2 |
| C10 | Updated R23 kerf validation rule to match N-cut model | 6.2 |
| C11 | Updated explainability example to match N-cut model | 7.1 |

### Rev 0.2 Changes Summary

| # | Change | Section |
|---|--------|---------|
| C1 | Added stock length model decision (single, extensible) | 3.1.1 |
| C2 | Added primary optimization objective (minimize stock lengths consumed) | 3.1.2 |
| C3 | Added length remnant strategy (3-tier classification) | 3.1.6 |
| C4 | Changed packing granularity to individual quantity units | 3.1.3 |
| C5 | Added Design Decisions appendix | Appendix A |
| C6 | Updated sample walkthrough with exact bin allocations | 10.2 |

---

## 1. FEATURE EVALUATION

### 1.1 Candidate Assessment

Five candidate features were evaluated for Phase-3.2. Each is scored against four criteria: Business Value (impact on material cost), Technical Feasibility (complexity relative to current architecture), Foundation Readiness (how much Phase-3.1 infrastructure supports it), and Risk (implementation risk to frozen baseline).

| # | Feature | Business Value | Feasibility | Foundation | Risk | Recommendation |
|---|---------|---------------|-------------|------------|------|---------------|
| 1 | **Cutting Stock Optimization** | HIGH | MEDIUM | HIGH | LOW | **INCLUDE** |
| 2 | **Material Recovery Maximization** | MEDIUM | MEDIUM | HIGH | LOW | **INCLUDE** |
| 3 | Inventory Utilization Optimization | MEDIUM | LOW | HIGH | LOW | DEFER (subset of #1) |
| 4 | Bin Packing Engine | HIGH | LOW | MEDIUM | MEDIUM | DEFER (subset of #1) |
| 5 | Cross-Project Recovery | HIGH | LOW | LOW | HIGH | DEFER (requires persistence) |

### 1.2 Evaluation Rationale

**Feature 1 — Cutting Stock Optimization: INCLUDE**

Currently each panel consumes one full 6000mm stock length regardless of fabricated length. A 1250mm panel wastes 4750mm (79.2% waste in the length direction). Packing multiple panels into one stock length directly reduces raw material consumption.

Phase-3.1 provides MCK matching, stock tracking, and consumption audit — all prerequisites. The optimization is additive: it improves how stock lengths are allocated but does not change panel dimensions, patterns, or frozen KPIs.

**Feature 2 — Material Recovery Maximization: INCLUDE**

Phase-3.1 matching has three limitations that leave recoverable material unmatched:
- A demand with qty=10 matched against stock with qty=5 only recovers 5 — the remaining 5 go unmatched.
- After a match reduces a stock piece, the remainder may satisfy a smaller demand — but the current engine does not re-scan.
- Multiple matches in sequence may cascade (trim from Match 1 feeds Match 2) — not implemented.

Fixing these limitations maximizes the output of the existing engine without new algorithms.

**Feature 3 — Inventory Utilization Optimization: DEFER**

This is a subset of Feature 1. Optimizing how existing inventory pieces are consumed across demands is already handled by improving the matching engine (#2) and packing (#1).

**Feature 4 — Bin Packing Engine: DEFER (absorbed into #1)**

Pure bin packing (fitting items into bins) is the algorithmic core of Feature 1. Rather than implementing a generic bin packing library, Feature 1 applies cutting-stock-specific constraints (kerf, MCK, length direction) directly.

**Feature 5 — Cross-Project Recovery: DEFER**

Requires persistent storage, concurrency control, age tracking, and physical location management. These are infrastructure concerns beyond the current in-memory architecture. Phase-3.1 data models support future extension (as designed in DBD Rev 0.3 Section 13), but implementation is premature.

### 1.3 Phase-3.2 Scope Decision

Phase-3.2 implements two features:

| ID | Feature | Codename |
|----|---------|----------|
| F1 | Cutting Stock Optimization | **LENGTH PACKING** |
| F2 | Material Recovery Maximization | **MATCH IMPROVEMENT** |

---

## 2. BUSINESS OBJECTIVE

### 2.1 Problem Statement

Phase-3.1 recovers material in the **width direction** only (expansion strips from reduction waste). Two significant waste sources remain:

**Length Waste:** Each panel consumes one full 6000mm stock length. Panels shorter than 6000mm waste the remainder. With sample data, four marks at 1250-1450mm length each consume a full 6000mm stock — 75-79% of each stock length is wasted.

**Matching Gaps:** Phase-3.1 matching is single-pass, single-candidate. Demands that cannot be fully satisfied by one stock piece go partially or fully unmatched, even when sufficient inventory exists across multiple pieces.

### 2.2 Objective

Reduce raw material waste by:

1. **Packing multiple panels into one stock length** where MCK-compatible panels share the same stock.
2. **Maximizing width-direction recovery** by iterating matches until no further recovery is possible.

### 2.3 Success Criteria

| Metric | Phase-3.1 Baseline | Phase-3.2 Target |
|--------|-------------------|-----------------|
| Recovery Rate | 100% (sample data) | >= 100% (maintain) |
| Stock Length Utilization | Not measured | > 0% (new metric) |
| Unmatched demands due to qty mismatch | Possible | Zero (if inventory exists) |
| Frozen Yield | 92.89% | 92.89% (unchanged) |

### 2.4 Non-Goals

- Phase-3.2 does NOT modify frozen yield calculation.
- Phase-3.2 does NOT introduce a new "effective yield after recovery" metric that blends with frozen yield.
- Phase-3.2 does NOT implement cross-project recovery.
- Phase-3.2 does NOT modify the width-direction MCK matching rules (C1-C5, R1-R4).

---

## 3. DESIGN BASIS

### 3.1 Feature F1: Length Packing

#### 3.1.1 Stock Length Model (Q1 — RESOLVED)

**Decision: Single stock length (6000mm), extensible design.**

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| A. Single stock length | Simple, matches current STOCK_LENGTH constant, deterministic, no inventory input needed | Cannot model factory floor remnants from prior jobs | **SELECTED** |
| B. Multiple stock lengths | Models real factory inventory, maximizes utilization of partial stock | Requires stock inventory input, complex bin selection, approaches Cross-Project scope | DEFERRED |

**Rationale:**

Steel grating stock arrives from the mill in uniform 6000mm lengths. This is the standard purchasing unit. The `STOCK_LENGTH = 6000.0` constant in `rule_engine.py` already encodes this fact.

Multiple stock lengths arise only from two sources:
1. **Remnants from prior jobs** — this is Cross-Project Recovery (Feature 5, deferred).
2. **Non-standard mill orders** — rare in steel grating; mills supply 6m bars.

For Phase-3.2, a single stock length eliminates input complexity and produces a clean optimization: "How many 6000mm stock lengths do we actually need?"

**Extensibility:** The `CutPlan.stock_length` field is parameterized (not hardcoded as 6000). When multiple stock lengths are implemented in a future phase, the algorithm changes from "open a new 6000mm bin" to "select the best bin size from available inventory." No structural change to data models.

#### 3.1.2 Primary Optimization Objective (Q2 — RESOLVED)

**Decision: Minimize stock lengths consumed.**

| Objective | Rationale | Decision |
|-----------|-----------|----------|
| Minimize stock lengths consumed | Directly reduces purchase orders. For uniform bins, this also minimizes waste area and cost. Easiest to explain to factory floor. | **SELECTED** |
| Minimize waste area | Equivalent to above for uniform bins. Only differs when bins have different sizes — not applicable in Phase-3.2. | EQUIVALENT (for uniform bins) |
| Minimize raw material cost | Equivalent to above when all stock lengths cost the same — which they do for uniform 6m bars. Would matter only with variable pricing. | EQUIVALENT (for uniform pricing) |

**Rationale:**

For uniform stock lengths at uniform price:

```
Minimize stock lengths consumed
  = Minimize total stock length purchased
  = Minimize total waste area
  = Minimize raw material cost
```

All three objectives are mathematically equivalent. We choose "minimize stock lengths consumed" because:

1. **Factory language** — Production managers think in "how many bars do we order?" not "minimize the integral of waste area."
2. **Measurable** — The KPI is an integer count: 70 stock lengths → 15 stock lengths. Clear, auditable.
3. **FFD-aligned** — First Fit Decreasing directly minimizes bin count, which IS stock length count.

If future phases introduce variable-length stock or variable pricing, the objective can be refined without changing the algorithm — only the bin selection heuristic changes.

#### 3.1.3 Packing Granularity (Q4 — RESOLVED)

**Decision: Individual quantity units.**

Packing operates on **individual quantity units**, not panel demands.

| Option | Description | Decision |
|--------|-------------|----------|
| Panel demand | G02 (qty=25) treated as one block — all 25 must go in the same bin | REJECTED |
| Individual quantity units | G02 (qty=25) expanded to 25 individual items, each 1250mm, packed independently | **SELECTED** |

**Rationale:**

Panel demand packing is physically impossible — 25 panels of 1250mm = 31,250mm total. No single 6000mm bin can hold them. Even if we interpret "demand packing" as "all pieces of one mark in consecutive bins," it prevents mixing marks, which is the primary source of packing savings.

**Example — Individual unit packing:**

```
Input:
  G02: 995mm × 1250mm, qty=25 (NORMAL)
  G03: 965mm × 1250mm, qty=25 (REDUCTION)
  G04: 605mm × 1450mm, qty=10 (REDUCTION)

All share standard_width=995mm and MCK=(30.0, 25.0, 5.0).

Expand to individual units:
  25 items of 1250mm (G02)
  25 items of 1250mm (G03)
  10 items of 1450mm (G04)
  = 60 individual items

Sort by length descending:
  10 × 1450mm (G04), then 50 × 1250mm (G02+G03)

FFD Packing (N cuts = N × 6mm kerf per bin, sorted by length descending):
  BIN-001: G04(1450) + G04(1450) + G04(1450) + G04(1450) + 4 cuts = 5800 + 24 = 5824mm → remnant 176mm
  BIN-002: G04(1450) + G04(1450) + G04(1450) + G04(1450) + 4 cuts = 5800 + 24 = 5824mm → remnant 176mm
  BIN-003: G04(1450) + G04(1450) + G02(1250) + G03(1250) + 4 cuts = 5400 + 24 = 5424mm → remnant 576mm
  BIN-004..015: 4 × 1250mm + 4 cuts = 5000 + 24 = 5024mm → remnant 976mm each
  ...

Result: ~15 bins instead of 60 stock lengths
```

**Panel identity preserved:** Each `CutPlanEntry` records which mark and product_code the item belongs to. The factory cut sheet shows exactly which panel goes where in each stock length. Qty is tracked per-mark across bins.

**Kerf between identical marks:** Even two pieces of the same mark (e.g., G02 + G02) require a kerf between them — they are separate physical panels cut from one stock bar.

#### 3.1.4 Grouping Rules

Panels can share a stock length only if:

| Rule | Constraint | Rationale |
|------|-----------|-----------|
| G1 | Same standard width | Must be cut from the same stock width |
| G2 | Same MCK | Must be weld-compatible (pitch, depth, thickness) |
| G3 | Not an expansion panel | Expansion panels use standard_width + expansion_width — different stock width |

**G3 Simplification:** Expansion panels are excluded from packing because they consume a wider stock piece (standard_width + expansion_width). Normal panels and reduction panels both use standard_width stock, so they can share a bin.

**G3 and reduction panels:** A reduction panel uses standard_width stock but produces a narrower fabricated panel. The reduction strip becomes scrap inventory (handled by Phase-3.1). For packing purposes, the stock consumption is standard_width — same as normal panels.

#### 3.1.5 Kerf Model (Q5 — RESOLVED)

**Decision: N cuts for N panels. Each cut consumes SAW_KERF (6mm) of material.**

**Physical process:**

A 6000mm stock bar is fed into the saw. Each panel is cut from the bar sequentially:

```
CUT 1: Saw at position panel_1_length → panel 1 separated, kerf destroyed
CUT 2: Saw at position panel_1 + kerf_1 + panel_2_length → panel 2 separated
...
CUT N: Saw at position (sum of all panels + all kerfs) → panel N separated from remnant
```

Each cut destroys exactly SAW_KERF (6mm) of material — the width of the saw blade.

**Formal definition:**

```
Length Used = Panel Length Sum + Cut Count × SAW_KERF

where:
  Panel Length Sum = Σ fabricated_length_i     (for i = 1..N)
  Cut Count       = N                          (one cut per panel)
  SAW_KERF        = 6mm                        (constant from rule_engine.py)

Remnant Length = STOCK_LENGTH - Length Used
              = 6000 - Σ fabricated_length_i - N × 6
```

**Why N cuts, not N-1:**

Each panel must be physically separated from the bar by a saw cut. The first panel needs a cut on its right edge to separate it from the rest of the bar. The last panel needs a cut on its right edge to separate it from the remnant (even if the remnant is waste — the panel must be freed). Therefore N panels = N cuts = N × SAW_KERF material consumed.

**Example — 4 panels in one bin:**

```
Stock bar: |======================== 6000mm ========================|

Panel 1 (G04, 1450mm):
  Position:  0mm
  Cut at:    1450mm → destroys 1450..1456mm (kerf 1)

Panel 2 (G02, 1250mm):
  Position:  1456mm
  Cut at:    2706mm → destroys 2706..2712mm (kerf 2)

Panel 3 (G03, 1250mm):
  Position:  2712mm
  Cut at:    3962mm → destroys 3962..3968mm (kerf 3)

Panel 4 (G02, 1250mm):
  Position:  3968mm
  Cut at:    5218mm → destroys 5218..5224mm (kerf 4)

Length Used = (1450 + 1250 + 1250 + 1250) + (4 × 6)
           = 5200 + 24
           = 5224mm

Remnant = 6000 - 5224 = 776mm
```

**Example — 1 panel in one bin (G01 solo):**

```
Panel 1 (G01, 1450mm):
  Position:  0mm
  Cut at:    1450mm → destroys 1450..1456mm (kerf 1)

Length Used = 1450 + (1 × 6) = 1456mm
Remnant = 6000 - 1456 = 4544mm
```

**Position formula:**

```
position_start_1 = 0
position_start_i = position_start_(i-1) + fabricated_length_(i-1) + SAW_KERF    (for i > 1)
```

#### 3.1.6 Packing Algorithm

**First Fit Decreasing (FFD):**

```
1. Collect all packing-eligible panels (pass G1-G3).
2. Expand qty into individual units.
3. Sort by fabricated_length descending.
4. For each individual unit:
   a. Scan existing bins in order.
   b. Find first bin where remaining_capacity >= fabricated_length + SAW_KERF.
   c. If found: assign unit to that bin, deduct (fabricated_length + SAW_KERF) from remaining_capacity.
   d. If no bin fits: open a new bin.
      - remaining_capacity initialized to STOCK_LENGTH - fabricated_length - SAW_KERF.
5. Record the cut plan for each bin.
```

**Remaining capacity formula:**

```
remaining_capacity = STOCK_LENGTH - Length Used
                   = STOCK_LENGTH - Σ fabricated_length_i - N × SAW_KERF
```

#### 3.1.7 Length Remnant Strategy (Q3 — RESOLVED, UPDATED Rev 0.3)

**Decision: Three-tier classification with configurable, independent thresholds.**

After packing, each bin has a remnant length. This remnant is classified into one of three tiers:

| Tier | Condition | Classification | Action |
|------|-----------|---------------|--------|
| 1 | remnant_length = 0 | **EXACT_FIT** | No waste. Perfect packing for this bin. |
| 2 | remnant_length > 0 AND remnant meets reusable thresholds | **REUSABLE_REMNANT** | Tracked in packing report. Available for future recovery. |
| 3 | remnant_length > 0 AND remnant below thresholds | **LENGTH_WASTE** | Tracked in packing report. Classified as dead scrap. |

**Length remnant thresholds (independent from width recovery):**

Length packing remnants use their own configurable constants, defined in `packing_models.py`. These are NOT shared with the width-direction thresholds in `rule_engine.py`.

```
# packing_models.py — Length Remnant Thresholds
PACKING_REUSABLE_MIN_LENGTH: float = 200.0    # mm — minimum remnant length
PACKING_REUSABLE_MIN_AREA: float   = 0.20     # m² — minimum remnant area

# rule_engine.py — Width Recovery Thresholds (SEPARATE, NOT REUSED)
# REUSABLE_MIN_WIDTH  = 200.0   ← width-direction only
# REUSABLE_MIN_AREA   = 0.2     ← width-direction only
```

**Why separate thresholds:**

Width recovery and length packing operate on different physical dimensions with different manufacturing constraints. A width strip of 200mm has different reusability characteristics than a length remnant of 200mm. Sharing thresholds couples two independent systems — changing one threshold for width recovery would unintentionally affect length packing classification, and vice versa.

**Classification logic:**

```
REUSABLE_REMNANT if ALL of:
  remnant_length >= PACKING_REUSABLE_MIN_LENGTH (default 200mm)
  remnant_area   >= PACKING_REUSABLE_MIN_AREA   (default 0.20 m²)

where remnant_area = remnant_length × stock_width / 1,000,000
```

Since stock_width is always >= 995mm in current data, the binding constraint is `remnant_length >= 201mm` (200mm × 995mm = 0.199 m² < 0.20 m²). However, both thresholds are always evaluated — no shortcut assumptions.

**Configurability:** Default values match the current width-direction defaults for consistency, but they can be tuned independently. For example, if the factory determines that length remnants shorter than 500mm are not worth storing, only `PACKING_REUSABLE_MIN_LENGTH` changes — width recovery thresholds remain untouched.

**Remnant tracking model:**

```
LengthRemnant
  remnant_id: str              # REM-{bin_id}
  bin_id: str                  # parent bin
  stock_width: float           # mm
  remnant_length: float        # mm
  remnant_area_m2: float       # m²
  classification: str          # REUSABLE_REMNANT | LENGTH_WASTE
  mck: tuple[float,float,float]
```

**Future recovery roadmap:**

| Phase | Remnant Handling |
|-------|----------------|
| Phase-3.2 (current) | Classify and report. Remnants are informational only — not fed back into matching or packing. |
| Phase-3.3 (future) | Reusable remnants become available stock in a length-direction inventory. Short panels from future projects can be matched against existing remnants (similar to Phase-3.1 width matching). |
| Phase-4 (future) | Cross-project remnant pool. Remnants from Project A available to Project B. Requires persistence layer. |

**Why not feed back now:** Feeding remnants back into the current project's packing creates a circular dependency (pack → remnant → re-pack). For a single project, all panels are already packed in one pass. Remnant reuse only makes sense across projects or across production batches.

---

### 3.2 Feature F2: Match Improvement

#### 3.2.1 Current Limitations (Phase-3.1)

| Limitation | Impact | Fix |
|-----------|--------|-----|
| L1: Partial qty match — demand qty=10, stock qty=5, only 5 matched | 5 panels go unmatched even if another stock piece exists | **Continue searching** after partial match |
| L2: Single-pass — after a match reduces a stock piece, no re-scan for smaller demands | Trim remainder is REUSABLE but never considered for other demands | **Multi-pass matching** until no more matches possible |
| L3: No cascading — Match 1 trim could feed Match 2 | Recovery rate is suboptimal when multiple demands and stock pieces interact | Solved by L2 (multi-pass inherently cascades) |

#### 3.2.2 Multi-Pass Matching Algorithm

```
REPEAT:
  1. Collect all unmatched expansion demands (sorted largest-first)
  2. Collect all AVAILABLE stock pieces
  3. For each demand:
     a. Find candidates (existing C1-C5, R1-R4 logic — unchanged)
     b. If found: consume, record match
     c. If partially fulfilled (qty mismatch): record partial match, reduce demand qty
  4. If no matches were made in this pass → STOP
UNTIL no more matches possible
```

**Convergence guarantee:** Each pass either reduces total unmatched demand or reduces total available stock. Since both are finite and non-negative, the loop terminates.

**Maximum passes:** In practice, limited by the number of stock pieces × demands. For typical projects (10-50 marks), convergence within 3-5 passes.

#### 3.2.3 Partial Qty Handling

Phase-3.1 (current):

```python
pieces_to_use = min(best.qty, demand_qty)
# If pieces_to_use < demand_qty, remainder goes unmatched
```

Phase-3.2 (proposed):

```python
remaining_demand_qty = demand_qty
while remaining_demand_qty > 0:
    candidates = find_candidates(...)
    if not candidates:
        break
    best = candidates[0]
    pieces_to_use = min(best.qty, remaining_demand_qty)
    consume(best, pieces_to_use)
    remaining_demand_qty -= pieces_to_use
# Only truly unmatched qty goes to unmatched list
```

#### 3.2.4 Impact on Existing KPIs

| KPI | Change |
|-----|--------|
| Recovery Rate | May increase (more demands matched) |
| Stock Utilization Rate | May increase (more inventory consumed) |
| Material Recovery Score | May increase (more recovery from reductions) |
| Dead Scrap Area | May increase (more post-consumption reclassifications) |
| Remaining Stock Area | May decrease (more consumption) |
| Frozen Yield | **UNCHANGED** |

---

## 4. DATA MODEL

### 4.1 New Data Classes

```
CutPlan
  bin_id: str                    # BIN-{seq}
  stock_width: float             # mm — standard width of the stock
  stock_length: float            # mm — parameterized (6000 for Phase-3.2)
  mck: tuple[float, float, float]
  panels: list[CutPlanEntry]     # ordered list of panels in this bin
  total_used: float              # mm — sum of panel lengths + kerfs
  remnant_length: float          # mm — stock_length - total_used
  remnant_classification: str    # EXACT_FIT | REUSABLE_REMNANT | LENGTH_WASTE
  remnant_area_m2: float         # remnant_length × stock_width / 1e6

CutPlanEntry
  mark: str
  product_code: str
  fabricated_length: float       # mm
  position_start: float          # mm — start position in the bin
  kerf_after: float              # mm — SAW_KERF (6mm) for every panel (cut that separates it)

LengthRemnant
  remnant_id: str                # REM-{bin_id}
  bin_id: str
  stock_width: float             # mm
  remnant_length: float          # mm
  remnant_area_m2: float         # m²
  classification: str            # REUSABLE_REMNANT | LENGTH_WASTE
  mck: tuple[float, float, float]
```

### 4.2 Extended Data Classes

```
PackingSummary
  total_bins: int
  total_items_packed: int        # individual quantity units
  total_marks_packed: int        # unique marks
  stock_lengths_before: int      # one per item (baseline)
  stock_lengths_after: int       # bins used
  stock_savings: int             # before - after
  stock_savings_percent: float   # savings / before × 100
  stock_utilization_rate: float  # %
  total_length_waste_m2: float
  total_reusable_remnant_m2: float
  total_exact_fit_bins: int
  cut_plans: list[CutPlan]
  length_remnants: list[LengthRemnant]

RecoverySummary (extended)
  # Existing Phase-3.1 fields unchanged
  packing_summary: PackingSummary | None  # None if packing not run
```

### 4.3 No Changes to Frozen Models

| Model | Change |
|-------|--------|
| `ProductMaster` | NONE |
| `FabricatedPanel` | NONE |
| `ProjectSummary` | NONE |
| `Pattern` | NONE |
| `ScrapPiece` | NONE |

---

## 5. OPTIMIZATION STRATEGY

### 5.1 Processing Pipeline

```
process_panels_with_recovery(panels, depth_map)
│
├── Phase-1: process_panels()               ← FROZEN
├── Phase-2: optimize_project()             ← FROZEN
├── Phase-3.1: Width Recovery               ← v1.1.0-RC1
│   ├── build_inventory()
│   ├── match_expansions()                  ← IMPROVED (multi-pass, F2)
│   ├── validate_recovery()
│   └── generate_recovery_report()
│
└── Phase-3.2: Length Packing               ← NEW (F1)
    ├── group_panels_for_packing()
    ├── run_length_packing()                ← FFD algorithm
    ├── classify_remnants()
    ├── calculate_packing_kpis()
    ├── validate_packing()
    └── generate_packing_report()
```

### 5.2 Execution Order

Length packing runs AFTER width recovery because:
1. Width recovery may change which panels need expansion (matched demands consume stock).
2. Packing groups depend on panel classification (normal/expansion/reduction), which is finalized after width recovery.
3. Packing metrics (stock savings) are independent from width recovery metrics.

### 5.3 Algorithm Complexity

| Algorithm | Complexity | Practical Impact |
|-----------|-----------|-----------------|
| FFD (sort + greedy fit) | O(n log n + n × b) | n=items, b=bins. For 100 items → <1ms |
| Multi-pass matching | O(p × d × s) | p=passes, d=demands, s=stock pieces. For 5×10×10 → <1ms |
| Total Phase-3.2 | O(n log n) | Negligible compared to Phase-2 scenario generation |

FFD is a 11/9 OPT + 6/9 approximation — within 22% of optimal for uniform bin sizes. Exact solutions (branch-and-bound) are unnecessary for this domain where stock lengths are uniform and panels are few.

### 5.4 Algorithm Baseline Reference

**FFD (First Fit Decreasing) is the baseline reference algorithm for Phase-3.2 validation and regression.**

All validation rules (R22-R28), regression tests, and KPI calculations are defined against FFD output. FFD results serve as the ground truth for correctness verification.

Future phases may introduce alternative packing algorithms:

| Algorithm | Type | When to Consider |
|-----------|------|-----------------|
| Best Fit Decreasing (BFD) | Heuristic | When FFD leaves excessive remnant variance across bins |
| Branch & Bound | Exact | When panel count is small (<20) and optimal solution is required |
| Genetic Algorithm | Metaheuristic | When problem constraints become non-linear (e.g., multiple stock widths + lengths) |

**Invariants when adding future algorithms:**

1. FFD remains available as a selectable algorithm — it is never removed.
2. All algorithms must satisfy the same validation rules (R22-R28).
3. Regression tests compare new algorithm output against FFD baseline — any deviation must produce equal or better stock_lengths_after (fewer bins = better).
4. The algorithm identifier is recorded in PackingSummary for traceability.

---

## 6. VALIDATION RULES

### 6.1 Existing Rules (unchanged)

R10-R21 from Phase-3.1 remain unchanged. They validate width-direction recovery.

### 6.2 New Packing Rules

| Rule | Description | Check |
|------|-------------|-------|
| R22 | No Bin Overflow | Every bin: total_used <= stock_length |
| R23 | Kerf Accounted | Every bin: cut count = panels_in_bin; total kerf = panels_in_bin × SAW_KERF (6mm) |
| R24 | Panel Coverage | Every packing-eligible item appears in exactly one bin |
| R25 | Remnant Classification Consistent | Remnant dimensions match PACKING_REUSABLE_MIN_LENGTH and PACKING_REUSABLE_MIN_AREA thresholds |
| R26 | Stock Savings Non-Negative | stock_lengths_after <= stock_lengths_before |
| R27 | Packing Utilization Bounded | 0% <= utilization <= 100% |
| R28 | Frozen KPI Unchanged (Packing) | Packing does not alter yield, scrap, or any Phase-1/2 KPI |
| R29 | Packing Conservation | Every bin: packed_length + remnant_length + kerf_loss = stock_length. Where packed_length = Σ panel lengths, kerf_loss = N × SAW_KERF |

### 6.3 Match Improvement Rules (Phase-3.2B)

| Rule | Description | Check |
|------|-------------|-------|
| R30 | Multi-Pass Convergence | Matching loop terminated (did not run forever) |
| R31 | No Duplicate Match | Each (demand_mark, stock_piece_id, pass_number) tuple is unique |
| R32 | Partial Qty Balanced | Sum of matched qty per demand <= original demand qty |

---

## 7. EXPLAINABILITY REQUIREMENTS

### 7.1 Length Packing

Each bin generates an explainability entry:

```
BIN ALLOCATION: BIN-001
  Stock: 6000mm × 995mm (MCK: 30.0, 25.0, 5.0)
  Position 0mm:    G04 (1450mm)  [cut at 1450mm, kerf 6mm]
  Position 1456mm: G04 (1450mm)  [cut at 2906mm, kerf 6mm]
  Position 2912mm: G04 (1450mm)  [cut at 4362mm, kerf 6mm]
  Position 4368mm: G04 (1450mm)  [cut at 5818mm, kerf 6mm]
  Panel Sum: 5800mm | Cuts: 4 × 6mm = 24mm | Length Used: 5824mm
  Remnant: 176mm → LENGTH_WASTE (0.175 m²)
```

### 7.2 Multi-Pass Matching

Each pass generates an explainability entry:

```
MATCH PASS 2:
  Demand: G01 (remaining qty=5, expansion=120mm)
  Stock: SP-G04-001 (remaining_width=270mm, qty=10)
  Result: MATCHED (5 pieces)
  Post Consumption: 270 - 120 = 150mm → DEAD_SCRAP
  Reason: Second pass — first pass matched 5/10, this pass matches remaining 5/10
```

---

## 8. TECHNICAL RISKS

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| T1 | FFD may produce suboptimal packing for highly variable panel lengths | LOW | FFD is within 22% of optimal; exact solutions add complexity for marginal gain. Monitor actual vs theoretical savings. |
| T2 | Multi-pass matching may produce different results from Phase-3.1 single-pass | MEDIUM | Phase-3.1 results are a SUBSET of multi-pass results. All Phase-3.1 matches remain valid; multi-pass only ADDS matches. Validate with regression test. |
| T3 | Expansion panels excluded from packing reduces savings potential | LOW | Expansion panels are few (10/70 in sample data = 14%). Normal+reduction panels are the primary packing opportunity. |
| T4 | Kerf accumulation reduces packing efficiency for many small panels | LOW | Kerf is 6mm vs panels of 1250-1450mm. Even 4 panels in one bin: 4×6=24mm kerf out of 6000mm (0.4%). |
| T5 | Packing group rules (G1-G3) may be too restrictive | MEDIUM | Monitor percentage of panels eligible for packing. If <50%, consider relaxing G3 in Phase-3.3. |
| T6 | Interaction between width recovery and length packing | LOW | Sequential execution (width first, then length). No circular dependency. Packing reads panel data, does not modify it. |
| T7 | RecoverySummary extension may break existing UI | LOW | `packing_summary` is Optional (None when not run). Existing UI code checks for presence before rendering. |
| T8 | Individual unit expansion creates large item lists for high-qty marks | LOW | 70 panels in sample data → 60 packing items. Even 500-panel projects produce manageable lists. FFD is O(n log n). |

---

## 9. INTEGRATION STRATEGY

### 9.1 New Modules

| Module | Purpose | Dependencies |
|--------|---------|-------------|
| `packing_models.py` | CutPlan, CutPlanEntry, LengthRemnant, PackingSummary | dataclasses only |
| `packing_engine.py` | group_panels_for_packing(), run_length_packing() | models, packing_models, product_master (RO) |
| `packing_validation.py` | R22-R31 validation | models, packing_models, recovery_models |
| `packing_report.py` | Structured report for packing results | models, packing_models |

### 9.2 Modified Modules

| Module | Change | Impact |
|--------|--------|--------|
| `recovery_engine.py` | Replace single-pass with multi-pass matching | Match results may increase. All Phase-3.1 validation rules still apply. |
| `recovery_models.py` | Add `packing_summary` field to RecoverySummary | Optional field, default None. No breaking change. |
| `processor.py` | Extend `process_panels_with_recovery()` to call packing engine | Additive call after recovery engine. Return dict gains `packing_summary` key. |
| `app.py` | Add Sections 16-18 for packing display | Additive sections after Section 15. |

### 9.3 Unmodified Modules

| Module | Status |
|--------|--------|
| `models.py` | FROZEN |
| `product_master.py` | FROZEN |
| `rule_engine.py` | FROZEN |
| `pattern_engine.py` | FROZEN |
| `project_optimizer.py` | FROZEN |
| `optimizer_models.py` | FROZEN |
| `scrap_inventory.py` | UNCHANGED |
| `recovery_validation.py` | UNCHANGED (R10-R21 stay as-is) |
| `recovery_report.py` | UNCHANGED |

### 9.4 UI Additions

| Section | Title | Content |
|---------|-------|---------|
| 16 | Length Packing Summary | Stock savings, utilization rate, bins used |
| 17 | Cut Plans | Per-bin detail with panel positions |
| 18 | Packing Validation | R22-R31 results |

### 9.5 Implementation Order

```
Step 1: packing_models.py          — Data classes
Step 2: packing_engine.py          — FFD algorithm + grouping
Step 3: packing_validation.py      — R22-R31
Step 4: packing_report.py          — Report generation
Step 5: recovery_engine.py         — Multi-pass matching improvement
Step 6: recovery_models.py         — Add packing_summary field
Step 7: processor.py               — Integrate packing into pipeline
Step 8: app.py                     — Sections 16-18
Step 9: Regression test             — All R10-R31 PASS, frozen KPIs unchanged
```

Each step follows the same review gate pattern as Phase-3.1: explain → approve → implement → test → review.

---

## 10. SAMPLE DATA WALKTHROUGH

### 10.1 Current State (Phase-3.1)

```
G01: TA325/1, 1115mm × 1450mm, qty=10  → EXPANSION (120mm)
G02: TA325/1,  995mm × 1250mm, qty=25  → NORMAL
G03: TA325/1,  965mm × 1250mm, qty=25  → REDUCTION (30mm → DEAD_SCRAP)
G04: TA325/1,  605mm × 1450mm, qty=10  → REDUCTION (390mm → STOCK_PIECE)

Width Recovery: G01 matched to G04 stock → Recovery Rate 100%
Stock lengths consumed: 70 panels × 1 stock each = 70 stock lengths
```

### 10.2 Phase-3.2 Length Packing (Exact Walkthrough)

**Step 1 — Grouping:**

| Mark | Eligible? | Rule | Reason |
|------|-----------|------|--------|
| G01 | NO | G3 | Expansion panel |
| G02 | YES | G1+G2+G3 | Normal, std_width=995, MCK=(30.0, 25.0, 5.0) |
| G03 | YES | G1+G2+G3 | Reduction, std_width=995, MCK=(30.0, 25.0, 5.0) |
| G04 | YES | G1+G2+G3 | Reduction, std_width=995, MCK=(30.0, 25.0, 5.0) |

Packing group: {G02, G03, G04} — 60 items total.
Non-packable: {G01} — 10 items, each gets own stock length.

**Step 2 — Expand to individual units:**

```
10 × G04 @ 1450mm
25 × G02 @ 1250mm
25 × G03 @ 1250mm
= 60 items
```

**Step 3 — Sort descending by length:**

```
Items 1-10:  G04 (1450mm)
Items 11-60: G02/G03 (1250mm) — interleaved by mark
```

**Step 4 — FFD Packing:**

Each bin capacity = 6000mm.

```
Bin pattern X (4 × G04, 4 panels):
  Panels: 1450 + 1450 + 1450 + 1450 = 5800mm
  Cuts:   4 × 6 = 24mm
  Length Used: 5824mm
  Remnant: 6000 - 5824 = 176mm → LENGTH_WASTE (0.175 m²)

Bin pattern Y (2 × G04 + 2 × 1250, 4 panels):
  Panels: 1450 + 1450 + 1250 + 1250 = 5400mm
  Cuts:   4 × 6 = 24mm
  Length Used: 5424mm
  Remnant: 6000 - 5424 = 576mm → REUSABLE_REMNANT (0.573 m²)

Bin pattern Z (4 × 1250mm, 4 panels):
  Panels: 1250 + 1250 + 1250 + 1250 = 5000mm
  Cuts:   4 × 6 = 24mm
  Length Used: 5024mm
  Remnant: 6000 - 5024 = 976mm → REUSABLE_REMNANT (0.971 m²)
```

**FFD Allocation (greedy, sorted by length descending):**

FFD places the 10 longest items (G04 at 1450mm) first, packing 4 per bin. Then remaining G04 items mix with 1250mm items. Finally, 1250mm items fill the rest.

```
Bins 1-2:   Pattern X (4 × G04)                  → 2 bins, 8 items
Bin  3:     Pattern Y (2 × G04 + 2 × G02/G03)    → 1 bin, 4 items
Bins 4-15:  Pattern Z (4 × G02/G03)              → 12 bins, 48 items
Total: 15 bins, 60 items
```

**Step 5 — Results:**

| Metric | Before Packing | After Packing | Savings |
|--------|---------------|---------------|---------|
| Stock lengths (packable) | 60 | 15 | 45 (75.0%) |
| Stock lengths (non-packable, G01) | 10 | 10 | 0 |
| **Total stock lengths** | **70** | **25** | **45 (64.3%)** |
| Total waste length | 70 × remnant | 15 × remnant | — |
| Utilization rate | ~22% | ~86% | — |

**Step 6 — Remnant classification:**

| Bin Type | Count | Remnant | Area (m²) | Classification |
|----------|-------|---------|-----------|---------------|
| Pattern X (4×G04) | 2 | 176mm | 0.175 | LENGTH_WASTE |
| Pattern Y (2×G04+2×1250) | 1 | 576mm | 0.573 | REUSABLE_REMNANT |
| Pattern Z (4×1250) | 12 | 976mm | 0.971 | REUSABLE_REMNANT |
| G01 solo | 10 | 4544mm | 4.521 | REUSABLE_REMNANT |

23 of 25 bins produce reusable remnants. 2 bins produce length waste.
Total reusable remnant area = 1×0.573 + 12×0.971 + 10×4.521 = **57.43 m²**.
Total length waste area = 2×0.175 = **0.35 m²**.

### 10.3 Phase-3.2 Match Improvement

With sample data, Phase-3.1 already achieves 100% recovery rate (1 expansion demand, 1 stock piece, exact qty match). Multi-pass matching produces no change for this dataset.

Multi-pass improvement is most visible with datasets containing:
- Multiple expansion demands of different widths
- Multiple stock pieces of different remaining widths
- Qty mismatches between demands and stock

---

## 11. DEPENDENCIES AND PREREQUISITES

| Prerequisite | Status | Action |
|-------------|--------|--------|
| Phase-3.1 complete | DONE | v1.1.0-RC1 |
| Width recovery validated | DONE | R10-R21 all PASS |
| depth_map.json populated | PARTIAL | Only TA325/1. Must add all products before production use. |
| STOCK_LENGTH constant | EXISTS | 6000mm in rule_engine.py |
| SAW_KERF constant | EXISTS | 6mm in rule_engine.py |
| Width recovery thresholds | EXISTS | In rule_engine.py (NOT reused by packing) |
| Length packing thresholds | NEW | PACKING_REUSABLE_MIN_LENGTH=200, PACKING_REUSABLE_MIN_AREA=0.20 in packing_models.py |

---

## 12. DELIVERABLES

| # | Deliverable | Format |
|---|------------|--------|
| 1 | packing_models.py | Python module |
| 2 | packing_engine.py | Python module |
| 3 | packing_validation.py | Python module |
| 4 | packing_report.py | Python module |
| 5 | recovery_engine.py (multi-pass) | Modified Python module |
| 6 | recovery_models.py (packing_summary field) | Modified Python module |
| 7 | processor.py (packing integration) | Modified Python module |
| 8 | app.py (Sections 16-18) | Modified Python module |
| 9 | PHASE3_2_REGRESSION_TEST_REPORT.md | Test report |

---

## 13. RESOLVED DESIGN QUESTIONS

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| Q1 | Single or multiple stock lengths? | **Single (6000mm), extensible** | Matches mill standard. Multiple lengths is Cross-Project scope. CutPlan.stock_length is parameterized for future extension. |
| Q2 | Primary optimization objective? | **Minimize stock lengths consumed** | Equivalent to minimize waste and minimize cost for uniform bins. Factory-friendly language. FFD directly optimizes bin count. |
| Q3 | Length remnant strategy? | **3-tier classification, configurable independent thresholds** | EXACT_FIT / REUSABLE_REMNANT / LENGTH_WASTE. Thresholds in packing_models.py, NOT reused from width recovery. Configurable per dimension. |
| Q4 | Packing granularity? | **Individual quantity units** | Panel-demand packing is physically impossible for high qty. Individual units enable cross-mark mixing, which is the primary savings source. |
| Q5 | Kerf model? | **N cuts for N panels, Length Used = Σ panels + N × SAW_KERF** | Each panel requires one saw cut to separate from bar. Conservative, physically accurate. |

---

## APPENDIX A: DESIGN DECISIONS

| ID | Decision | Rationale | Alternatives Considered |
|----|----------|-----------|------------------------|
| D1 | Single stock length (6000mm) | Mill standard, simple, deterministic | Multiple lengths (deferred — Cross-Project scope) |
| D2 | Minimize stock lengths consumed | Equivalent objectives for uniform bins; factory-friendly | Minimize waste area, minimize cost |
| D3 | 3-tier remnant classification | Consistent with width-direction classification model | Binary (reusable/waste), no tracking |
| D4 | Individual unit packing | Enables cross-mark mixing for maximum savings | Panel demand packing (rejected — physically impossible for high qty) |
| D5 | FFD algorithm | O(n log n), proven 22% approximation bound, simple to implement | Branch-and-bound (too complex), Best Fit (marginal gain) |
| D6 | Expansion panels excluded from packing | Different stock width prevents sharing | Include with separate groups (adds complexity for 14% of panels) |
| D7 | Sequential execution (width first, then length) | No circular dependency; clean separation | Interleaved (complex, high risk) |
| D8 | Remnants not fed back into current project | Avoids circular dependency; reuse only meaningful across projects | Iterative repack (unnecessary for single project) |
| D9 | Multi-pass matching with inner qty loop | Maximizes recovery without changing selection rules | Single-pass (current, leaves gaps), configurable (complexity without benefit) |
| D10 | Kerf between all panels including same-mark | Each panel is a separate physical piece requiring a saw cut | Skip kerf for same-mark (incorrect — still needs cutting) |
| D11 | N cuts for N panels (not N-1) | Each panel must be freed from bar by a saw cut, including last panel from remnant | N-1 cuts (undercounts — last panel would remain attached to remnant) |
| D12 | Length remnant thresholds independent from width thresholds | Width and length are different physical dimensions with different reusability. Coupling them creates unintended side effects. | Share thresholds with rule_engine.py (rejected — changes to width thresholds would affect length classification) |

---

**END OF DOCUMENT**
