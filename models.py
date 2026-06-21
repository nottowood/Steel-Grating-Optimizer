"""Domain models for Steel Grating Optimizer."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductMaster:
    series: int
    product_type: str
    load_bar_pitch: float
    load_bar_count: int
    cross_bar_pitch: float
    front_length: float
    load_bar_thickness: float
    standard_width: float

    @property
    def type_code(self) -> str:
        return f"T{self.product_type}"


@dataclass
class Pattern:
    rod_qty: int
    mid_length: float
    start_length: float
    end_length: float
    score: int = 0
    rank: int = 0
    selection_reason: str = ""

    @property
    def is_preferred(self) -> bool:
        return 40.0 <= self.start_length <= 45.0


@dataclass
class FabricatedPanel:
    mark: str
    product_code: str
    fabricated_width: float
    fabricated_length: float
    qty: int
    series: int = 0
    product_type: str = ""
    standard_width: float = 0.0
    load_bar_thickness: float = 0.0
    cross_bar_pitch: float = 0.0
    cut_length: float = 0.0
    expansion_width: float = 0.0
    reduction_width: float = 0.0
    needs_expansion: bool = False
    needs_reduction: bool = False
    pattern: Optional[Pattern] = None
    all_patterns: list = field(default_factory=list)

    @property
    def sold_area_m2(self) -> float:
        """Sold Area = Fab Width x Fab Length x Qty."""
        return (self.fabricated_width / 1000) * (self.fabricated_length / 1000) * self.qty

    @property
    def production_area_m2(self) -> float:
        """Production Area = Fab Width x Fab Length x Qty."""
        return (self.fabricated_width / 1000) * (self.fabricated_length / 1000) * self.qty

    @property
    def standard_width_used(self) -> float:
        """Standard width of stock material used.

        Normal/Reduction: standard_width
        Expansion: standard_width + expansion_width
        """
        if self.needs_expansion:
            return self.standard_width + self.expansion_width
        return self.standard_width

    @property
    def raw_material_area_m2(self) -> float:
        """Raw Material Area = Standard Width Used x Fab Length x Qty."""
        return (self.standard_width_used / 1000) * (self.fabricated_length / 1000) * self.qty


@dataclass
class ScrapPiece:
    width: float
    length: float
    area_m2: float
    is_reusable: bool


@dataclass
class ProjectSummary:
    total_sold_area: float = 0.0
    total_production_area: float = 0.0
    total_raw_material_area: float = 0.0
    yield_percent: float = 0.0
    scrap_percent: float = 0.0
    total_panels: int = 0
    expansion_count: int = 0
    reduction_count: int = 0
    total_expansion_width: float = 0.0
    total_reduction_width: float = 0.0
