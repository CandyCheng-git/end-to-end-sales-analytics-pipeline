"""Load validated synthetic CSV into DuckDB bronze.raw_sales."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.sales_analytics.validation import validate_headers, validate_row  # noqa: E402

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

SOURCE = ROOT / "data" / "raw" / "sample_sales.csv"
DB_PATH = ROOT / "data" / "warehouse" / "sales.duckdb"


def main() -> None:
    df = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
    validate_headers(df.columns.tolist())
    if df.empty:
        raise ValueError("Input CSV has no data rows")
    for idx, record in enumerate(df.to_dict(orient="records"), start=2):
        validate_row(record, idx)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH)) as conn:
        conn.execute("create schema if not exists bronze")
        conn.register("input_sales", df)
        conn.execute("create or replace table bronze.raw_sales as select * from input_sales")
        conn.unregister("input_sales")
    print(f"Loaded {len(df)} synthetic rows into {DB_PATH}: bronze.raw_sales")


if __name__ == "__main__":
    main()
