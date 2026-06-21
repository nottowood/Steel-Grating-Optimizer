"""Project Optimizer — Phase-2 project-level pattern optimization.

Optimizes an entire project simultaneously for floor visual consistency.
This is an additional layer on top of the Phase-1 Rule Engine and Pattern Engine.

Phase-1 logic is NOT modified. Phase-2 selects which Phase-1 candidate pattern
to assign to each panel based on project-level visual consistency goals.

Scenario generation: one scenario per unique Start Length across all panels
in a Floor Group. Every start that appears in Pattern Details appears as a
candidate in Scenario Comparison.

Temporary grouping assumption (Phase-2 only):
    Floor Group = Product Code.
    Future versions will support Area, Zone, and Installation Sequence.
"""

from collections import defaultdict

from models import FabricatedPanel
from pattern_engine import select_best_pattern
from rule_engine import calculate_summary
from optimizer_models import (
    CandidateScenario,
    FloorGroupResult,
    OptimizationSummary,
    PanelAssignment,
)

# --- Scoring weights ---
W_COVERAGE = 1000
W_PREFERRED = 500
W_ROD = 0.5
W_YIELD = 50
W_FALLBACK = -100

# --- Coverage thresholds ---
COVERAGE_HIGH = 90.0
COVERAGE_LOW = 50.0


def optimize_project(
    panels: list[FabricatedPanel],
) -> tuple[list[FabricatedPanel], OptimizationSummary]:
    """Run project-level optimization on pre-processed panels."""
    floor_groups = _group_by_product(panels)

    individual_summary = calculate_summary(panels)
    yield_individual = individual_summary.yield_percent

    group_results = []
    for group_name, group_panels in floor_groups.items():
        result = _optimize_floor_group(group_name, group_panels)
        result.yield_individual = _calc_group_yield(group_panels)
        group_results.append(result)

    _apply_assignments(panels, group_results)

    optimized_summary = calculate_summary(panels)
    yield_optimized = optimized_summary.yield_percent

    total_common_qty = sum(r.coverage_qty for r in group_results)
    total_qty = sum(r.total_qty for r in group_results)
    total_common_marks = sum(r.coverage_marks for r in group_results)
    total_marks = sum(r.total_marks for r in group_results)
    total_fallback = total_qty - total_common_qty
    overall_consistency = round((total_common_qty / total_qty * 100) if total_qty > 0 else 0, 2)

    opt_summary = OptimizationSummary(
        overall_consistency=overall_consistency,
        yield_individual=yield_individual,
        yield_optimized=yield_optimized,
        yield_difference=round(yield_optimized - yield_individual, 2),
        total_floor_groups=len(group_results),
        total_fallback_groups=sum(1 for r in group_results if r.consistency_status == "REJECTED"),
        total_coverage_panels=total_common_qty,
        total_panels=total_qty,
        total_coverage_marks=total_common_marks,
        total_marks=total_marks,
        total_fallback_panels=total_fallback,
        fallback_rate=round((total_fallback / total_qty * 100) if total_qty > 0 else 0, 2),
        optimization_mode="COMMON START",
        floor_groups=group_results,
    )
    return panels, opt_summary


def _group_by_product(panels: list[FabricatedPanel]) -> dict[str, list[FabricatedPanel]]:
    groups: dict[str, list[FabricatedPanel]] = defaultdict(list)
    for panel in panels:
        groups[panel.product_code].append(panel)
    return dict(groups)


