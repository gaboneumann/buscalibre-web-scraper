"""
CSV data export module for writing scraped product data.
"""

import csv
from typing import List, Dict


def write_csv(path: str, data: List[Dict]) -> None:
    """
    Write scraped product data to CSV file.

    Args:
        path: Output file path
        data: List of product dictionaries to export

    Raises:
        ValueError: If data list is empty
    """
    if not data:
        raise ValueError("No data to export in CSV")

    fieldnames = [
        "title",
        "author",
        "price",
        "stock",
        "page_index",
        "product_url",
        "source",
    ]

    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in data:
            writer.writerow({key: row.get(key) for key in fieldnames})
