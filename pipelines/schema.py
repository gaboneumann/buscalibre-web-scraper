"""CSV schema validation and checkpoint management."""
import csv
import os
from typing import Set, Dict, List


class CSVSchema:
    """Validates and prepares product data for CSV export."""

    def __init__(self):
        """Initialize schema with required field names."""
        self._fields = ["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]

    @property
    def fields(self) -> List[str]:
        """Return list of required field names in order."""
        return self._fields

    def validate(self, data: Dict) -> bool:
        """
        Validate that parsed data contains all required fields.

        Args:
            data: Dictionary with product data.

        Returns:
            True if all required fields present, False otherwise.
        """
        if not isinstance(data, dict):
            return False
        for field in self._fields:
            if field not in data:
                return False
        return True

    def prepare_for_csv(self, data: Dict) -> Dict:
        """
        Prepare data for CSV export by filtering to schema fields and preserving order.

        Args:
            data: Raw parsed product data (may have extra fields).

        Returns:
            Dictionary with only schema fields in correct order.
        """
        result = {}
        for field in self._fields:
            if field in data:
                result[field] = data[field]
        return result


class CheckpointManager:
    """Manages CSV checkpoint reads/writes for resume capability."""

    def __init__(self, output_path: str, category_url: str = ""):
        """
        Initialize checkpoint manager.

        Args:
            output_path: Path to CSV file for storing product records.
            category_url: Category URL for filtering checkpoint data by category.
        """
        self.output_path = output_path
        self.category_url = category_url
        self.fieldnames = CSVSchema().fields

    def get_scraped_urls(self) -> Set[str]:
        """
        Load already-scraped product URLs from CSV checkpoint, filtered by category.

        Only returns URLs where category_url matches the current category.
        Rows without category_url are ignored (retrocompat: old CSVs).

        Returns:
            Set of product URLs already processed for this category.
        """
        scraped_urls = set()
        if not os.path.isfile(self.output_path):
            return scraped_urls

        try:
            with open(self.output_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("category_url", "") == self.category_url:
                        url = row.get("product_url")
                        if url:
                            scraped_urls.add(url.strip())
        except Exception as e:
            print(f"⚠️ WARNING: Could not read checkpoint file: {e}")
        return scraped_urls

    def save_record(self, record: Dict) -> None:
        """
        Write a single product record to CSV immediately (append mode).
        Automatically adds category_url to record.

        Args:
            record: Dictionary with product data to save.
        """
        record["category_url"] = self.category_url
        file_exists = os.path.isfile(self.output_path)
        target_dir = os.path.dirname(self.output_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        with open(self.output_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