def _optimize_floor_group(
    group_name: str, panels: list[FabricatedPanel]
) -> FloorGroupResult:
    """Optimize one Floor Group for visual consistency.

    Generates one scenario per unique Start Length found across all panels.
    """
    total_qty = sum(p.qty for p in panels)
    all_marks = [p.mark for p in panels]
    total_marks = len(all_marks)

    # Build per-mark pattern map: {mark: {start_length: rod_qty}}
    mark_start_rod: dict[str, dict[float, int]] = {}
    panel_qty: dict[str, int] = {}
    for panel in panels:
        panel_qty[panel.mark] = panel.qty
        mark_start_rod[panel.mark] = {
            pat.start_length: pat.rod_qty for pat in panel.all_patterns
        }

    # Collect ALL unique starts across all marks
    all_unique_starts = sorted(set(
        start
        for rod_map in mark_start_rod.values()
        for start in rod_map.keys()
    ))

    if not all_unique_starts:
        return FloorGroupResult(
            group_name=group_name,
            total_qty=total_qty,
            total_marks=total_marks,
            consistency_status="REJECTED",
        )

    # Build one scenario per unique start
    yield_base = _calc_group_yield(panels)
    scenarios: list[CandidateScenario] = []

    for start_val in all_unique_starts:
        matching = []
        non_matching = []
        rod_values = []

        for mark in all_marks:
            if start_val in mark_start_rod[mark]:
                matching.append(mark)
                rod_values.append(mark_start_rod[mark][start_val])
            else:
                non_matching.append(mark)

        coverage_qty = sum(panel_qty[m] for m in matching)
        coverage_pct = round((coverage_qty / total_qty * 100) if total_qty > 0 else 0, 2)
        avg_rod = round(sum(rod_values) / len(rod_values), 1) if rod_values else 0.0
        is_preferred = 40.0 <= start_val <= 45.0

        scenario = CandidateScenario(
            representative_start=start_val,
            matching_marks=matching,
            non_matching_marks=non_matching,
            coverage_qty=coverage_qty,
            total_qty=total_qty,
            coverage_percent=coverage_pct,
            coverage_marks=len(matching),
            total_marks=total_marks,
            is_preferred=is_preferred,
            avg_rod_qty=avg_rod,
            yield_optimized=yield_base,
            fallback_count=len(non_matching),
        )
        scenario.score, scenario.score_breakdown = _score_scenario(scenario)
        scenarios.append(scenario)

    # Sort by score descending, then smallest start as tiebreaker
    scenarios.sort(key=lambda s: (-s.score, s.representative_start))

    best = scenarios[0]
    _assign_rejection_reasons(scenarios, best)

    # Determine consistency status
    if best.coverage_percent >= COVERAGE_HIGH:
        status = "HIGH"
    elif best.coverage_percent >= COVERAGE_LOW:
        status = "MEDIUM"
    else:
        status = "REJECTED"

    # Build assignments
    if status == "REJECTED":
        assignments = _build_fallback_assignments(panels)
        common_start = None
        common_marks: list[str] = []
        fb_marks = list(all_marks)
        preferred_hit = False
    else:
        best.selected = True
        assignments = _build_optimized_assignments(panels, best)
        common_start = best.representative_start
        common_marks = list(best.matching_marks)
        fb_marks = list(best.non_matching_marks)
        preferred_hit = best.is_preferred

    yield_opt_final = best.yield_optimized if status != "REJECTED" else 0.0

    return FloorGroupResult(
        group_name=group_name,
        common_start=common_start,
        coverage_percent=best.coverage_percent if status != "REJECTED" else 0.0,
        coverage_qty=best.coverage_qty if status != "REJECTED" else 0,
        coverage_marks=len(common_marks),
        total_qty=total_qty,
        total_marks=total_marks,
        common_start_marks=common_marks,
        fallback_marks=fb_marks,
        is_preferred=preferred_hit,
        consistency_status=status,
        assignments=assignments,
        all_scenarios=scenarios,
        yield_optimized=yield_opt_final,
        yield_difference=0.0,
    )


def _score_scenario(scenario: CandidateScenario) -> tuple[float, dict]:
    """Score a candidate scenario.

    Score = Coverage + Preferred + Rod Bonus + Yield + Fallback
    """
    coverage_score = W_COVERAGE * (scenario.coverage_percent / 100.0)
    preferred_score = W_PREFERRED if scenario.is_preferred else 0
    rod_score = W_ROD * scenario.avg_rod_qty
    yield_score = W_YIELD * (scenario.yield_optimized / 100.0) if scenario.yield_optimized > 0 else 0
    fallback_score = W_FALLBACK * scenario.fallback_count

    total = coverage_score + preferred_score + rod_score + yield_score + fallback_score

    breakdown = {
        "coverage": round(coverage_score, 2),
        "preferred": round(preferred_score, 2),
        "rod_bonus": round(rod_score, 2),
        "yield": round(yield_score, 2),
        "fallback": round(fallback_score, 2),
        "total": round(total, 2),
    }
    return round(total, 2), breakdown


