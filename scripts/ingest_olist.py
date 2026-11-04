"""Deterministic, audited full-refresh of all nine Olist CSVs into DuckDB Bronze.

The source CSVs remain local and excluded from Git. Bronze columns are VARCHAR:
type conversion, deduplication and business decisions belong in dbt Silver.

Run from the repository root:
    docker compose run --rm olist-ingestion
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "raw" / "olist"
DEFAULT_DB_PATH = ROOT / "data" / "warehouse" / "sales.duckdb"

# M1 dictionary: all 52 headers, in their verified source order.
# The spelling of "lenght" is intentional and is retained from Olist.
SOURCE_SCHEMAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "olist_orders_dataset.csv": (
        "olist_orders",
        (
            "order_id", "customer_id", "order_status", "order_purchase_timestamp",
            "order_approved_at", "order_delivered_carrier_date",
            "order_delivered_customer_date", "order_estimated_delivery_date",
        ),
    ),
    "olist_order_items_dataset.csv": (
        "olist_order_items",
        (
            "order_id", "order_item_id", "product_id", "seller_id",
            "shipping_limit_date", "price", "freight_value",
        ),
    ),
    "olist_order_payments_dataset.csv": (
        "olist_order_payments",
        ("order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"),
    ),
    "olist_order_reviews_dataset.csv": (
        "olist_order_reviews",
        (
            "review_id", "order_id", "review_score", "review_comment_title",
            "review_comment_message", "review_creation_date", "review_answer_timestamp",
        ),
    ),
    "olist_customers_dataset.csv": (
        "olist_customers",
        (
            "customer_id", "customer_unique_id", "customer_zip_code_prefix",
            "customer_city", "customer_state",
        ),
    ),
    "olist_products_dataset.csv": (
        "olist_products",
        (
            "product_id", "product_category_name", "product_name_lenght",
            "product_description_lenght", "product_photos_qty", "product_weight_g",
            "product_length_cm", "product_height_cm", "product_width_cm",
        ),
    ),
    "olist_sellers_dataset.csv": (
        "olist_sellers",
        ("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"),
    ),
    "olist_geolocation_dataset.csv": (
        "olist_geolocation",
        (
            "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
            "geolocation_city", "geolocation_state",
        ),
    ),
    "product_category_name_translation.csv": (
        "olist_category_name_translation",
        ("product_category_name", "product_category_name_english"),
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_csv(path: Path, expected_headers: tuple[str, ...]) -> tuple[int, int, str]:
    """Check every CSV record before touching DuckDB; return count, size and hash."""
    if not path.is_file():
        raise ValueError(f"Missing Olist source file: {path}")

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            actual_headers = next(reader, [])
            if actual_headers != list(expected_headers):
                raise ValueError(
                    f"{path.name}: unexpected headers\n"
                    f"Expected: {list(expected_headers)}\nActual:   {actual_headers}"
                )
            rows = 0
            for record in reader:
                if len(record) != len(expected_headers):
                    raise ValueError(
                        f"{path.name}: malformed CSV record ending at physical line "
                        f"{reader.line_num}; expected {len(expected_headers)} fields, "
                        f"got {len(record)}"
                    )
                rows += 1
    except (csv.Error, UnicodeError, OSError) as exc:
        raise ValueError(f"{path.name}: CSV parsing failed: {exc}") from exc

    if rows == 0:
        raise ValueError(f"{path.name}: source CSV contains no data rows")
    return rows, path.stat().st_size, sha256_file(path)


def ingest_olist(
    data_dir: Path = DEFAULT_DATA_DIR,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, str | int]]:
    """Load nine raw tables atomically; append nine audit records on success.

    An individual full-refresh replaces only the nine Olist tables. The old
    synthetic bronze.raw_sales table and existing dbt models are untouched.
    """
    data_dir = Path(data_dir)
    db_path = Path(db_path)

    missing = [name for name in SOURCE_SCHEMAS if not (data_dir / name).is_file()]
    if missing:
        raise ValueError("Missing Olist source file(s): " + ", ".join(missing))

    # Check all nine inputs before creating or replacing any warehouse table.
    inspected: dict[str, tuple[int, int, str]] = {}
    for filename, (_, headers) in SOURCE_SCHEMAS.items():
        inspected[filename] = inspect_csv(data_dir / filename, headers)

    run_id = str(uuid4())
    ingested_at = datetime.now(timezone.utc)
    results: list[dict[str, str | int]] = []
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bronze.olist_ingestion_audit (
                    run_id VARCHAR NOT NULL,
                    ingested_at_utc TIMESTAMPTZ NOT NULL,
                    source_file VARCHAR NOT NULL,
                    target_table VARCHAR NOT NULL,
                    source_sha256 VARCHAR NOT NULL,
                    source_bytes BIGINT NOT NULL,
                    source_row_count BIGINT NOT NULL,
                    bronze_row_count BIGINT NOT NULL
                )
                """
            )

            for filename, (table, _) in SOURCE_SCHEMAS.items():
                source_path = data_dir / filename
                source_count, source_bytes, expected_sha = inspected[filename]
                # The target table name comes exclusively from SOURCE_SCHEMAS.
                conn.execute(
                    f'CREATE OR REPLACE TABLE bronze."{table}" AS '
                    "SELECT * FROM read_csv(?, header=true, all_varchar=true, "
                    "ignore_errors=false, null_padding=false)",
                    [str(source_path)],
                )
                bronze_count = conn.execute(
                    f'SELECT COUNT(*) FROM bronze."{table}"'
                ).fetchone()[0]
                if bronze_count != source_count:
                    raise ValueError(
                        f"{filename}: source rows={source_count}, "
                        f"Bronze rows={bronze_count}; rolling back"
                    )
                if sha256_file(source_path) != expected_sha:
                    raise ValueError(f"{filename}: source changed during ingestion; rolling back")

                conn.execute(
                    "INSERT INTO bronze.olist_ingestion_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        run_id, ingested_at, filename, f"bronze.{table}",
                        expected_sha, source_bytes, source_count, bronze_count,
                    ],
                )
                results.append({
                    "source_file": filename,
                    "target_table": f"bronze.{table}",
                    "rows": bronze_count,
                    "sha256": expected_sha,
                })

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Load all nine Olist CSVs into DuckDB Bronze")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    rows = ingest_olist(data_dir=args.data_dir, db_path=args.db_path)
    for row in rows:
        print(f"{row['source_file']} -> {row['target_table']}: {row['rows']:,} rows")
    print(f"M2 Bronze full refresh committed: {len(rows)} tables; {sum(r['rows'] for r in rows):,} total rows")
    print(f"Audit: bronze.olist_ingestion_audit | Database: {args.db_path}")


if __name__ == "__main__":
    main()
