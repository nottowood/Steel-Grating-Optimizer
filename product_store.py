"""Product Store — persistence layer for custom and hidden products using JSON."""

import json
import os
from models import ProductMaster

STORE_PATH = os.path.join(os.path.dirname(__file__), "custom_products.json")
HIDDEN_PATH = os.path.join(os.path.dirname(__file__), "hidden_products.json")


def _serialize(product: ProductMaster) -> dict:
    return {
        "series": product.series,
        "product_type": product.product_type,
        "load_bar_pitch": product.load_bar_pitch,
        "load_bar_count": product.load_bar_count,
        "cross_bar_pitch": product.cross_bar_pitch,
        "front_length": product.front_length,
        "load_bar_thickness": product.load_bar_thickness,
        "standard_width": product.standard_width,
    }


def _deserialize(data: dict) -> ProductMaster:
    return ProductMaster(**data)


def load_custom_products() -> dict[str, ProductMaster]:
    """Load custom products from JSON file."""
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {code: _deserialize(d) for code, d in raw.items()}


def save_custom_products(products: dict[str, ProductMaster]) -> None:
    """Save custom products to JSON file."""
    raw = {code: _serialize(p) for code, p in products.items()}
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)


def add_custom_product(code: str, product: ProductMaster) -> None:
    """Add or update a single custom product."""
    products = load_custom_products()
    products[code] = product
    save_custom_products(products)


def delete_custom_product(code: str) -> bool:
    """Delete a custom product by code. Returns True if found and deleted."""
    products = load_custom_products()
    if code in products:
        del products[code]
        save_custom_products(products)
        return True
    return False


# --- Hidden products (for hiding standard products) ---

def load_hidden_codes() -> list[str]:
    """Load list of hidden product codes."""
    if not os.path.exists(HIDDEN_PATH):
        return []
    with open(HIDDEN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_hidden_codes(codes: list[str]) -> None:
    """Save list of hidden product codes."""
    with open(HIDDEN_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(set(codes)), f, indent=2, ensure_ascii=False)


def hide_product(code: str) -> None:
    """Hide a product (standard or custom)."""
    codes = load_hidden_codes()
    if code not in codes:
        codes.append(code)
        save_hidden_codes(codes)


def unhide_product(code: str) -> None:
    """Unhide a previously hidden product."""
    codes = load_hidden_codes()
    if code in codes:
        codes.remove(code)
        save_hidden_codes(codes)


def unhide_all() -> None:
    """Unhide all products."""
    save_hidden_codes([])
