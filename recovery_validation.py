"""Phase-3 Recovery Validation — Centralized Rule Checking.

Validates all Phase-3 rules (R10-R21) against recovery results.
Produces structured validation reports with PASS/FAIL status
and detailed diagnostic messages.

No UI integration — report formatting belongs in recovery_report.py.
No modification of any input data.

Reference: DBD_PHASE3_REV0.3, Section 10
"""

from dataclasses import dataclass, field

from models import FabricatedPanel, ProjectSummary
from recovery_models import (
    RecoverySummary,
    classify_remainder,
)


@dataclass
class ValidationResult:
    """Result of a single validation rule check."""

    rule_id: str
    description: str
    status: str  # PASS | FAIL
    detail: str = ""


@dataclass
class ValidationReport:
    """Complete validation report for Phase-3 recovery."""

    results: list[ValidationResult] = field(default_factory=list)
    total_rules: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)
        self.total_rules += 1
        if result.status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
        self.pass_rate = round((self.passed / self.total_rules) * 100, 2)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0


def validate_recovery(
    recovery: RecoverySummary,
    panels: list[FabricatedPanel],
    project_summary: ProjectSummary,
) -> ValidationReport:
    """Run all Phase-3 validation rules and return a structured report."""
    report = ValidationReport()

    report.add(_validate_r10(recovery, panels))
    report.add(_validate_r11(recovery))
    report.add(_validate_r12(recovery))
    report.add(_validate_r13(recovery))
    report.add(_validate_r14(recovery))
    report.add(_validate_r15(recovery))
    report.add(_validate_r16(recovery))
    report.add(_validate_r17(recovery))
    report.add(_validate_r18(recovery, project_summary))
    report.add(_validate_r19(recovery))
    report.add(_validate_r20(recovery))
    report.add(_validate_r21(recovery))

    return report


def _validate_r10(recovery: RecoverySummary, panels: list[FabricatedPanel]) -> ValidationResult:
    """R10: Strip Classification Complete.

    Every reduction panel must produce exactly one inventory record.
    """
    reduction_marks = {p.mark for p in panels if p.needs_reduction}

    stock_marks = {sp.source_mark for sp in recovery.inventory.stock_pieces}
    dead_marks = {
        ds.source_mark
        for ds in recovery.inventory.dead_scrap_pieces
        if ds.origin == "REDUCTION"
    }
    classified_marks = stock_marks | dead_marks

    missing = reduction_marks - classified_marks
    extra = classified_marks - reduction_marks

    if not missing and not extra:
        return ValidationResult(
            rule_id="R10",
            description="Strip Classification Complete",
            status="PASS",
            detail=f"{len(reduction_marks)} reduction marks, all classified",
        )

    parts = []
    if missing:
        parts.append(f"Missing classification: {sorted(missing)}")
    if extra:
        parts.append(f"Extra records for non-reduction marks: {sorted(extra)}")
    return ValidationResult(
        rule_id="R10",
        description="Strip Classification Complete",
        status="FAIL",
        detail="; ".join(parts),
    )


def _validate_r11(recovery: RecoverySummary) -> ValidationResult:
    """R11: No Over-Consumption.

    remaining_width >= 0 for all stock pieces.
    """
    violations = [
        f"{sp.piece_id}: remaining_width={sp.remaining_width}"
        for sp in recovery.inventory.stock_pieces
        if sp.remaining_width < 0
    ]

    if not violations:
        return ValidationResult(
            rule_id="R11",
            description="No Over-Consumption",
            status="PASS",
            detail=f"{len(recovery.inventory.stock_pieces)} stock pieces checked",
        )

    return ValidationResult(
        rule_id="R11",
        description="No Over-Consumption",
        status="FAIL",
        detail=f"Negative remaining width: {'; '.join(violations)}",
    )


