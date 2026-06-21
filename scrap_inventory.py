"""Phase-3 Scrap Inventory Management.

Builds and manages the scrap inventory from processed panels:
- Classifies reduction strips into Stock Pieces or Dead Scrap
- Manages stock piece consumption with Post Consumption Classification
- Tracks inventory state (AVAILABLE / DEPLETED)

No matching logic — that belongs in recovery_engine.py.
No UI integration — that belongs in recovery_report.py.

Reference: DBD_PHASE3_REV0.3, Sections 5-6
"""

from models import FabricatedPanel
from product_master import ProductMaster
from recovery_models import (
    StockPiece,
    DeadScrapPiece,
    ConsumptionRecord,
    ScrapInventory,
    classify_remainder,
    REUSABLE_MIN_WIDTH,
)


def build_inventory(
    panels: list[FabricatedPanel],
    catalog: dict[str, ProductMaster],
    depth_map: dict[str, float] | None = None,
) -> ScrapInventory:
    """Build scrap inventory from processed panels.

    Scans all panels for reduction strips and classifies each as
    StockPiece (AVAILABLE) or DeadScrapPiece.

    Args:
        panels: Processed panels from Phase-1/Phase-2 (read-only).
        catalog: Product catalog for looking up load_bar_pitch.
        depth_map: Product code → load_bar_depth mapping.
                   If None, defaults all depths to 0.0 (will fail MCK validation
                   per DBD R19 fail-closed rule until depth data is populated).
    """
    if depth_map is None:
        depth_map = {}

    stock_pieces: list[StockPiece] = []
    dead_scrap_pieces: list[DeadScrapPiece] = []
    sp_seq = 0
    ds_seq = 0

    reduction_marks = 0
    reduction_panels = 0
    expansion_marks = 0
    expansion_panels = 0

    for panel in panels:
        if panel.needs_expansion:
            expansion_marks += 1
            expansion_panels += panel.qty

        if not panel.needs_reduction:
            continue

        reduction_marks += 1
        reduction_panels += panel.qty

        width = panel.reduction_width
        length = panel.fabricated_length
        area_m2 = round((width / 1000) * (length / 1000), 4)

        product = catalog.get(panel.product_code)
        pitch = product.load_bar_pitch if product else 0.0
        depth = depth_map.get(panel.product_code, 0.0)
        thickness = panel.load_bar_thickness

        classification = classify_remainder(width, length)

        if classification == "REUSABLE":
            sp_seq += 1
            piece = StockPiece(
                piece_id=f"SP-{panel.mark}-{sp_seq:03d}",
                source_mark=panel.mark,
                source_product_code=panel.product_code,
                load_bar_pitch=pitch,
                load_bar_depth=depth,
                load_bar_thickness=thickness,
                original_width=width,
                remaining_width=width,
                length=length,
                original_area_m2=area_m2,
                remaining_area_m2=area_m2,
                qty=panel.qty,
                status="AVAILABLE",
            )
            stock_pieces.append(piece)
        else:
            ds_seq += 1
            reason = _build_dead_scrap_reason(width, length)
            scrap = DeadScrapPiece(
                scrap_id=f"DS-{panel.mark}-{ds_seq:03d}",
                source_mark=panel.mark,
                source_product_code=panel.product_code,
                width=width,
                length=length,
                area_m2=area_m2,
                qty=panel.qty,
                origin="REDUCTION",
                reason=reason,
            )
            dead_scrap_pieces.append(scrap)

    inventory = ScrapInventory(
        project_name="",
        total_reduction_marks=reduction_marks,
        total_reduction_panels=reduction_panels,
        total_expansion_marks=expansion_marks,
        total_expansion_panels=expansion_panels,
        stock_pieces=stock_pieces,
        dead_scrap_pieces=dead_scrap_pieces,
    )
    update_inventory_stats(inventory)
    return inventory


