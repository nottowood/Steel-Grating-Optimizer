"""Main processor that orchestrates panel processing through all engines."""

from models import FabricatedPanel, ProjectSummary
from optimizer_models import OptimizationSummary
from product_master import build_product_catalog, lookup_product
from pattern_engine import generate_patterns, select_best_pattern
from rule_engine import apply_rules, calculate_summary
from project_optimizer import optimize_project
from recovery_engine import run_recovery_engine
from recovery_validation import validate_recovery
from recovery_report import generate_recovery_report
from packing_engine import run_length_packing
from packing_validation import validate_packing
from packing_report import generate_packing_report


def process_panels(
    panels: list[FabricatedPanel],
) -> tuple[list[FabricatedPanel], ProjectSummary, list[str]]:
    """Phase-1: Process panels individually through rule engine and pattern engine."""
    catalog = build_product_catalog()
    warnings = []
    processed = []

    for panel in panels:
        product = lookup_product(panel.product_code, catalog)
        if product is None:
            warnings.append(f"Mark {panel.mark}: Unknown product code '{panel.product_code}'")
            continue

        panel = apply_rules(panel, product)
        patterns = generate_patterns(panel.cut_length, product.cross_bar_pitch)
        panel.all_patterns = patterns

        best = select_best_pattern(patterns)
        if best is None:
            warnings.append(
                f"Mark {panel.mark}: No valid pattern for cut length {panel.cut_length} mm"
            )
        panel.pattern = best
        processed.append(panel)

    summary = calculate_summary(processed)
    return processed, summary, warnings


def process_panels_optimized(
    panels: list[FabricatedPanel],
) -> tuple[list[FabricatedPanel], ProjectSummary, OptimizationSummary, list[str]]:
    """Phase-2: Process panels then optimize project-level visual consistency.

    Step 1: Run Phase-1 processing (rules + individual pattern selection)
    Step 2: Run Phase-2 optimization (clustering + common start selection)
    Step 3: Recalculate KPI with optimized assignments
    """
    processed, _, warnings = process_panels(panels)

    optimized, opt_summary = optimize_project(processed)

    summary = calculate_summary(optimized)

    return optimized, summary, opt_summary, warnings


def process_panels_with_recovery(
    panels: list[FabricatedPanel],
    depth_map: dict[str, float] | None = None,
) -> dict:
    """Phase-3: Process panels with Material Recovery Engine.

    Runs the full Phase-1 + Phase-2 pipeline, then layers Phase-3
    recovery on top. Frozen outputs are returned unchanged.

    Args:
        panels: Raw panels from CSV input.
        depth_map: Product code -> load_bar_depth (mm). None is safe.
    """
    processed, summary, opt_summary, warnings = process_panels_optimized(panels)

    catalog = build_product_catalog()
    recovery = run_recovery_engine(processed, summary, catalog, depth_map)
    validation = validate_recovery(recovery, processed, summary)
    report = generate_recovery_report(recovery, validation, processed)

    return {
        "processed": processed,
        "summary": summary,
        "opt_summary": opt_summary,
        "warnings": warnings,
        "recovery_summary": recovery,
        "validation_report": validation,
        "recovery_report": report,
    }


def process_panels_with_packing(
    panels: list[FabricatedPanel],
    depth_map: dict[str, float] | None = None,
) -> dict:
    """Phase-3.2A: Process panels with Recovery + Length Packing.

    Runs the full Phase-1 + Phase-2 + Phase-3.1 pipeline, then layers
    Phase-3.2A length packing on top. All prior outputs are returned unchanged.

    Args:
        panels: Raw panels from CSV input.
        depth_map: Product code -> load_bar_depth (mm). None is safe.
    """
    result = process_panels_with_recovery(panels, depth_map)

    catalog = build_product_catalog()
    packing = run_length_packing(result["processed"], catalog, depth_map)
    packing_val = validate_packing(
        packing,
        result["summary"].yield_percent,
        result["summary"].yield_percent,
    )
    packing_rpt = generate_packing_report(packing, packing_val)

    result["packing_summary"] = packing
    result["packing_validation"] = packing_val
    result["packing_report"] = packing_rpt

    return result
