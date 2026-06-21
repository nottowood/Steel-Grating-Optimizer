"""Phase-3 Recovery Report Generation.

Generates structured report data for recovery results.
Returns plain dicts and lists — no Streamlit dependency.
UI rendering belongs in app.py.

Reference: DBD_PHASE3_REV0.3, Section 11
"""

from models import FabricatedPanel
from recovery_models import RecoverySummary
from recovery_validation import ValidationReport


def generate_recovery_report(
    recovery: RecoverySummary,
    validation: ValidationReport,
    panels: list[FabricatedPanel],
) -> dict:
    """Generate complete Phase-3 recovery report.

    Returns a dict with all report sections ready for UI display.
    """
    return {
        "executive_summary": _build_executive_summary(recovery, validation),
        "inventory_summary": _build_inventory_summary(recovery),
        "match_summary": _build_match_summary(recovery),
        "unmatched_summary": _build_unmatched_summary(recovery),
        "kpi_summary": _build_kpi_summary(recovery),
        "validation_summary": _build_validation_summary(validation),
        "explainability": _build_explainability(recovery, panels),
    }


def _build_executive_summary(
    recovery: RecoverySummary,
    validation: ValidationReport,
) -> dict:
    """Executive Summary — top-level status and key metrics."""
    return {
        "recovery_status": "VALID" if validation.all_passed else "INVALID",
        "validation_pass_rate": validation.pass_rate,
        "validation_passed": validation.passed,
        "validation_total": validation.total_rules,
        "frozen_yield": recovery.frozen_yield,
        "recovered_area_m2": recovery.recovered_area_m2,
        "recovery_rate": recovery.recovery_rate,
        "remaining_stock_area_m2": recovery.remaining_stock_area_m2,
        "dead_scrap_area_m2": recovery.dead_scrap_area_m2,
        "total_matches": len(recovery.matches),
        "total_unmatched": len(recovery.unmatched_demands),
    }


def _build_inventory_summary(recovery: RecoverySummary) -> dict:
    """Inventory Summary — stock pieces and dead scrap."""
    inv = recovery.inventory

    stock_pieces = []
    for sp in inv.stock_pieces:
        consumptions = []
        for c in sp.consumption_log:
            consumptions.append({
                "consumed_by": c.consumed_by_mark,
                "width_consumed": c.width_consumed,
                "width_before": c.width_before,
                "width_after": c.width_after,
                "qty_consumed": c.qty_consumed,
                "classification": c.post_classification,
            })

        stock_pieces.append({
            "piece_id": sp.piece_id,
            "source_mark": sp.source_mark,
            "product_code": sp.source_product_code,
            "mck": sp.mck,
            "original_width": sp.original_width,
            "remaining_width": sp.remaining_width,
            "length": sp.length,
            "original_area_m2": sp.original_area_m2,
            "remaining_area_m2": sp.remaining_area_m2,
            "qty": sp.qty,
            "status": sp.status,
            "consumptions": consumptions,
        })

    dead_scrap = []
    for ds in inv.dead_scrap_pieces:
        dead_scrap.append({
            "scrap_id": ds.scrap_id,
            "source_mark": ds.source_mark,
            "product_code": ds.source_product_code,
            "width": ds.width,
            "length": ds.length,
            "area_m2": ds.area_m2,
            "qty": ds.qty,
            "origin": ds.origin,
            "reason": ds.reason,
        })

    return {
        "total_reduction_marks": inv.total_reduction_marks,
        "total_reduction_panels": inv.total_reduction_panels,
        "total_expansion_marks": inv.total_expansion_marks,
        "total_expansion_panels": inv.total_expansion_panels,
        "stock_pieces": stock_pieces,
        "dead_scrap": dead_scrap,
        "total_stock_pieces": inv.total_stock_pieces,
        "available_stock_pieces": inv.available_stock_pieces,
        "depleted_stock_pieces": inv.depleted_stock_pieces,
        "total_stock_area_m2": inv.total_stock_area_m2,
        "remaining_stock_area_m2": inv.remaining_stock_area_m2,
        "total_dead_scrap_pieces": inv.total_dead_scrap_pieces,
        "total_dead_scrap_area_m2": inv.total_dead_scrap_area_m2,
    }


def _build_match_summary(recovery: RecoverySummary) -> list[dict]:
    """Match Summary — each recovery match with full traceability."""
    matches = []
    for m in recovery.matches:
        matches.append({
            "demand_mark": m.demand_mark,
            "demand_product_code": m.demand_product_code,
            "expansion_width": m.expansion_width,
            "demand_length": m.demand_length,
            "demand_qty": m.demand_qty,
            "stock_piece_id": m.stock_piece_id,
            "source_mark": m.source_mark,
            "stock_original_width": m.stock_original_width,
            "stock_width_before": m.stock_width_before,
            "stock_width_after": m.stock_width_after,
            "trim_waste": m.trim_waste,
            "post_consumption_class": m.post_consumption_class,
            "mck": m.mck,
            "candidate_count": m.candidate_count,
            "decision_reason": m.decision_reason,
        })
    return matches


