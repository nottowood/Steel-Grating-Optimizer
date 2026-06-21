"""Phase-3 Material Recovery Engine — Data Models.

Defines all data structures for stock piece tracking, scrap inventory,
recovery matching, and recovery KPIs. These models are additive to the
frozen Phase-1/Phase-2 data model and do not modify any existing classes.

Reference: DBD_PHASE3_REV0.3, Sections 4-6, 8-9, 12
"""

from dataclasses import dataclass, field


@dataclass
class ConsumptionRecord:
    """Records one consumption event against a stock piece."""

    consumed_by_mark: str
    width_consumed: float
    width_before: float
    width_after: float
    qty_consumed: int
    purpose: str  # EXPANSION_MATCH
    post_classification: str  # REUSABLE | DEAD_SCRAP | EXACT_FIT


@dataclass
class StockPiece:
    """A reusable reduction strip that enters inventory as consumable material.

    Width is consumed incrementally. After each consumption, the remainder
    is reclassified via Post Consumption Classification (DBD Section 5).
    """

    piece_id: str  # SP-{mark}-{seq}
    source_mark: str
    source_product_code: str
    load_bar_pitch: float  # MCK field 1
    load_bar_depth: float  # MCK field 2
    load_bar_thickness: float  # MCK field 3
    original_width: float
    remaining_width: float
    length: float
    original_area_m2: float
    remaining_area_m2: float
    qty: int
    status: str  # AVAILABLE | DEPLETED
    consumption_log: list[ConsumptionRecord] = field(default_factory=list)

    @property
    def mck(self) -> tuple[float, float, float]:
        """Manufacturing Compatibility Key — 3-field tuple (pitch, depth, thickness)."""
        return (self.load_bar_pitch, self.load_bar_depth, self.load_bar_thickness)


@dataclass
class DeadScrapPiece:
    """A piece of material that cannot be recovered."""

    scrap_id: str  # DS-{mark}-{seq}
    source_mark: str
    source_product_code: str
    width: float
    length: float
    area_m2: float
    qty: int
    origin: str  # REDUCTION | TRIM_WASTE | POST_CONSUMPTION
    reason: str


@dataclass
class RecoveryMatch:
    """Records one recovery match between a stock piece and an expansion demand."""

    demand_mark: str
    demand_product_code: str
    expansion_width: float
    demand_length: float
    demand_qty: int
    stock_piece_id: str
    source_mark: str
    stock_original_width: float
    stock_width_before: float
    stock_width_after: float
    trim_waste: float
    trim_classification: str  # REUSABLE | DEAD_SCRAP | EXACT_FIT
    post_consumption_class: str  # REUSABLE | DEAD_SCRAP | EXACT_FIT
    candidate_count: int
    decision_reason: str
    mck: tuple[float, float, float]
    rejection_log: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ScrapInventory:
    """Complete inventory of all waste material in a project."""

    project_name: str
    total_reduction_marks: int
    total_reduction_panels: int
    total_expansion_marks: int
    total_expansion_panels: int

    stock_pieces: list[StockPiece] = field(default_factory=list)
    dead_scrap_pieces: list[DeadScrapPiece] = field(default_factory=list)

    total_stock_pieces: int = 0
    available_stock_pieces: int = 0
    depleted_stock_pieces: int = 0
    total_stock_area_m2: float = 0.0
    remaining_stock_area_m2: float = 0.0

    total_dead_scrap_pieces: int = 0
    total_dead_scrap_area_m2: float = 0.0

    total_waste_area_m2: float = 0.0
    total_recovered_area_m2: float = 0.0


@dataclass
class RecoverySummary:
    """Complete Phase-3 recovery results — inventory, matches, and KPIs."""

    inventory: ScrapInventory

    matches: list[RecoveryMatch] = field(default_factory=list)
    unmatched_demands: list[dict] = field(default_factory=list)

    total_reduction_area_m2: float = 0.0
    total_expansion_demand_m2: float = 0.0
    recovered_area_m2: float = 0.0
    unrecovered_area_m2: float = 0.0
    recovery_rate: float = 0.0
    stock_utilization_rate: float = 0.0
    dead_scrap_area_m2: float = 0.0
    remaining_stock_area_m2: float = 0.0
    material_recovery_score: float = 0.0

    frozen_yield: float = 0.0


# --- Constants (from DBD Section 6, rule_engine.py frozen values) ---

REUSABLE_MIN_WIDTH = 200.0  # mm
REUSABLE_MIN_LENGTH = 200.0  # mm
REUSABLE_MIN_AREA = 0.20  # m²


def classify_remainder(width: float, length: float) -> str:
    """Classify a piece remainder per Post Consumption Classification rules.

    Returns: "REUSABLE", "DEAD_SCRAP", or "EXACT_FIT"
    """
    if width == 0:
        return "EXACT_FIT"
    area = (width / 1000) * (length / 1000)
    if width > REUSABLE_MIN_WIDTH and length > REUSABLE_MIN_LENGTH and area >= REUSABLE_MIN_AREA:
        return "REUSABLE"
    return "DEAD_SCRAP"
