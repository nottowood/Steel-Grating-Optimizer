"""Rule Engine for Steel Grating Optimizer.

Applies manufacturing rules to fabricated panels:
- Cut length calculation
- Expansion detection
- Scrap classification
- Production area calculation
"""

from models import FabricatedPanel, ScrapPiece, ProjectSummary
from product_master import ProductMaster

STOCK_LENGTH = 6000.0
SAW_KERF = 6.0
REUSABLE_MIN_WIDTH = 200.0
REUSABLE_MIN_AREA = 0.2


def calculate_cut_length(fabricated_length: float, load_bar_thickness: float) -> float:
    """Calculate cut length by removing banding on both ends.

    Cut Length = Fabricated Length - (2 × Load Bar Thickness)
    """
    return fabricated_length - (2 * load_bar_thickness)


def check_expansion(fabricated_width: float, standard_width: float) -> tuple[bool, float]:
    """Check if panel requires expansion strip.

    Returns (needs_expansion, expansion_width).
    """
    if fabricated_width > standard_width:
        return True, round(fabricated_width - standard_width, 2)
    return False, 0.0


def check_reduction(fabricated_width: float, standard_width: float) -> tuple[bool, float]:
    """Check if panel is narrower than standard width.

    Returns (needs_reduction, reduction_width).
    Reduction Width = Standard Width - Fabricated Width
    """
    if fabricated_width < standard_width:
        return True, round(standard_width - fabricated_width, 2)
    return False, 0.0


def classify_scrap(width: float, length: float) -> ScrapPiece:
    """Classify scrap as reusable or dead based on size rules.

    Reusable: width > 200 mm AND area >= 0.2 m²
    """
    area_m2 = (width / 1000) * (length / 1000)
    is_reusable = width > REUSABLE_MIN_WIDTH and area_m2 >= REUSABLE_MIN_AREA
    return ScrapPiece(
        width=width,
        length=length,
        area_m2=round(area_m2, 4),
        is_reusable=is_reusable,
    )


def apply_rules(panel: FabricatedPanel, product: ProductMaster) -> FabricatedPanel:
    """Apply all manufacturing rules to a fabricated panel."""
    panel.series = product.series
    panel.product_type = product.product_type
    panel.standard_width = product.standard_width
    panel.load_bar_thickness = product.load_bar_thickness
    panel.cross_bar_pitch = product.cross_bar_pitch
    panel.cut_length = calculate_cut_length(panel.fabricated_length, product.load_bar_thickness)
    panel.needs_expansion, panel.expansion_width = check_expansion(
        panel.fabricated_width, product.standard_width
    )
    panel.needs_reduction, panel.reduction_width = check_reduction(
        panel.fabricated_width, product.standard_width
    )
    return panel


def calculate_summary(panels: list[FabricatedPanel]) -> ProjectSummary:
    """Calculate project-level KPI summary.

    Sold Area          = Fab Width x Fab Length x Qty
    Production Area    = Fab Width x Fab Length x Qty
    Raw Material Area  = Standard Width Used x Fab Length x Qty
    Yield              = Sold Area / Raw Material Area
    Scrap              = 1 - Yield
    """
    summary = ProjectSummary()
    summary.total_panels = sum(p.qty for p in panels)

    for panel in panels:
        summary.total_sold_area += panel.sold_area_m2
        summary.total_production_area += panel.production_area_m2
        summary.total_raw_material_area += panel.raw_material_area_m2
        if panel.needs_expansion:
            summary.expansion_count += panel.qty
            summary.total_expansion_width += panel.expansion_width * panel.qty
        if panel.needs_reduction:
            summary.reduction_count += panel.qty
            summary.total_reduction_width += panel.reduction_width * panel.qty

    summary.total_sold_area = round(summary.total_sold_area, 4)
    summary.total_production_area = round(summary.total_production_area, 4)
    summary.total_raw_material_area = round(summary.total_raw_material_area, 4)
    summary.total_expansion_width = round(summary.total_expansion_width, 2)
    summary.total_reduction_width = round(summary.total_reduction_width, 2)

    if summary.total_raw_material_area > 0:
        summary.yield_percent = round(
            (summary.total_sold_area / summary.total_raw_material_area) * 100, 2
        )
        summary.scrap_percent = round(100 - summary.yield_percent, 2)
    return summary
