"""Phase-3.2A Production Cutting Plan — Report Generation.

Produces a structured report: Summary + Production Cutting Plan + Validation.

Reference: DBD_PHASE3.2_REV0.4, Section 7.1
"""

from packing_models import PackingSummary


def generate_packing_report(
    packing: PackingSummary,
    validation: dict,
) -> dict:
    """Generate production cutting plan report.

    Returns dict with sections: summary, cutting_plan, validation.
    """
    summary = {
        "algorithm": packing.algorithm,
        "total_bins": packing.total_bins,
        "total_items_packed": packing.total_items_packed,
        "total_marks_packed": packing.total_marks_packed,
        "stock_lengths_before": packing.stock_lengths_before,
        "stock_lengths_after": packing.stock_lengths_after,
        "stock_savings": packing.stock_savings,
        "stock_savings_percent": packing.stock_savings_percent,
        "stock_utilization_rate": packing.stock_utilization_rate,
        "total_raw_material_area_m2": packing.total_raw_material_area_m2,
        "total_product_area_m2": packing.total_product_area_m2,
        "total_waste_area_m2": packing.total_waste_area_m2,
        "total_kerf_loss_m2": packing.total_kerf_loss_m2,
        "total_reusable_remnant_area_m2": packing.total_reusable_remnant_area_m2,
        "total_length_waste_m2": packing.total_length_waste_m2,
        "total_exact_fit_bins": packing.total_exact_fit_bins,
    }

    cutting_plan = []
    for cp in packing.cut_plans:
        entry_notes = []
        for e in cp.entries:
            label = f"{e.mark} x {e.qty}"
            if e.note:
                label += f" ({e.note})"
            entry_notes.append(label)
        marks = ", ".join(entry_notes)

        remnant_text = (
            f"Remnant {cp.remnant_length:.0f}mm ({cp.remnant_classification})"
            if cp.remnant_classification != "EXACT_FIT"
            else "EXACT FIT"
        )
        cutting_plan.append({
            "bin_id": cp.bin_id,
            "stock_width": cp.stock_width,
            "mck": cp.mck,
            "entries": [
                {
                    "mark": e.mark,
                    "product_code": e.product_code,
                    "fabricated_length": e.fabricated_length,
                    "qty": e.qty,
                    "note": e.note,
                }
                for e in cp.entries
            ],
            "total_panels": cp.total_panels,
            "total_used": cp.total_used,
            "remnant_length": cp.remnant_length,
            "remnant_classification": cp.remnant_classification,
            "display": f"Bar {cp.bin_id}: {marks}, {remnant_text}",
        })

    return {
        "summary": summary,
        "cutting_plan": cutting_plan,
        "validation": validation,
    }
