"""Phase-3.2A Production Cutting Plan Engine — Data Models.

Data classes and constants for cutting stock optimization.
Thresholds are independent from width-direction recovery (rule_engine.py).

Reference: DBD_PHASE3.2_REV0.4, Sections 3.1.5-3.1.7, 4
"""

from dataclasses import dataclass, field

PACKING_REUSABLE_MIN_LENGTH: float = 200.0
PACKING_REUSABLE_MIN_AREA: float = 0.20
ALGORITHM_ID: str = "FFD"


@dataclass
class CutPlanEntry:
    mark: str
    product_code: str
    fabricated_length: float
    qty: int
    note: str = ""


@dataclass
class ExcludedPanel:
    mark: str
    product_code: str
    fabricated_width: float
    fabricated_length: float
    standard_width: float
    qty: int
    reason: str
    expansion_width: float = 0.0
    reduction_width: float = 0.0


@dataclass
class CutPlan:
    bin_id: str
    stock_width: float
    stock_length: float
    mck: tuple[float, float, float]
    entries: list[CutPlanEntry] = field(default_factory=list)
    total_panels: int = 0
    total_used: float = 0.0
    remnant_length: float = 0.0
    remnant_classification: str = ""
    remnant_area_m2: float = 0.0


@dataclass
class LengthRemnant:
    remnant_id: str
    bin_id: str
    stock_width: float
    remnant_length: float
    remnant_area_m2: float
    classification: str
    mck: tuple[float, float, float]


@dataclass
class PackingSummary:
    total_bins: int = 0
    total_items_packed: int = 0
    total_marks_packed: int = 0
    stock_lengths_before: int = 0
    stock_lengths_after: int = 0
    stock_savings: int = 0
    stock_savings_percent: float = 0.0
    stock_utilization_rate: float = 0.0
    total_raw_material_area_m2: float = 0.0
    total_product_area_m2: float = 0.0
    total_waste_area_m2: float = 0.0
    total_kerf_loss_m2: float = 0.0
    total_reusable_remnant_area_m2: float = 0.0
    total_length_waste_m2: float = 0.0
    total_exact_fit_bins: int = 0
    algorithm: str = ALGORITHM_ID
    cut_plans: list[CutPlan] = field(default_factory=list)
    length_remnants: list[LengthRemnant] = field(default_factory=list)
    excluded_panels: list[ExcludedPanel] = field(default_factory=list)


def classify_length_remnant(remnant_length: float, stock_width: float) -> str:
    """Classify a length remnant into one of three tiers.

    Uses PACKING thresholds (independent from width recovery).
    """
    if remnant_length == 0.0:
        return "EXACT_FIT"
    area_m2 = (remnant_length / 1000.0) * (stock_width / 1000.0)
    if remnant_length >= PACKING_REUSABLE_MIN_LENGTH and area_m2 >= PACKING_REUSABLE_MIN_AREA:
        return "REUSABLE_REMNANT"
    return "LENGTH_WASTE"
