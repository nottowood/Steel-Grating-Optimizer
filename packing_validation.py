"""Phase-3.2A Length Packing — Validation Rules R22-R29.

Validates packing output against design constraints.
R30-R32 (match improvement) deferred to Phase-3.2B.

Reference: DBD_PHASE3.2_REV0.4, Section 6.2
"""

from rule_engine import STOCK_LENGTH, SAW_KERF
from packing_models import (
    PackingSummary,
    PACKING_REUSABLE_MIN_LENGTH,
    PACKING_REUSABLE_MIN_AREA,
    classify_length_remnant,
)


def validate_packing(
    packing: PackingSummary,
    frozen_yield: float,
    frozen_yield_after: float,
) -> dict:
    """Run R22-R29 validation on packing results."""
    rules = []

    # R22: No Bin Overflow
    r22_details = []
    r22_pass = True
    for cp in packing.cut_plans:
        if cp.total_used > cp.stock_length + 0.01:
            r22_pass = False
            r22_details.append(f"{cp.bin_id}: {cp.total_used} > {cp.stock_length}")
    rules.append({
        "rule_id": "R22",
        "description": "No Bin Overflow",
        "status": "PASS" if r22_pass else "FAIL",
        "detail": f"{len(packing.cut_plans)} bins checked"
        if r22_pass else "; ".join(r22_details),
    })

    # R23: Kerf Accounted (N cuts = N panels)
    r23_pass = True
    r23_details = []
    for cp in packing.cut_plans:
        expected_kerf = cp.total_panels * SAW_KERF
        panel_sum = sum(e.fabricated_length * e.qty for e in cp.entries)
        actual_total = panel_sum + expected_kerf
        if abs(actual_total - cp.total_used) > 0.01:
            r23_pass = False
            r23_details.append(f"{cp.bin_id}: panels+kerf {actual_total} != total_used {cp.total_used}")
    rules.append({
        "rule_id": "R23",
        "description": "Kerf Accounted",
        "status": "PASS" if r23_pass else "FAIL",
        "detail": f"{len(packing.cut_plans)} bins, N cuts = N panels"
        if r23_pass else "; ".join(r23_details),
    })

    # R24: Panel Coverage
    r24_items = sum(cp.total_panels for cp in packing.cut_plans)
    r24_pass = r24_items == packing.total_items_packed
    rules.append({
        "rule_id": "R24",
        "description": "Panel Coverage",
        "status": "PASS" if r24_pass else "FAIL",
        "detail": f"{r24_items} items in bins = {packing.total_items_packed} total packed"
        if r24_pass else f"Mismatch: {r24_items} in bins vs {packing.total_items_packed} reported",
    })

    # R25: Remnant Classification Consistent
    r25_pass = True
    r25_details = []
    for cp in packing.cut_plans:
        expected_class = classify_length_remnant(cp.remnant_length, cp.stock_width)
        if cp.remnant_classification != expected_class:
            r25_pass = False
            r25_details.append(
                f"{cp.bin_id}: {cp.remnant_classification} != {expected_class}"
            )
    rules.append({
        "rule_id": "R25",
        "description": "Remnant Classification Consistent",
        "status": "PASS" if r25_pass else "FAIL",
        "detail": f"{len(packing.cut_plans)} bins classified correctly"
        if r25_pass else "; ".join(r25_details),
    })

    # R26: Stock Savings Non-Negative
    r26_pass = packing.stock_lengths_after <= packing.stock_lengths_before
    rules.append({
        "rule_id": "R26",
        "description": "Stock Savings Non-Negative",
        "status": "PASS" if r26_pass else "FAIL",
        "detail": f"{packing.stock_lengths_before} -> {packing.stock_lengths_after} "
        f"(saved {packing.stock_savings})",
    })

    # R27: Packing Utilization Bounded
    r27_pass = 0.0 <= packing.stock_utilization_rate <= 100.0
    rules.append({
        "rule_id": "R27",
        "description": "Packing Utilization Bounded",
        "status": "PASS" if r27_pass else "FAIL",
        "detail": f"Utilization = {packing.stock_utilization_rate}%",
    })

    # R28: Frozen KPI Unchanged
    r28_pass = abs(frozen_yield - frozen_yield_after) < 0.001
    rules.append({
        "rule_id": "R28",
        "description": "Frozen KPI Unchanged",
        "status": "PASS" if r28_pass else "FAIL",
        "detail": f"Yield before={frozen_yield}%, after={frozen_yield_after}%",
    })

    # R29: Packing Conservation
    r29_pass = True
    r29_details = []
    for cp in packing.cut_plans:
        panel_sum = sum(e.fabricated_length * e.qty for e in cp.entries)
        kerf_loss = cp.total_panels * SAW_KERF
        conservation = panel_sum + cp.remnant_length + kerf_loss
        if abs(conservation - cp.stock_length) > 0.01:
            r29_pass = False
            r29_details.append(
                f"{cp.bin_id}: {panel_sum} + {cp.remnant_length} + {kerf_loss} "
                f"= {conservation} != {cp.stock_length}"
            )
    rules.append({
        "rule_id": "R29",
        "description": "Packing Conservation",
        "status": "PASS" if r29_pass else "FAIL",
        "detail": f"{len(packing.cut_plans)} bins: packed + remnant + kerf = stock_length"
        if r29_pass else "; ".join(r29_details),
    })

    passed = sum(1 for r in rules if r["status"] == "PASS")
    failed = sum(1 for r in rules if r["status"] == "FAIL")

    return {
        "rules": rules,
        "passed": passed,
        "failed": failed,
        "total": len(rules),
        "all_passed": failed == 0,
    }