def consume_stock_piece(
    piece: StockPiece,
    width_consumed: float,
    consumed_by_mark: str,
    qty_consumed: int,
    inventory: ScrapInventory,
) -> str:
    """Consume width from a stock piece and run Post Consumption Classification.

    Args:
        piece: The stock piece to consume from.
        width_consumed: Width to deduct (mm).
        consumed_by_mark: Mark of the panel consuming this piece.
        qty_consumed: Number of identical pieces consumed.
        inventory: The parent inventory (for adding dead scrap if needed).

    Returns:
        Post Consumption Classification result: "REUSABLE", "DEAD_SCRAP", or "EXACT_FIT"
    """
    width_before = piece.remaining_width
    width_after = round(width_before - width_consumed, 2)

    classification = classify_remainder(width_after, piece.length)

    record = ConsumptionRecord(
        consumed_by_mark=consumed_by_mark,
        width_consumed=width_consumed,
        width_before=width_before,
        width_after=width_after,
        qty_consumed=qty_consumed,
        purpose="EXPANSION_MATCH",
        post_classification=classification,
    )
    piece.consumption_log.append(record)

    piece.remaining_width = width_after
    piece.remaining_area_m2 = round((width_after / 1000) * (piece.length / 1000), 4)

    if classification == "REUSABLE":
        pass  # stays AVAILABLE
    elif classification == "EXACT_FIT":
        piece.status = "DEPLETED"
    else:
        # DEAD_SCRAP — deplete piece and create dead scrap record
        piece.status = "DEPLETED"
        ds_seq = len(inventory.dead_scrap_pieces) + 1
        scrap = DeadScrapPiece(
            scrap_id=f"DS-{piece.source_mark}-T{ds_seq:03d}",
            source_mark=piece.source_mark,
            source_product_code=piece.source_product_code,
            width=width_after,
            length=piece.length,
            area_m2=round((width_after / 1000) * (piece.length / 1000), 4),
            qty=piece.qty,
            origin="POST_CONSUMPTION",
            reason=f"Post-consumption remainder {width_after:.0f}mm < {REUSABLE_MIN_WIDTH:.0f}mm minimum",
        )
        inventory.dead_scrap_pieces.append(scrap)

    return classification


def update_inventory_stats(inventory: ScrapInventory) -> None:
    """Recalculate all summary statistics on the inventory."""
    inventory.total_stock_pieces = len(inventory.stock_pieces)
    inventory.available_stock_pieces = sum(
        1 for sp in inventory.stock_pieces if sp.status == "AVAILABLE"
    )
    inventory.depleted_stock_pieces = sum(
        1 for sp in inventory.stock_pieces if sp.status == "DEPLETED"
    )
    inventory.total_stock_area_m2 = round(
        sum(sp.original_area_m2 * sp.qty for sp in inventory.stock_pieces), 4
    )
    inventory.remaining_stock_area_m2 = round(
        sum(
            sp.remaining_area_m2 * sp.qty
            for sp in inventory.stock_pieces
            if sp.status == "AVAILABLE"
        ),
        4,
    )

    inventory.total_dead_scrap_pieces = len(inventory.dead_scrap_pieces)
    inventory.total_dead_scrap_area_m2 = round(
        sum(ds.area_m2 * ds.qty for ds in inventory.dead_scrap_pieces), 4
    )

    inventory.total_waste_area_m2 = round(
        inventory.total_dead_scrap_area_m2 + inventory.remaining_stock_area_m2, 4
    )


def _build_dead_scrap_reason(width: float, length: float) -> str:
    """Build human-readable reason for dead scrap classification."""
    area = (width / 1000) * (length / 1000)
    reasons = []
    if width <= REUSABLE_MIN_WIDTH:
        reasons.append(f"Width {width:.0f}mm <= {REUSABLE_MIN_WIDTH:.0f}mm")
    if length <= 200.0:
        reasons.append(f"Length {length:.0f}mm <= 200mm")
    if area < 0.20:
        reasons.append(f"Area {area:.4f}m² < 0.20m²")
    return "; ".join(reasons) if reasons else "Below reusability threshold"