def _assign_rejection_reasons(
    scenarios: list[CandidateScenario], best: CandidateScenario
) -> None:
    """Assign human-readable rejection reason to every non-selected scenario."""
    for sc in scenarios:
        if sc is best:
            sc.rejection_reason = ""
            continue

        reasons = []
        if sc.coverage_percent < best.coverage_percent:
            reasons.append(f"Coverage {sc.coverage_percent:.1f}% < selected {best.coverage_percent:.1f}%")
        if sc.coverage_percent == best.coverage_percent and sc.avg_rod_qty < best.avg_rod_qty:
            reasons.append(f"Lower avg rod qty ({sc.avg_rod_qty:.1f} vs {best.avg_rod_qty:.1f})")
        if best.is_preferred and not sc.is_preferred:
            reasons.append("Not in preferred range (40-45 mm)")
        if not reasons:
            reasons.append(f"Lower score ({sc.score} vs {best.score})")

        sc.rejection_reason = "; ".join(reasons)


def _calc_group_yield(panels: list[FabricatedPanel]) -> float:
    summary = calculate_summary(panels)
    return summary.yield_percent


def _build_optimized_assignments(
    panels: list[FabricatedPanel],
    scenario: CandidateScenario,
) -> list[PanelAssignment]:
    """Build per-panel assignments for a selected scenario."""
    matching_set = set(scenario.matching_marks)
    assignments = []

    for panel in panels:
        if panel.mark in matching_set:
            pat = _find_pattern_by_start(panel, scenario.representative_start)
            assignments.append(PanelAssignment(
                mark=panel.mark,
                product_code=panel.product_code,
                start_length=pat.start_length if pat else scenario.representative_start,
                rod_qty=pat.rod_qty if pat else 0,
                assignment_type="COMMON",
                reason=f"Common Start = {scenario.representative_start} mm",
            ))
        else:
            best = select_best_pattern(panel.all_patterns)
            assignments.append(PanelAssignment(
                mark=panel.mark,
                product_code=panel.product_code,
                start_length=best.start_length if best else 0,
                rod_qty=best.rod_qty if best else 0,
                assignment_type="INDIVIDUAL",
                reason="No matching pattern at selected start",
            ))
    return assignments


def _build_fallback_assignments(panels: list[FabricatedPanel]) -> list[PanelAssignment]:
    assignments = []
    for panel in panels:
        best = select_best_pattern(panel.all_patterns)
        assignments.append(PanelAssignment(
            mark=panel.mark,
            product_code=panel.product_code,
            start_length=best.start_length if best else 0,
            rod_qty=best.rod_qty if best else 0,
            assignment_type="INDIVIDUAL",
            reason="Floor consistency rejected (coverage < 50%)",
        ))
    return assignments


def _find_pattern_by_start(panel: FabricatedPanel, target_start: float):
    for pat in panel.all_patterns:
        if pat.start_length == target_start:
            return pat
    return None


def _apply_assignments(
    panels: list[FabricatedPanel],
    group_results: list[FloorGroupResult],
) -> None:
    assignment_map: dict[str, PanelAssignment] = {}
    for result in group_results:
        for assign in result.assignments:
            assignment_map[assign.mark] = assign

    for panel in panels:
        assign = assignment_map.get(panel.mark)
        if assign is None:
            continue
        target_start = assign.start_length
        pat = _find_pattern_by_start(panel, target_start)
        if pat:
            pat.selection_reason = f"{assign.assignment_type}: {assign.reason}"
            panel.pattern = pat
