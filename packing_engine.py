"""Phase-3.2A Production Cutting Plan Engine — FFD Algorithm.

Groups MCK-compatible panels and packs them into stock lengths
using First Fit Decreasing. This is the baseline reference algorithm.

Reference: DBD_PHASE3.2_REV0.4, Sections 3.1.4-3.1.6, 5.4
"""

from models import FabricatedPanel, ProductMaster
from product_master import build_product_catalog, lookup_product
from rule_engine import STOCK_LENGTH, SAW_KERF
from packing_models import (
    ALGORITHM_ID,
    CutPlan,
    CutPlanEntry,
    LengthRemnant,
    PackingSummary,
    classify_length_remnant,
)


def group_panels_for_packing(
    panels: list[FabricatedPanel],
    catalog: dict[str, ProductMaster],
    depth_map: dict[str, float] | None = None,
) -> tuple[dict[tuple, list[dict]], list[FabricatedPanel]]:
    """Group panels by (standard_width, MCK) applying G1-G3 rules.

    Expansion panels are split into P1 (standard width) and P2 (extension
    strip). Both enter FFD packing in their respective width groups.

    Returns:
        (groups dict keyed by (std_width, mck), excluded panels list)
    """
    if depth_map is None:
        depth_map = {}

    groups: dict[tuple, list[dict]] = {}
    excluded: list[FabricatedPanel] = []

    for panel in panels:
        product = lookup_product(panel.product_code, catalog)
        if product is None:
            excluded.append(panel)
            continue

        pitch = product.load_bar_pitch
        depth = depth_map.get(panel.product_code, 0.0)
        thickness = panel.load_bar_thickness
        std_width = panel.standard_width
        mck = (pitch, depth, thickness)

        if panel.needs_expansion:
            p1_key = (std_width, mck)
            if p1_key not in groups:
                groups[p1_key] = []
            groups[p1_key].append({
                "mark": f"{panel.mark}-P1",
                "product_code": panel.product_code,
                "fabricated_length": panel.fabricated_length,
                "qty": panel.qty,
                "note": f"expand P1 (std {std_width:.0f}mm)",
            })

            p2_width = panel.expansion_width
            p2_key = (p2_width, mck)
            if p2_key not in groups:
                groups[p2_key] = []
            groups[p2_key].append({
                "mark": f"{panel.mark}-P2",
                "product_code": panel.product_code,
                "fabricated_length": panel.fabricated_length,
                "qty": panel.qty,
                "note": f"expand P2 (extend {p2_width:.0f}mm)",
            })
        else:
            group_key = (std_width, mck)
            if group_key not in groups:
                groups[group_key] = []

            note = ""
            if panel.needs_reduction:
                note = f"reduce {panel.reduction_width:.0f}mm"

            groups[group_key].append({
                "mark": panel.mark,
                "product_code": panel.product_code,
                "fabricated_length": panel.fabricated_length,
                "qty": panel.qty,
                "note": note,
            })

    return groups, excluded


def _expand_to_units(group: list[dict]) -> list[dict]:
    """Expand panel demands into individual quantity units."""
    units = []
    for item in group:
        for _ in range(item["qty"]):
            units.append({
                "mark": item["mark"],
                "product_code": item["product_code"],
                "fabricated_length": item["fabricated_length"],
                "note": item.get("note", ""),
            })
    return units


def _group_bin_entries(raw_entries: list[dict]) -> list[CutPlanEntry]:
    """Group identical (mark, product_code, length) into CutPlanEntry with qty."""
    counts: dict[tuple, int] = {}
    notes: dict[tuple, str] = {}
    for e in raw_entries:
        key = (e["mark"], e["product_code"], e["fabricated_length"])
        counts[key] = counts.get(key, 0) + 1
        if e.get("note"):
            notes[key] = e["note"]

    return [
        CutPlanEntry(mark=m, product_code=pc, fabricated_length=fl, qty=q,
                     note=notes.get((m, pc, fl), ""))
        for (m, pc, fl), q in counts.items()
    ]


