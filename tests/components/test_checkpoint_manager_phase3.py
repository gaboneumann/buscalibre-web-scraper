"""Unit tests for CheckpointManager (Phase 3 finalization)."""
import pytest
import os
import csv
from unittest.mock import patch, mock_open
from pipelines.components import CheckpointManager
from pipelines.schema import CSVSchema

CATEGORY_URL = "https://www.buscalibre.cl/libros/ficcion"


class TestCheckpointManagerGetScrapedUrls:
    """Test CheckpointManager.get_scraped_urls() reads CSV correctly."""

    def test_get_scraped_urls_returns_empty_set_if_file_missing(self):
        """get_scraped_urls() returns empty set when CSV file does not exist."""
        mgr = CheckpointManager(output_path="/nonexistent/path.csv", category_url=CATEGORY_URL)
        result = mgr.get_scraped_urls()
        assert isinstance(result, set)
        assert len(result) == 0

    def test_get_scraped_urls_extracts_product_urls_from_csv(self, tmp_path):
        """get_scraped_urls() reads CSV and extracts product_url column."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
            )
            writer.writeheader()
            writer.writerow({
                "title": "Book 1",
                "author": "Author 1",
                "price": 100,
                "stock": True,
                "page_index": 1,
                "product_url": "https://example.com/product/1",
                "source": "test",
                "category_url": CATEGORY_URL,
            })
            writer.writerow({
                "title": "Book 2",
                "author": "Author 2",
                "price": 200,
                "stock": False,
                "page_index": 1,
                "product_url": "https://example.com/product/2",
                "source": "test",
                "category_url": CATEGORY_URL,
            })

        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)
        result = mgr.get_scraped_urls()
        assert "https://example.com/product/1" in result
        assert "https://example.com/product/2" in result
        assert len(result) == 2

    def test_get_scraped_urls_deduplicates_urls(self, tmp_path):
        """get_scraped_urls() returns deduplicated set even if CSV has duplicates."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
            )
            writer.writeheader()
            writer.writerow({
                "title": "Book 1",
                "author": "Author 1",
                "price": 100,
                "stock": True,
                "page_index": 1,
                "product_url": "https://example.com/product/1",
                "source": "test",
                "category_url": CATEGORY_URL,
            })
            writer.writerow({
                "title": "Book 1 (duplicate)",
                "author": "Author 1",
                "price": 100,
                "stock": True,
                "page_index": 2,
                "product_url": "https://example.com/product/1",
                "source": "test",
                "category_url": CATEGORY_URL,
            })

        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)
        result = mgr.get_scraped_urls()
        assert len(result) == 1
        assert "https://example.com/product/1" in result

    def test_get_scraped_urls_handles_whitespace(self, tmp_path):
        """get_scraped_urls() strips whitespace from URLs."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
            )
            writer.writeheader()
            writer.writerow({
                "title": "Book 1",
                "author": "Author 1",
                "price": 100,
                "stock": True,
                "page_index": 1,
                "product_url": "  https://example.com/product/1  ",
                "source": "test",
                "category_url": CATEGORY_URL,
            })

        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)
        result = mgr.get_scraped_urls()
        assert "https://example.com/product/1" in result
        assert len(result) == 1


class TestCheckpointManagerSaveRecord:
    """Test CheckpointManager.save_record() writes CSV correctly."""

    def test_save_record_creates_csv_with_header(self, tmp_path):
        """save_record() creates CSV file with header if missing."""
        csv_file = tmp_path / "new.csv"
        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)

        record = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 100,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "test",
        }
        mgr.save_record(record)

        assert csv_file.exists()
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["title"] == "Test Book"
            assert rows[0]["product_url"] == "https://example.com/product/1"
            assert rows[0]["category_url"] == CATEGORY_URL

    def test_save_record_appends_to_existing_csv(self, tmp_path):
        """save_record() appends to existing CSV without recreating header."""
        csv_file = tmp_path / "existing.csv"
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
            )
            writer.writeheader()
            writer.writerow({
                "title": "Existing Book",
                "author": "Existing Author",
                "price": 100,
                "stock": True,
                "page_index": 1,
                "product_url": "https://example.com/product/existing",
                "source": "test",
                "category_url": CATEGORY_URL,
            })

        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)
        new_record = {
            "title": "New Book",
            "author": "New Author",
            "price": 200,
            "stock": False,
            "page_index": 2,
            "product_url": "https://example.com/product/new",
            "source": "test",
        }
        mgr.save_record(new_record)

        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["title"] == "Existing Book"
            assert rows[1]["title"] == "New Book"

    def test_save_record_creates_parent_directory(self, tmp_path):
        """save_record() creates parent directories if missing."""
        csv_file = tmp_path / "nested" / "dir" / "output.csv"
        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)

        record = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 100,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "test",
        }
        mgr.save_record(record)

        assert csv_file.exists()
        assert csv_file.parent.exists()


class TestCheckpointManagerIntegration:
    """Integration tests for CheckpointManager CSV format compatibility."""

    def test_csv_output_format_matches_original(self, tmp_path):
        """CheckpointManager output CSV matches original category_pipeline format."""
        csv_file = tmp_path / "output.csv"
        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)

        records = [
            {
                "title": "Book 1",
                "author": "Author 1",
                "price": 100.50,
                "stock": True,
                "page_index": 1,
                "product_url": "https://example.com/product/1",
                "source": "buscalibre",
            },
            {
                "title": "Book 2",
                "author": "Author 2",
                "price": 200.75,
                "stock": False,
                "page_index": 2,
                "product_url": "https://example.com/product/2",
                "source": "buscalibre",
            },
        ]

        for record in records:
            mgr.save_record(record)

        # Verify CSV format
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames
            expected_header = ["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
            assert header == expected_header

            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["title"] == "Book 1"
            assert rows[1]["title"] == "Book 2"

    def test_checkpoint_manager_uses_csv_schema_fields(self):
        """CheckpointManager.fieldnames matches CSVSchema().fields."""
        mgr = CheckpointManager(output_path="/tmp/test_cm.csv", category_url=CATEGORY_URL)
        assert mgr.fieldnames == CSVSchema().fields

    def test_get_and_save_round_trip(self, tmp_path):
        """Round-trip test: save records, read them back, verify match."""
        csv_file = tmp_path / "roundtrip.csv"
        mgr = CheckpointManager(output_path=str(csv_file), category_url=CATEGORY_URL)

        original_records = [
            {
                "title": "Book A",
                "author": "Author A",
                "price": 10.0,
                "stock": True,
                "page_index": 1,
                "product_url": "https://example.com/a",
                "source": "test",
            },
            {
                "title": "Book B",
                "author": "Author B",
                "price": 20.0,
                "stock": False,
                "page_index": 1,
                "product_url": "https://example.com/b",
                "source": "test",
            },
        ]

        # Save records
        for record in original_records:
            mgr.save_record(record)

        # Read back URLs
        scraped_urls = mgr.get_scraped_urls()
        assert scraped_urls == {"https://example.com/a", "https://example.com/b"}
