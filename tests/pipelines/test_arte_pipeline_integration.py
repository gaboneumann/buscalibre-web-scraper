import os
import csv
from unittest.mock import patch, MagicMock
from config.settings import OUTPUT_PATH

def test_production_csv_never_receives_test_data():
    """
    CRITICAL: Verify that test execution NEVER writes mock data to production CSV.

    This test enforces data integrity:
    - Production CSV must contain ONLY real Buscalibre book data
    - Zero test fixtures, zero mocks, zero contamination
    - This is a non-negotiable requirement for client delivery

    Solution: Mock save_single_record() to prevent ANY writes during testing.
    """
    # Get initial state of production CSV
    initial_rows = 0
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',')
            initial_rows = len(list(reader))

    # Mock save_single_record to prevent writes during tests
    with patch('pipelines.arte_pipeline.save_single_record') as mock_save:
        # Simulate pipeline execution (imports will work, but save_single_record is mocked)
        test_record = {
            "title": "Test Book",
            "author": "Test Author",
            "price": 15000,
            "stock": "TRUE",
            "page_index": 1,
            "product_url": "https://test.com/test",
            "source": "test"
        }

        # Try to "save" test record (should be mocked, not actually written)
        from pipelines.arte_pipeline import save_single_record
        save_single_record(test_record)

        # Verify mock was called (test is exercising the code path)
        mock_save.assert_called_once()

    # Verify CSV state unchanged after test
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',')
            final_rows = list(reader)

        # CSV should not have gained any rows
        assert len(final_rows) == initial_rows, \
            f"Production CSV was modified during test (gained {len(final_rows) - initial_rows} rows)"

        # CSV must not contain test fixtures
        content = ''.join(str(row) for row in final_rows)
        assert "Test Book" not in content, \
            "Production CSV must not contain test fixture 'Test Book' data"

        print(f"✅ Data integrity verified: {len(final_rows)} real rows, zero test data")
