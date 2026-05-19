"""Unit tests for CSVSchema."""
import pytest
from pipelines.schema import CSVSchema


class TestCSVSchemaValidation:
    """Test CSVSchema validation logic."""

    def test_validate_passes_on_complete_record(self):
        """validate() returns True when all required fields present."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
            "category_url": "https://www.buscalibre.cl/libros/ficcion",
        }
        assert schema.validate(data) is True

    def test_validate_fails_on_missing_title(self):
        """validate() returns False when title is missing."""
        schema = CSVSchema()
        data = {
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_author(self):
        """validate() returns False when author is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_price(self):
        """validate() returns False when price is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
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
            "source": "buscalibre",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_page_index(self):
        """validate() returns False when page_index is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_product_url(self):
        """validate() returns False when product_url is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "source": "buscalibre",
        }
        assert schema.validate(data) is False

    def test_validate_fails_on_missing_source(self):
        """validate() returns False when source is missing."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
        }
        assert schema.validate(data) is False

    def test_validate_with_extra_fields(self):
        """validate() returns True when extra fields present (not in schema)."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
            "category_url": "https://www.buscalibre.cl/libros/ficcion",
            "extra_field": "ignored",
        }
        assert schema.validate(data) is True

    def test_validate_fields_property(self):
        """CSVSchema.fields returns list of required field names."""
        schema = CSVSchema()
        expected = ["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
        assert schema.fields == expected

    def test_prepare_for_csv_returns_dict(self):
        """prepare_for_csv() returns a dictionary with CSV-ready values."""
        schema = CSVSchema()
        data = {
            "title": "Test Book",
            "author": "Author Name",
            "price": 100.00,
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
            "category_url": "https://www.buscalibre.cl/libros/ficcion",
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
            "stock": True,
            "page_index": 1,
            "product_url": "https://example.com/product/1",
            "source": "buscalibre",
            "category_url": "https://www.buscalibre.cl/libros/ficcion",
            "extra_field": "should_be_removed",
        }
        result = schema.prepare_for_csv(data)
        assert "extra_field" not in result
        assert len(result) == 8  # Only schema fields

    def test_prepare_for_csv_preserves_field_order(self):
        """prepare_for_csv() returns dict with fields in schema order."""
        schema = CSVSchema()
        data = {
            "source": "buscalibre",
            "category_url": "https://www.buscalibre.cl/libros/ficcion",
            "product_url": "https://example.com/product/1",
            "page_index": 1,
            "stock": True,
            "price": 100.00,
            "author": "Author Name",
            "title": "Test Book",
        }
        result = schema.prepare_for_csv(data)
        keys_list = list(result.keys())
        expected_order = ["title", "author", "price", "stock", "page_index", "product_url", "source", "category_url"]
        assert keys_list == expected_order
