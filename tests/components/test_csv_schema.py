"""Unit tests for CSVSchema."""
import pytest
from pipelines.schema import CSVSchema

EXPECTED_FIELDS = ["title", "author", "price", "stock", "page_index", "product_url"]


class TestCSVSchemaValidation:
    """Test CSVSchema validation logic."""

    def test_validate_passes_on_complete_record(self):
        """validate() returns True when all required fields present."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is True

    def test_validate_fails_on_missing_title(self):
        """validate() returns False when title is missing."""
        schema = CSVSchema()
        data = {
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_author(self):
        """validate() returns False when author is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_price(self):
        """validate() returns False when price is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_stock(self):
        """validate() returns False when stock is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_page_index(self):
        """validate() returns False when page_index is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_product_url(self):
        """validate() returns False when product_url is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
        }
        assert schema.validate(data) is False

    def test_validate_source_not_required(self):
        """validate() returns True when source field is absent (removed from schema)."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is True

    def test_validate_with_extra_fields(self):
        """validate() returns True when extra fields present (not in schema)."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "extra_field": "ignored",
        }
        assert schema.validate(data) is True

    def test_validate_fields_property(self):
        """CSVSchema.fields returns exactly the 6-field target list."""
        schema = CSVSchema()
        assert schema.fields == EXPECTED_FIELDS
        assert len(schema.fields) == 6
        assert "source" not in schema.fields
        assert "category_url" not in schema.fields

    def test_prepare_for_csv_returns_dict(self):
        """prepare_for_csv() returns a dictionary with CSV-ready values."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        result = schema.prepare_for_csv(data)
        assert isinstance(result, dict)
        assert result["title"] == "Test Book"
        assert result["author"] == "Author Name"

    def test_prepare_for_csv_filters_to_schema_fields(self):
        """prepare_for_csv() only includes fields defined in schema."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": 1,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
            "category_url": "https://www.buscalibre.cl/libros/ficcion",
            "extra_field": "should_be_removed",
        }
        result = schema.prepare_for_csv(data)
        assert "extra_field" not in result
        assert "source" not in result
        assert "category_url" not in result
        assert len(result) == 6

    def test_prepare_for_csv_preserves_field_order(self):
        """prepare_for_csv() returns dict with fields in schema order."""
        schema = CSVSchema()
        data = {
            "product_url": "https://example.com/product/1",
            "page_index": 1,
            "stock": 1,
            "price": 100.00,
            "author": "Author Name",
            "title": "Test Book",
        }
        result = schema.prepare_for_csv(data)
        keys_list = list(result.keys())
        assert keys_list == EXPECTED_FIELDS