def _validate_r12(recovery: RecoverySummary) -> ValidationResult:
    """R12: MCK Verified.

    Every match must have stock.mck == demand.mck (all 3 fields).
    """
    piece_map = {sp.piece_id: sp for sp in recovery.inventory.stock_pieces}

    violations = []
    for m in recovery.matches:
        sp = piece_map.get(m.stock_piece_id)
        if sp is None:
            violations.append(f"{m.demand_mark}: stock piece {m.stock_piece_id} not found")
            continue
        if sp.mck != m.mck:
            violations.append(
                f"{m.demand_mark}: stock MCK {sp.mck} != demand MCK {m.mck}"
            )

    if not violations:
        return ValidationResult(
            rule_id="R12",
            description="MCK Verified",
            status="PASS",
            detail=f"{len(recovery.matches)} matches verified",
        )

    return ValidationResult(
        rule_id="R12",
        description="MCK Verified",
        status="FAIL",
        detail="; ".join(violations),
    )


def _validate_r13(recovery: RecoverySummary) -> ValidationResult:
    """R13: Qty Balanced.

    Sum of consumed qty <= source qty for every stock piece.
    """
    violations = []
    for sp in recovery.inventory.stock_pieces:
        total_consumed = sum(c.qty_consumed for c in sp.consumption_log)
        if total_consumed > sp.qty:
            violations.append(
                f"{sp.piece_id}: consumed {total_consumed} > source qty {sp.qty}"
            )

    if not violations:
        return ValidationResult(
            rule_id="R13",
            description="Qty Balanced",
            status="PASS",
            detail=f"{len(recovery.inventory.stock_pieces)} stock pieces checked",
        )

    return ValidationResult(
        rule_id="R13",
        description="Qty Balanced",
        status="FAIL",
        detail="; ".join(violations),
    )


def _validate_r14(recovery: RecoverySummary) -> ValidationResult:
    """R14: Recovered Area Consistent.

    Sum of individual match recovered areas must equal total recovered_area_m2.
    """
    individual_sum = round(
        sum(
            (m.expansion_width / 1000) * (m.demand_length / 1000) * m.demand_qty
            for m in recovery.matches
        ),
        4,
    )
    total = recovery.recovered_area_m2

    if individual_sum == total:
        return ValidationResult(
            rule_id="R14",
            description="Recovered Area Consistent",
            status="PASS",
            detail=f"Sum={individual_sum} == Total={total}",
        )

    return ValidationResult(
        rule_id="R14",
        description="Recovered Area Consistent",
        status="FAIL",
        detail=f"Sum={individual_sum} != Total={total}",
    )


def _validate_r15(recovery: RecoverySummary) -> ValidationResult:
    """R15: Recovery Rate Bounded.

    0% <= Recovery Rate <= 100%.
    """
    rate = recovery.recovery_rate

    if 0 <= rate <= 100:
        return ValidationResult(
            rule_id="R15",
            description="Recovery Rate Bounded",
            status="PASS",
            detail=f"Recovery Rate = {rate}%",
        )

    return ValidationResult(
        rule_id="R15",
        description="Recovery Rate Bounded",
        status="FAIL",
        detail=f"Recovery Rate = {rate}% (out of 0-100 range)",
    )


def _validate_r16(recovery: RecoverySummary) -> ValidationResult:
    """R16: Inventory Balanced.

    total_stock_pieces == depleted + available.
    """
    inv = recovery.inventory
    total = inv.total_stock_pieces
    depleted = inv.depleted_stock_pieces
    available = inv.available_stock_pieces

    if total == depleted + available:
        return ValidationResult(
            rule_id="R16",
            description="Inventory Balanced",
            status="PASS",
            detail=f"Total={total}, Depleted={depleted}, Available={available}",
        )

    return ValidationResult(
        rule_id="R16",
        description="Inventory Balanced",
        status="FAIL",
        detail=f"Total={total} != Depleted({depleted}) + Available({available})",
    )


def _validate_r17(recovery: RecoverySummary) -> ValidationResult:
    """R17: Dead Scrap Accounted.

    Sum by origin (REDUCTION + POST_CONSUMPTION + TRIM_WASTE) == total.
    """
    inv = recovery.inventory
    by_origin: dict[str, int] = {}
    for ds in inv.dead_scrap_pieces:
        by_origin[ds.origin] = by_origin.get(ds.origin, 0) + 1

    origin_sum = sum(by_origin.values())
    total = inv.total_dead_scrap_pieces

    if origin_sum == total:
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_origin.items()))
        return ValidationResult(
            rule_id="R17",
            description="Dead Scrap Accounted",
            status="PASS",
            detail=f"Total={total} ({breakdown})",
        )

    return ValidationResult(
        rule_id="R17",
        description="Dead Scrap Accounted",
        status="FAIL",
        detail=f"Origin sum={origin_sum} != Total={total}",
    )