def _ffd_pack(units: list[dict], stock_length: float, saw_kerf: float,
              stock_width: float, mck: tuple, start_bin: int = 1) -> list[CutPlan]:
    """First Fit Decreasing bin packing.

    Kerf model: N cuts for N panels. Each panel consumes
    fabricated_length + SAW_KERF from the bin.
    """
    sorted_units = sorted(units, key=lambda u: u["fabricated_length"], reverse=True)

    bins: list[list[dict]] = []
    remaining: list[float] = []

    for unit in sorted_units:
        needed = unit["fabricated_length"] + saw_kerf
        placed = False

        for i, rem in enumerate(remaining):
            if rem >= needed:
                bins[i].append(unit)
                remaining[i] -= needed
                placed = True
                break

        if not placed:
            bins.append([unit])
            remaining.append(stock_length - needed)

    cut_plans = []
    for i, raw_entries in enumerate(bins, start=start_bin):
        bin_id = f"BIN-{i:03d}"
        n_panels = len(raw_entries)
        panel_length_sum = sum(e["fabricated_length"] for e in raw_entries)
        kerf_loss = n_panels * saw_kerf
        total_used = panel_length_sum + kerf_loss
        rem_length = round(stock_length - total_used, 2)
        rem_class = classify_length_remnant(rem_length, stock_width)
        rem_area = round((rem_length / 1000.0) * (stock_width / 1000.0), 6)

        entries = _group_bin_entries(raw_entries)

        cut_plans.append(CutPlan(
            bin_id=bin_id,
            stock_width=stock_width,
            stock_length=stock_length,
            mck=mck,
            entries=entries,
            total_panels=n_panels,
            total_used=round(total_used, 2),
            remnant_length=rem_length,
            remnant_classification=rem_class,
            remnant_area_m2=rem_area,
        ))

    return cut_plans


def run_length_packing(
    panels: list[FabricatedPanel],
    catalog: dict[str, ProductMaster],
    depth_map: dict[str, float] | None = None,
) -> PackingSummary:
    """Run FFD length packing on all eligible panels."""
    groups, excluded = group_panels_for_packing(panels, catalog, depth_map)

    all_cut_plans: list[CutPlan] = []
    all_remnants: list[LengthRemnant] = []
    total_items_packed = 0
    marks_packed: set[str] = set()
    next_bin = 1

    for (std_width, mck), group in groups.items():
        units = _expand_to_units(group)
        if not units:
            continue

        cut_plans = _ffd_pack(units, STOCK_LENGTH, SAW_KERF, std_width, mck, start_bin=next_bin)
        next_bin += len(cut_plans)
        all_cut_plans.extend(cut_plans)

        for cp in cut_plans:
            total_items_packed += cp.total_panels
            for entry in cp.entries:
                marks_packed.add(entry.mark)

            if cp.remnant_classification != "EXACT_FIT":
                all_remnants.append(LengthRemnant(
                    remnant_id=f"REM-{cp.bin_id}",
                    bin_id=cp.bin_id,
                    stock_width=cp.stock_width,
                    remnant_length=cp.remnant_length,
                    remnant_area_m2=cp.remnant_area_m2,
                    classification=cp.remnant_classification,
                    mck=cp.mck,
                ))

    excluded_items = sum(p.qty for p in excluded)
    stock_before = total_items_packed + excluded_items
    stock_after = len(all_cut_plans) + excluded_items
    stock_savings = stock_before - stock_after

    raw_material_area = sum(
        cp.stock_length / 1000.0 * (cp.stock_width / 1000.0)
        for cp in all_cut_plans
    )
    product_area = sum(
        e.fabricated_length / 1000.0 * (cp.stock_width / 1000.0) * e.qty
        for cp in all_cut_plans for e in cp.entries
    )
    utilization = (product_area / raw_material_area * 100.0) if raw_material_area > 0 else 0.0

    kerf_loss_area = sum(
        cp.total_panels * SAW_KERF / 1000.0 * (cp.stock_width / 1000.0)
        for cp in all_cut_plans
    )

    reusable_m2 = sum(r.remnant_area_m2 for r in all_remnants if r.classification == "REUSABLE_REMNANT")
    waste_m2 = sum(r.remnant_area_m2 for r in all_remnants if r.classification == "LENGTH_WASTE")

    total_waste = waste_m2 + kerf_loss_area

    return PackingSummary(
        total_bins=len(all_cut_plans),
        total_items_packed=total_items_packed,
        total_marks_packed=len(marks_packed),
        stock_lengths_before=stock_before,
        stock_lengths_after=stock_after,
        stock_savings=stock_savings,
        stock_savings_percent=round(stock_savings / stock_before * 100.0, 2) if stock_before > 0 else 0.0,
        stock_utilization_rate=round(utilization, 2),
        total_raw_material_area_m2=round(raw_material_area, 6),
        total_product_area_m2=round(product_area, 6),
        total_waste_area_m2=round(total_waste, 6),
        total_kerf_loss_m2=round(kerf_loss_area, 6),
        total_reusable_remnant_area_m2=round(reusable_m2, 6),
        total_length_waste_m2=round(waste_m2, 6),
        total_exact_fit_bins=sum(1 for cp in all_cut_plans if cp.remnant_classification == "EXACT_FIT"),
        algorithm=ALGORITHM_ID,
        cut_plans=all_cut_plans,
        length_remnants=all_remnants,
    )
