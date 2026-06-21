"""Phase-2 optimization models for project-level pattern optimization."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StartCluster:
    cluster_id: int
    center: float
    low: float
    high: float
    member_starts: list[float] = field(default_factory=list)

    def contains(self, start_length: float) -> bool:
        return self.low <= start_length <= self.high


@dataclass
class CandidateScenario:
    representative_start: float
    cluster: Optional[StartCluster] = None
    matching_marks: list[str] = field(default_factory=list)
    non_matching_marks: list[str] = field(default_factory=list)
    coverage_qty: int = 0
    total_qty: int = 0
    coverage_percent: float = 0.0
    coverage_marks: int = 0
    total_marks: int = 0
    is_preferred: bool = False
    avg_rod_qty: float = 0.0
    yield_individual: float = 0.0
    yield_optimized: float = 0.0
    yield_difference: float = 0.0
    fallback_count: int = 0
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    selected: bool = False
    rejection_reason: str = ""


@dataclass
class PanelAssignment:
    mark: str
    product_code: str
    start_length: float
    rod_qty: int
    assignment_type: str = ""
    reason: str = ""


@dataclass
class FloorGroupResult:
    group_name: str
    common_start: float | None = None
    cluster: Optional[StartCluster] = None
    coverage_percent: float = 0.0
    coverage_qty: int = 0
    coverage_marks: int = 0
    total_qty: int = 0
    total_marks: int = 0
    common_start_marks: list[str] = field(default_factory=list)
    fallback_marks: list[str] = field(default_factory=list)
    is_preferred: bool = False
    consistency_status: str = ""
    assignments: list[PanelAssignment] = field(default_factory=list)
    all_scenarios: list[CandidateScenario] = field(default_factory=list)
    yield_individual: float = 0.0
    yield_optimized: float = 0.0
    yield_difference: float = 0.0


@dataclass
class OptimizationSummary:
    overall_consistency: float = 0.0
    yield_individual: float = 0.0
    yield_optimized: float = 0.0
    yield_difference: float = 0.0
    total_floor_groups: int = 0
    total_fallback_groups: int = 0
    total_coverage_panels: int = 0
    total_panels: int = 0
    total_coverage_marks: int = 0
    total_marks: int = 0
    total_fallback_panels: int = 0
    fallback_rate: float = 0.0
    optimization_mode: str = "COMMON START"
    floor_groups: list[FloorGroupResult] = field(default_factory=list)