def _validate_r18(
    recovery: RecoverySummary, project_summary: ProjectSummary
) -> ValidationResult:
    """R18: Frozen KPI Unchanged.

    Phase-3 frozen_yield must equal Phase-1/Phase-2 yield_percent (bit-exact).
    """
    frozen = recovery.frozen_yield
    expected = project_summary.yield_percent

    if frozen == expected:
        return ValidationResult(
            rule_id="R18",
            description="Frozen KPI Unchanged",
            status="PASS",
            detail=f"Frozen Yield = {frozen}%",
        )

    return ValidationResult(
        rule_id="R18",
        description="Frozen KPI Unchanged",
        status="FAIL",
        detail=f"Frozen Yield {frozen}% != Expected {expected}%",
    )


def _validate_r19(recovery: RecoverySummary) -> ValidationResult:
    """R19: MCK 3-Field Validation.

    Every match must have all 3 MCK fields non-zero.
    A match with any field == 0 is invalid (fail-closed on missing depth).
    """
    violations = []
    for m in recovery.matches:
        pitch, depth, thickness = m.mck
        zero_fields = []
        if pitch == 0.0:
            zero_fields.append("pitch")
        if depth == 0.0:
            zero_fields.append("depth")
        if thickness == 0.0:
            zero_fields.append("thickness")
        if zero_fields:
            violations.append(f"{m.demand_mark}: MCK zero fields: {zero_fields}")

    if not violations:
        return ValidationResult(
            rule_id="R19",
            description="MCK 3-Field Validation",
            status="PASS",
            detail=f"{len(recovery.matches)} matches have complete MCK",
        )

    return ValidationResult(
        rule_id="R19",
        description="MCK 3-Field Validation",
        status="FAIL",
        detail="; ".join(violations),
    )


def _validate_r20(recovery: RecoverySummary) -> ValidationResult:
    """R20: Post Consumption Classification Validation.

    Every consumption event must have exactly one classification result
    (REUSABLE, DEAD_SCRAP, or EXACT_FIT) consistent with remaining dimensions.
    """
    valid_classes = {"REUSABLE", "DEAD_SCRAP", "EXACT_FIT"}
    violations = []

    for sp in recovery.inventory.stock_pieces:
        for i, c in enumerate(sp.consumption_log):
            if c.post_classification not in valid_classes:
                violations.append(
                    f"{sp.piece_id} consumption #{i+1}: "
                    f"invalid classification '{c.post_classification}'"
                )
                continue

            expected = classify_remainder(c.width_after, sp.length)
            if c.post_classification != expected:
                violations.append(
                    f"{sp.piece_id} consumption #{i+1}: "
                    f"classification '{c.post_classification}' inconsistent with "
                    f"remaining {c.width_after}mm x {sp.length}mm "
                    f"(expected '{expected}')"
                )

    total_consumptions = sum(
        len(sp.consumption_log) for sp in recovery.inventory.stock_pieces
    )

    if not violations:
        return ValidationResult(
            rule_id="R20",
            description="Post Consumption Classification",
            status="PASS",
            detail=f"{total_consumptions} consumption events validated",
        )

    return ValidationResult(
        rule_id="R20",
        description="Post Consumption Classification",
        status="FAIL",
        detail="; ".join(violations),
    )


def _validate_r21(recovery: RecoverySummary) -> ValidationResult:
    """R21: Recovery Bounds (TD-006).

    Recovered Area must never exceed Total Expansion Demand Area.
    """
    recovered = recovery.recovered_area_m2
    demand = recovery.total_expansion_demand_m2

    if recovered <= demand:
        return ValidationResult(
            rule_id="R21",
            description="Recovery Bounds",
            status="PASS",
            detail=f"Recovered={recovered} <= Demand={demand}",
        )

    return ValidationResult(
        rule_id="R21",
        description="Recovery Bounds",
        status="FAIL",
        detail=f"Recovered={recovered} > Demand={demand} (over-recovery)",
    )
