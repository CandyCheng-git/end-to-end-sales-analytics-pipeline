"""Small synthetic nine-table Olist fixture for dbt CI (no original Olist CSVs).

Run in the repository root:
    python scripts/ci_olist_fixtures.py seed
    dbt build --project-dir dbt --profiles-dir . --select "stg_olist_*" "int_olist_*"
    python scripts/ci_olist_fixtures.py check

Fixtures are isolated in data/ci/sales.duckdb, not the owner\'s
real warehouse in data/warehouse/sales.duckdb. Set DBT_DUCKDB_PATH
to data/ci/sales.duckdb when running the Olist dbt build.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from ingest_olist import SOURCE_SCHEMAS, ingest_olist

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ci" / "sales.duckdb"

# Every tuple follows its schema's canonical M2 source CSV header ordering.
# Intentional cases: repeat customer identity, multi-item order, split payment,
# repeated review_id across orders, unmapped/missing product categories,
# repeated ZIP observation, leading-zero ZIP, and unmatched customer ZIP.
FIXTURES: dict[str, list[tuple[str, ...]]] = {
    "olist_orders": [
        ("o1", "c1", "delivered", "2018-01-01 10:00:00", "2018-01-01 11:00:00",
         "2018-01-02 10:00:00", "2018-01-03 10:00:00", "2018-01-07 00:00:00"),
        ("o2", "c2", "canceled", "2018-01-04 10:00:00", "", "", "", "2018-01-10 00:00:00"),
        ("o3", "c3", "shipped", "2018-01-05 10:00:00", "2018-01-05 10:30:00",
         "2018-01-07 08:00:00", "", "2018-01-15 00:00:00"),
    ],
    "olist_order_items": [
        ("o1", "1", "p1", "s1", "2018-01-04 12:00:00", "10.00", "2.00"),
        ("o1", "2", "p2", "s2", "2018-01-04 12:00:00", "7.00", "1.00"),
        ("o2", "1", "p3", "s1", "2018-01-06 12:00:00", "15.00", "3.00"),
        ("o3", "1", "p1", "s2", "2018-01-08 12:00:00", "8.00", "1.00"),
    ],
    "olist_order_payments": [
        ("o1", "1", "credit_card", "2", "10.00"),
        ("o1", "2", "voucher", "1", "9.00"),
        ("o2", "1", "boleto", "1", "18.00"),
        ("o3", "1", "debit_card", "1", "9.00"),
    ],
    "olist_order_reviews": [
        ("r1", "o1", "5", "Excellent", "Delivered", "2018-01-04 00:00:00", "2018-01-05 12:00:00"),
        ("r1", "o2", "3", "", "", "2018-01-05 00:00:00", "2018-01-06 12:00:00"),
        ("r2", "o3", "4", "", "Good", "2018-01-08 00:00:00", "2018-01-09 12:00:00"),
    ],
    "olist_customers": [
        ("c1", "u1", "01001", "Sao Paulo", "SP"),
        ("c2", "u1", "02002", "Rio de Janeiro", "RJ"),
        ("c3", "u2", "03003", "Belo Horizonte", "MG"),
    ],
    "olist_products": [
        ("p1", "eletronicos", "10", "30", "1", "300", "15", "10", "5"),
        ("p2", "pc_gamer", "8", "20", "2", "500", "20", "10", "12"),
        ("p3", "", "", "", "", "", "", "", ""),
    ],
    "olist_sellers": [
        ("s1", "01001", "Sao Paulo", "SP"),
        ("s2", "02002", "Rio de Janeiro", "RJ"),
    ],
    "olist_geolocation": [
        ("01001", "-23.5", "-46.6", "Sao Paulo", "SP"),
        ("01001", "-23.6", "-46.7", "Sao Paulo", "SP"),
        ("02002", "-22.9", "-43.2", "Rio de Janeiro", "RJ"),
    ],
    "olist_category_name_translation": [
        ("eletronicos", "electronics"),
    ],
}


def expect_equal(actual: object, expected: object, description: str) -> None:
    if actual != expected:
        raise AssertionError(f"{description}: expected {expected!r}; got {actual!r}")
    print(f"PASS {description}: {actual!r}")


def seed() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="olist-ci-") as directory:
        data_dir = Path(directory)
        for filename, (table_name, headers) in SOURCE_SCHEMAS.items():
            rows = FIXTURES[table_name]
            for row in rows:
                expect_equal(len(row), len(headers), f"{table_name} fixture field count")
            with (data_dir / filename).open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(rows)
        results = ingest_olist(data_dir=data_dir, db_path=DB_PATH)
        expect_equal(len(results), 9, "ingested Bronze source tables")
        expect_equal(
            sum(int(result["rows"]) for result in results),
            sum(len(rows) for rows in FIXTURES.values()),
            "ingested fixture observations",
        )
    print("Seeded nine synthetic Olist Bronze tables for CI.")


def check() -> None:
    with duckdb.connect(str(DB_PATH), read_only=True) as conn:
        for table_name, rows in FIXTURES.items():
            count = conn.execute(f"select count(*) from analytics.stg_{table_name}").fetchone()[0]
            expect_equal(count, len(rows), f"stg_{table_name} row count")

        zip_result = conn.execute(
            "select count(*), count(distinct geolocation_zip_code_prefix), "
            "sum(observation_count) from analytics.int_olist_geolocation_zip"
        ).fetchone()
        expect_equal(zip_result, (2, 2, 3), "unique ZIP lookup and preserved observations")
        zip_detail = conn.execute(
            "select observation_count from analytics.int_olist_geolocation_zip "
            "where geolocation_zip_code_prefix = '01001'"
        ).fetchone()
        expect_equal(zip_detail, (2,), "leading-zero ZIP aggregation")

        category_result = conn.execute(
            "select category_mapping_status, count(*) "
            "from analytics.int_olist_products_enriched "
            "group by category_mapping_status order by category_mapping_status"
        ).fetchall()
        expect_equal(
            category_result,
            [("missing_source_category", 1), ("translated", 1), ("unmapped_translation", 1)],
            "product category mapping coverage",
        )

        review_result = conn.execute(
            "select count(*), count(distinct review_id), count(distinct review_key) "
            "from analytics.stg_olist_order_reviews"
        ).fetchone()
        expect_equal(review_result, (3, 2, 3), "review composite-key grain")

        payment_result = conn.execute(
            "select count(*) from analytics.stg_olist_order_payments where order_id = 'o1'"
        ).fetchone()[0]
        expect_equal(payment_result, 2, "split payment grain")

        joined_result = conn.execute(
            """
            select
                count(*),
                count(distinct i.order_item_key),
                count(*) filter (where o.order_id is null),
                count(*) filter (where c.customer_id is null),
                count(*) filter (where p.product_id is null),
                count(*) filter (where s.seller_id is null),
                count(*) filter (where cg.geolocation_zip_code_prefix is null)
            from analytics.stg_olist_order_items i
            left join analytics.stg_olist_orders o on i.order_id = o.order_id
            left join analytics.stg_olist_customers c on o.customer_id = c.customer_id
            left join analytics.int_olist_products_enriched p on i.product_id = p.product_id
            left join analytics.stg_olist_sellers s on i.seller_id = s.seller_id
            left join analytics.int_olist_geolocation_zip cg
              on c.customer_zip_code_prefix = cg.geolocation_zip_code_prefix
            left join analytics.int_olist_geolocation_zip sg
              on s.seller_zip_code_prefix = sg.geolocation_zip_code_prefix
            """
        ).fetchone()
        expect_equal(
            joined_result,
            (4, 4, 0, 0, 0, 0, 1),
            "order-item join cardinality, relationships and unmatched ZIP preservation",
        )
    print("All Olist Silver CI fixture assertions passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seed", "check"))
    action = parser.parse_args().action
    if action == "seed":
        seed()
    else:
        check()


if __name__ == "__main__":
    main()
