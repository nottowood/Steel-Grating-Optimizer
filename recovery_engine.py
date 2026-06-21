"""Phase-3 Recovery Engine — Expansion Matching.

Matches stock pieces to expansion demands using MCK compatibility,
then calculates Recovery KPIs. This is the core matching logic for
the Material Recovery Engine.

No UI integration — that belongs in recovery_report.py.
No processor integration — that belongs in processor.py.

Reference: DBD_PHASE3_REV0.3, Sections 7-9
"""

from models import FabricatedPanel, ProjectSummary
from product_master import ProductMaster
from recovery_models import (
    RecoveryMatch,
    RecoverySummary,
    ScrapInventory,
    StockPiece,
    classify_remainder,
)
from scrap_inventory import (
    build_inventory,
    consume_stock_piece,
    update_inventory_stats,
)


def run_recovery_engine(
    panels: list[FabricatedPanel],
    project_summary: ProjectSummary,
    catalog: dict[str, ProductMaster],
    depth_map: dict[str, float] | None = None,
) -> RecoverySummary:
    """Run the full Material Recovery Engine.

    1. Build scrap inventory from panel reductions
    2. Match stock pieces to expansion demands
    3. Calculate Recovery KPIs

    Args:
        panels: Processed panels from Phase-1/Phase-2 (read-only).
        project_summary: Frozen KPI summary (read-only).
        catalog: Product catalog (SSOT for pitch/thickness).
        depth_map: Product code -> load_bar_depth mapping.
    """
    inventory = build_inventory(panels, catalog, depth_map)

    matches, unmatched = _match_expansions(panels, inventory, catalog, depth_map)

    update_inventory_stats(inventory)

    summary = _calculate_recovery_kpis(
        panels, inventory, matches, unmatched, project_summary
    )
    return summary


def _match_expansions(
    panels: list[FabricatedPanel],
    inventory: ScrapInventory,
    catalog: dict[str, ProductMaster],
    depth_map: dict[str, float] | None,
) -> tuple[list[RecoveryMatch], list[dict]]:
    """Match stock pieces to expansion demands.

    Demands are sorted largest-first (DBD D4).
    Selection uses minimum trim waste priority (DBD Section 8).
    """
    if depth_map is None:
        depth_map = {}

    demands = _collect_demands(panels, catalog, depth_map)
    demands.sort(key=lambda d: -d["expansion_width"])

    matches: list[RecoveryMatch] = []
    unmatched: list[dict] = []

    for demand in demands:
        demand_mck = demand["mck"]
        expansion_width = demand["expansion_width"]
        demand_length = demand["fabricated_length"]
        demand_qty = demand["qty"]

        # R19: fail-closed — reject if depth is missing (0.0)
        if demand_mck[1] == 0.0:
            unmatched.append({
                "mark": demand["mark"],
                "product_code": demand["product_code"],
                "expansion_width": expansion_width,
                "fabricated_length": demand_length,
                "qty": demand_qty,
                "reason": "MCK incomplete — load_bar_depth is 0 (R19 fail-closed)",
            })
            continue

        candidates, rejection_log = _find_candidates(
            inventory.stock_pieces, demand_mck, expansion_width, demand_length
        )

        if not candidates:
            unmatched.append({
                "mark": demand["mark"],
                "product_code": demand["product_code"],
                "expansion_width": expansion_width,
                "fabricated_length": demand_length,
                "qty": demand_qty,
                "reason": "No compatible stock piece available",
            })
            continue

        best = candidates[0]
        pieces_to_use = min(best.qty, demand_qty)

        width_before = best.remaining_width
        post_class = consume_stock_piece(
            best, expansion_width, demand["mark"], pieces_to_use, inventory
        )
        width_after = best.remaining_width
        trim = round(width_before - expansion_width, 2)

        reason = _build_decision_reason(best, candidates, expansion_width)

        match = RecoveryMatch(
            demand_mark=demand["mark"],
            demand_product_code=demand["product_code"],
            expansion_width=expansion_width,
            demand_length=demand_length,
            demand_qty=pieces_to_use,
            stock_piece_id=best.piece_id,
            source_mark=best.source_mark,
            stock_original_width=best.original_width,
            stock_width_before=width_before,
            stock_width_after=width_after,
            trim_waste=trim,
            trim_classification=post_class,
            post_consumption_class=post_class,
            candidate_count=len(candidates),
            decision_reason=reason,
            mck=demand_mck,
            rejection_log=rejection_log,
        )
        matches.append(match)

    return matches, unmatched


def _collect_demands(
    panels: list[FabricatedPanel],
    catalog: dict[str, ProductMaster],
    depth_map: dict[str, float],
) -> list[dict]:
    """Collect expansion demands with MCK from panels."""
    demands = []
    for panel in panels:
        if not panel.needs_expansion:
            continue

        product = catalog.get(panel.product_code)
        pitch = product.load_bar_pitch if product else 0.0
        depth = depth_map.get(panel.product_code, 0.0)
        thickness = panel.load_bar_thickness

        demands.append({
            "mark": panel.mark,
            "product_code": panel.product_code,
            "expansion_width": panel.expansion_width,
            "fabricated_length": panel.fabricated_length,
            "qty": panel.qty,
            "mck": (pitch, depth, thickness),
        })
    return demands


