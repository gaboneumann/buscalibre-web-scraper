"""CSV schema validation and checkpoint management."""
import csv
import logging
import os
from typing import Set, Dict, List

logger = logging.getLogger(__name__)


class CSVSchema:
    """Validates and prepares product data for CSV export."""

    def __init__(self):
        """Initialize schema with required field names."""
        self._fields = ["title", "author", "price", "stock", "page_index", "product_url"]

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

    def __init__(self, output_path: str):
        """
        Initialize checkpoint manager.

        Args:
            output_path: Path to CSV file for storing product records.
        """
        self.output_path = output_path
        self.fieldnames = CSVSchema().fields

    def get_scraped_urls(self) -> Set[str]:
        """
        Load already-scraped product URLs from CSV checkpoint.

        Returns:
            Set of all product URLs previously written to the output CSV.
        """
        scraped_urls = set()
        if not os.path.isfile(self.output_path):
            return scraped_urls

        try:
            with open(self.output_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("product_url")
                    if url:
                        scraped_urls.add(url.strip())
        except Exception as e:
            logger.warning("Could not read checkpoint file: %s", e)
        return scraped_urls

    def save_record(self, record: Dict) -> None:
        """
        Write a single product record to CSV immediately (append mode).

        Args:
            record: Dictionary with product data to save.
        """
        file_exists = os.path.isfile(self.output_path)
        target_dir = os.path.dirname(self.output_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        with open(self.output_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
