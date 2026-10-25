"""Input validation for synthetic order-line CSV records."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = (
    "order_id", "line_id", "order_date", "customer_id", "customer_name",
    "product_id", "product_name", "quantity", "unit_price", "order_status",
    "source_updated_at",
)
VALID_STATUSES = {"Completed", "Cancelled", "Returned"}


def validate_headers(columns: list[str]) -> None:
    missing = set(REQUIRED_COLUMNS) - set(columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")


def validate_row(row: dict[str, str], row_number: int) -> None:
    for field in REQUIRED_COLUMNS:
        if not str(row.get(field, "") or "").strip():
            raise ValueError(f"Row {row_number}: missing {field}")

    try:
        date.fromisoformat(row["order_date"])
        datetime.fromisoformat(row["source_updated_at"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Row {row_number}: invalid date or timestamp") from exc

    try:
        quantity = int(row["quantity"])
        price = Decimal(row["unit_price"])
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise ValueError(f"Row {row_number}: invalid quantity or unit_price") from exc

    if quantity <= 0 or not price.is_finite() or price < 0:
        raise ValueError(f"Row {row_number}: quantity must be positive and price non-negative")
    if row["order_status"] not in VALID_STATUSES:
        raise ValueError(f"Row {row_number}: invalid order_status {row['order_status']!r}")