def _find_candidates(
    stock_pieces: list[StockPiece],
    demand_mck: tuple[float, float, float],
    expansion_width: float,
    demand_length: float,
) -> tuple[list[StockPiece], list[tuple[str, str]]]:
    """Find and rank compatible stock pieces for a demand.

    Constraints (DBD Section 7):
        C1: MCK match (all 3 fields)
        C2: remaining_width >= expansion_width
        C3: length >= demand_length
        C4: status == AVAILABLE

    Selection priority (DBD Section 8):
        R1: minimum trim waste
        R2: exact length match
        R3: smallest remaining width
        R4: highest qty

    Returns:
        (sorted candidates, rejection log for non-matching pieces)
    """
    candidates: list[StockPiece] = []
    rejection_log: list[tuple[str, str]] = []

    for sp in stock_pieces:
        if sp.status != "AVAILABLE":
            rejection_log.append((sp.piece_id, f"Status {sp.status} (not AVAILABLE)"))
            continue

        if sp.mck != demand_mck:
            mismatches = []
            if sp.load_bar_pitch != demand_mck[0]:
                mismatches.append(f"pitch {sp.load_bar_pitch} != {demand_mck[0]}")
            if sp.load_bar_depth != demand_mck[1]:
                mismatches.append(f"depth {sp.load_bar_depth} != {demand_mck[1]}")
            if sp.load_bar_thickness != demand_mck[2]:
                mismatches.append(f"thickness {sp.load_bar_thickness} != {demand_mck[2]}")
            rejection_log.append((sp.piece_id, f"MCK mismatch: {'; '.join(mismatches)}"))
            continue

        if sp.load_bar_depth == 0.0:
            rejection_log.append((sp.piece_id, "MCK incomplete — depth is 0 (R19 fail-closed)"))
            continue

        if sp.remaining_width < expansion_width:
            rejection_log.append((
                sp.piece_id,
                f"Width insufficient: {sp.remaining_width}mm < {expansion_width}mm",
            ))
            continue

        if sp.length < demand_length:
            rejection_log.append((
                sp.piece_id,
                f"Length insufficient: {sp.length}mm < {demand_length}mm",
            ))
            continue

        candidates.append(sp)

    candidates.sort(key=lambda sp: (
        sp.remaining_width - expansion_width,
        0 if sp.length == demand_length else 1,
        sp.remaining_width,
        -sp.qty,
    ))

    return candidates, rejection_log


def _build_decision_reason(
    selected: StockPiece,
    all_candidates: list[StockPiece],
    expansion_width: float,
) -> str:
    """Build human-readable decision reason for match selection."""
    if len(all_candidates) == 1:
        return "Only compatible stock piece available"

    trim = selected.remaining_width - expansion_width
    if trim == 0:
        return f"Exact width match (selected from {len(all_candidates)} candidates)"

    return (
        f"Minimum trim waste {trim:.0f}mm "
        f"(selected from {len(all_candidates)} candidates)"
    )


def _calculate_recovery_kpis(
    panels: list[FabricatedPanel],
    inventory: ScrapInventory,
    matches: list[RecoveryMatch],
    unmatched: list[dict],
    project_summary: ProjectSummary,
) -> RecoverySummary:
    """Calculate all Recovery KPIs per DBD Section 9."""
    total_reduction_area = 0.0
    total_expansion_demand = 0.0

    for panel in panels:
        if panel.needs_reduction:
            total_reduction_area += (
                (panel.reduction_width / 1000)
                * (panel.fabricated_length / 1000)
                * panel.qty
            )
        if panel.needs_expansion:
            total_expansion_demand += (
                (panel.expansion_width / 1000)
                * (panel.fabricated_length / 1000)
                * panel.qty
            )

    total_reduction_area = round(total_reduction_area, 4)
    total_expansion_demand = round(total_expansion_demand, 4)

    recovered_area = round(
        sum(
            (m.expansion_width / 1000) * (m.demand_length / 1000) * m.demand_qty
            for m in matches
        ),
        4,
    )
    unrecovered_area = round(total_expansion_demand - recovered_area, 4)

    recovery_rate = (
        round((recovered_area / total_expansion_demand) * 100, 2)
        if total_expansion_demand > 0
        else 0.0
    )

    total_stock_area = inventory.total_stock_area_m2
    area_consumed = round(
        sum(
            (m.expansion_width / 1000) * (m.demand_length / 1000) * m.demand_qty
            for m in matches
        ),
        4,
    )
    stock_utilization_rate = (
        round((area_consumed / total_stock_area) * 100, 2)
        if total_stock_area > 0
        else 0.0
    )

    material_recovery_score = (
        round((recovered_area / total_reduction_area) * 100, 2)
        if total_reduction_area > 0
        else 0.0
    )

    return RecoverySummary(
        inventory=inventory,
        matches=matches,
        unmatched_demands=unmatched,
        total_reduction_area_m2=total_reduction_area,
        total_expansion_demand_m2=total_expansion_demand,
        recovered_area_m2=recovered_area,
        unrecovered_area_m2=unrecovered_area,
        recovery_rate=recovery_rate,
        stock_utilization_rate=stock_utilization_rate,
        dead_scrap_area_m2=inventory.total_dead_scrap_area_m2,
        remaining_stock_area_m2=inventory.remaining_stock_area_m2,
        material_recovery_score=material_recovery_score,
        frozen_yield=project_summary.yield_percent,
    )
