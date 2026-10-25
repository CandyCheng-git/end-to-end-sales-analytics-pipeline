"""Unit tests for input validation; these do not require DuckDB."""

from pathlib import Path
import csv

import pytest

from src.sales_analytics.validation import REQUIRED_COLUMNS, validate_headers, validate_row

ROOT = Path(__file__).resolve().parents[1]


def valid_record() -> dict[str, str]:
    with (ROOT / "data/raw/sample_sales.csv").open(newline="", encoding="utf-8") as fp:
        return next(csv.DictReader(fp))


def test_schema_has_required_columns():
    validate_headers(list(valid_record()))


def test_missing_header_is_rejected():
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_headers([c for c in REQUIRED_COLUMNS if c != "order_id"])


def test_valid_row_is_accepted():
    validate_row(valid_record(), 2)


@pytest.mark.parametrize("field,value", [
    ("quantity", "0"),
    ("quantity", "abc"),
    ("unit_price", "-1"),
    ("unit_price", "NaN"),
    ("order_date", "not-a-date"),
    ("source_updated_at", "oops"),
    ("order_status", "Unknown"),
    ("order_id", ""),
])
def test_invalid_row_is_rejected(field: str, value: str):
    row = valid_record()
    row[field] = value
    with pytest.raises(ValueError):
        validate_row(row, 2)
