"""CSV Importer for Steel Grating Optimizer.

Reads fabricated panel data from CSV files in the format:
Mark, Product, Width, Length, Qty
"""

import csv
import io

import pandas as pd

from models import FabricatedPanel


def parse_csv(file_content: str) -> list[FabricatedPanel]:
    """Parse CSV content into a list of FabricatedPanel objects.

    Expected columns: Mark, Product, Width, Length, Qty
    """
    panels = []
    reader = csv.DictReader(io.StringIO(file_content))

    for row in reader:
        try:
            panel = FabricatedPanel(
                mark=row["Mark"].strip(),
                product_code=row["Product"].strip(),
                fabricated_width=float(row["Width"]),
                fabricated_length=float(row["Length"]),
                qty=int(row["Qty"]),
            )
            panels.append(panel)
        except (KeyError, ValueError):
            continue
    return panels


def parse_csv_dataframe(df: pd.DataFrame) -> list[FabricatedPanel]:
    """Parse a pandas DataFrame into a list of FabricatedPanel objects."""
    panels = []
    required_cols = {"Mark", "Product", "Width", "Length", "Qty"}

    df.columns = df.columns.str.strip()
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing columns: {missing}")

    for _, row in df.iterrows():
        try:
            panel = FabricatedPanel(
                mark=str(row["Mark"]).strip(),
                product_code=str(row["Product"]).strip(),
                fabricated_width=float(row["Width"]),
                fabricated_length=float(row["Length"]),
                qty=int(row["Qty"]),
            )
            panels.append(panel)
        except (KeyError, ValueError):
            continue
    return panels
