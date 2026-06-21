"""Main processor that orchestrates panel processing through all engines."""

from models import FabricatedPanel, ProjectSummary
from optimizer_models import OptimizationSummary
from product_master import build_product_catalog, lookup_product
from pattern_engine import generate_patterns, select_best_pattern
from rule_engine import apply_rules, calculate_summary
from project_optimizer import optimize_project


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
