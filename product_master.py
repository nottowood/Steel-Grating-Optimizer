"""Product Master module for Steel Grating Optimizer.

Defines all standard steel grating products with their manufacturing parameters.
"""

import re
from typing import Optional

from models import ProductMaster

SERIES_CONFIG = {
    1: {"load_bar_pitch": 30.0, "load_bar_count": 34},
    2: {"load_bar_pitch": 40.0, "load_bar_count": 26},
    3: {"load_bar_pitch": 60.0, "load_bar_count": 18},
}

TYPE_CONFIG = {
    "A": {"cross_bar_pitch": 100.0, "front_length": 50.0},
    "B": {"cross_bar_pitch": 50.0, "front_length": 25.0},
}

SUPPORTED_THICKNESSES = [20, 25, 30, 32, 35, 40, 45, 50]


def calculate_standard_width(load_bar_pitch: float, load_bar_count: int, thickness: float) -> float:
    """Calculate standard panel width from pitch, count, and bar thickness."""
    return load_bar_pitch * (load_bar_count - 1) + thickness


def build_product_catalog(include_custom: bool = True) -> dict[str, ProductMaster]:
    """Build the complete product catalog from series, type, and thickness combinations."""
    catalog = {}
    for series, s_cfg in SERIES_CONFIG.items():
        for ptype, t_cfg in TYPE_CONFIG.items():
            for thickness in SUPPORTED_THICKNESSES:
                code = f"T{ptype}{series}{thickness:02d}/{series}"
                std_width = calculate_standard_width(
                    s_cfg["load_bar_pitch"], s_cfg["load_bar_count"], thickness
                )
                product = ProductMaster(
                    series=series,
                    product_type=ptype,
                    load_bar_pitch=s_cfg["load_bar_pitch"],
                    load_bar_count=s_cfg["load_bar_count"],
                    cross_bar_pitch=t_cfg["cross_bar_pitch"],
                    front_length=t_cfg["front_length"],
                    load_bar_thickness=thickness,
                    standard_width=std_width,
                )
                catalog[code] = product

    if include_custom:
        from product_store import load_custom_products, load_hidden_codes
        catalog.update(load_custom_products())
        for code in load_hidden_codes():
            catalog.pop(code, None)

    return catalog


def parse_product_code(code: str) -> Optional[dict]:
    """Parse a product code like 'TA205/1' into series, type, and thickness.

    Format: T{type}{series}{thickness}/{series}
    Example: TA205 → type=A, series=2, thickness=05 (but typically TA230/1 etc.)
    Flexible parsing: TA1xx/1 or TA2xx/1 etc.
    """
    code = code.strip().upper()
    match = re.match(r"T([AB])(\d)(\d{2})/(\d)", code)
    if match:
        ptype = match.group(1)
        series = int(match.group(2))
        thickness = int(match.group(3))
        series_check = int(match.group(4))
        if series != series_check:
            return None
        if series not in SERIES_CONFIG:
            return None
        if ptype not in TYPE_CONFIG:
            return None
        return {
            "product_type": ptype,
            "series": series,
            "thickness": thickness,
        }
    return None


def lookup_product(code: str, catalog: dict[str, ProductMaster]) -> Optional[ProductMaster]:
    """Look up a product in the catalog by its code."""
    code = code.strip().upper()
    if code in catalog:
        return catalog[code]

    parsed = parse_product_code(code)
    if parsed:
        for key, product in catalog.items():
            if (
                product.product_type == parsed["product_type"]
                and product.series == parsed["series"]
                and product.load_bar_thickness == parsed["thickness"]
            ):
                return product
    return None