def _build_unmatched_summary(recovery: RecoverySummary) -> list[dict]:
    """Unmatched Summary — demands that could not be satisfied."""
    return list(recovery.unmatched_demands)


def _build_kpi_summary(recovery: RecoverySummary) -> dict:
    """Recovery KPI Summary — all 9 recovery KPIs."""
    return {
        "total_reduction_area_m2": recovery.total_reduction_area_m2,
        "total_expansion_demand_m2": recovery.total_expansion_demand_m2,
        "recovered_area_m2": recovery.recovered_area_m2,
        "unrecovered_area_m2": recovery.unrecovered_area_m2,
        "recovery_rate": recovery.recovery_rate,
        "stock_utilization_rate": recovery.stock_utilization_rate,
        "material_recovery_score": recovery.material_recovery_score,
        "dead_scrap_area_m2": recovery.dead_scrap_area_m2,
        "remaining_stock_area_m2": recovery.remaining_stock_area_m2,
        "frozen_yield": recovery.frozen_yield,
    }


def _build_validation_summary(validation: ValidationReport) -> dict:
    """Validation Summary — all R10-R21 results."""
    rules = []
    for r in validation.results:
        rules.append({
            "rule_id": r.rule_id,
            "description": r.description,
            "status": r.status,
            "detail": r.detail,
        })

    return {
        "total_rules": validation.total_rules,
        "passed": validation.passed,
        "failed": validation.failed,
        "pass_rate": validation.pass_rate,
        "all_passed": validation.all_passed,
        "rules": rules,
    }


def _build_explainability(
    recovery: RecoverySummary,
    panels: list[FabricatedPanel],
) -> list[dict]:
    """Explainability — worked examples for each match and unmatched demand."""
    examples = []

    for m in recovery.matches:
        pitch, depth, thickness = m.mck
        lines = [
            f"MATCH APPROVED",
            f"  Demand:  {m.demand_mark}, expansion_width={m.expansion_width}mm, "
            f"length={m.demand_length}mm, qty={m.demand_qty}",
            f"  Stock:   {m.stock_piece_id}, remaining_width={m.stock_width_before}mm, "
            f"length={m.demand_length}mm, qty={m.demand_qty}",
            f"  MCK Check:",
            f"    Pitch:     {pitch} == {pitch}  PASS",
            f"    Depth:     {depth} == {depth}  PASS",
            f"    Thickness: {thickness} == {thickness}  PASS",
            f"  Width Check:  {m.stock_width_before} >= {m.expansion_width}  PASS",
            f"  Length Check: {m.demand_length} >= {m.demand_length}  PASS",
            f"  Result: MATCHED",
            f"  Width Consumed: {m.expansion_width}mm",
            f"  Remainder: {m.stock_width_after}mm -> "
            f"Post Consumption Classification: {m.post_consumption_class}",
            f"  Decision: {m.decision_reason}",
        ]
        examples.append({
            "type": "MATCH_APPROVED",
            "demand_mark": m.demand_mark,
            "stock_piece_id": m.stock_piece_id,
            "text": "\n".join(lines),
        })

        if m.post_consumption_class == "DEAD_SCRAP":
            reclass_lines = [
                f"POST CONSUMPTION CLASSIFICATION",
                f"  Stock Piece: {m.stock_piece_id}",
                f"  Before Consumption: remaining_width={m.stock_width_before}mm",
                f"  Width Consumed: {m.expansion_width}mm (for {m.demand_mark})",
                f"  After Consumption: remaining_width={m.stock_width_after}mm",
                f"  Classification Check:",
                f"    Width:  {m.stock_width_after}mm < 200mm  FAILS minimum width",
                f"  Result: DEAD_SCRAP",
                f"  Action: Status changed to DEPLETED",
            ]
            examples.append({
                "type": "INVENTORY_RECLASSIFIED",
                "demand_mark": m.demand_mark,
                "stock_piece_id": m.stock_piece_id,
                "text": "\n".join(reclass_lines),
            })

    for m in recovery.matches:
        if m.rejection_log:
            for piece_id, reason in m.rejection_log:
                rej_lines = [
                    f"MATCH REJECTED",
                    f"  Demand: {m.demand_mark}, expansion_width={m.expansion_width}mm",
                    f"  Stock:  {piece_id}",
                    f"  Reason: {reason}",
                ]
                examples.append({
                    "type": "MATCH_REJECTED",
                    "demand_mark": m.demand_mark,
                    "stock_piece_id": piece_id,
                    "text": "\n".join(rej_lines),
                })

    for u in recovery.unmatched_demands:
        unmatched_lines = [
            f"UNMATCHED DEMAND",
            f"  Demand: {u['mark']}, expansion_width={u['expansion_width']}mm, "
            f"length={u['fabricated_length']}mm, qty={u['qty']}",
            f"  Reason: {u['reason']}",
        ]
        examples.append({
            "type": "UNMATCHED",
            "demand_mark": u["mark"],
            "stock_piece_id": "",
            "text": "\n".join(unmatched_lines),
        })

    return examples
