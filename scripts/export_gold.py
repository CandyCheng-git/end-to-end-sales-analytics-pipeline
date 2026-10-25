"""Export dbt Gold daily-sales model to a Power BI-compatible CSV."""

from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "sales.duckdb"
EXPORT = ROOT / "data" / "processed" / "daily_sales.csv"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError("Warehouse missing; run ingestion and dbt build first")
    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH), read_only=True) as conn:
        target = str(EXPORT).replace("'", "''")
        conn.execute(
            "copy (select * from analytics.daily_sales order by order_date) "
            f"to '{target}' (header, delimiter ',')"
        )
    print(f"Wrote: {EXPORT}")


if __name__ == "__main__":
    main()
