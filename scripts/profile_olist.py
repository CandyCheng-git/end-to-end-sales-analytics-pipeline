"""Profile the nine Olist CSV files without ingesting or changing source data.

Run from repository root with Python and pandas available, e.g.:
    docker compose run --rm pipeline python scripts/profile_olist.py

Outputs are written under data/processed/olist/ (excluded from Git).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Expected candidate keys. Review IDs are diagnosed but NOT assumed unique;
# geolocation ZIP prefix is not a unique key.
SOURCES: dict[str, tuple[str, ...]] = {
    "olist_orders_dataset.csv": ("order_id",),
    "olist_order_items_dataset.csv": ("order_id", "order_item_id"),
    "olist_order_payments_dataset.csv": ("order_id", "payment_sequential"),
    "olist_order_reviews_dataset.csv": ("review_id",),
    "olist_customers_dataset.csv": ("customer_id",),
    "olist_products_dataset.csv": ("product_id",),
    "olist_sellers_dataset.csv": ("seller_id",),
    "olist_geolocation_dataset.csv": (),
    "product_category_name_translation.csv": ("product_category_name",),
}

# Columns to retain only as sets for distinct-value foreign-key profiling.
TRACK_COLUMNS: dict[str, tuple[str, ...]] = {
    "olist_orders_dataset.csv": ("order_id", "customer_id"),
    "olist_order_items_dataset.csv": ("order_id", "product_id", "seller_id"),
    "olist_order_payments_dataset.csv": ("order_id",),
    "olist_order_reviews_dataset.csv": ("order_id",),
    "olist_customers_dataset.csv": ("customer_id", "customer_unique_id"),
    "olist_products_dataset.csv": ("product_id", "product_category_name"),
    "olist_sellers_dataset.csv": ("seller_id",),
    "product_category_name_translation.csv": ("product_category_name",),
}

REFERENCES = [
    ("olist_orders_dataset.csv", "customer_id", "olist_customers_dataset.csv", "customer_id"),
    ("olist_order_items_dataset.csv", "order_id", "olist_orders_dataset.csv", "order_id"),
    ("olist_order_items_dataset.csv", "product_id", "olist_products_dataset.csv", "product_id"),
    ("olist_order_items_dataset.csv", "seller_id", "olist_sellers_dataset.csv", "seller_id"),
    ("olist_order_payments_dataset.csv", "order_id", "olist_orders_dataset.csv", "order_id"),
    ("olist_order_reviews_dataset.csv", "order_id", "olist_orders_dataset.csv", "order_id"),
    ("olist_products_dataset.csv", "product_category_name", "product_category_name_translation.csv", "product_category_name"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Olist CSV data-profiling reports")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/olist"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/olist"))
    parser.add_argument("--chunksize", type=int, default=50_000)
    args = parser.parse_args()
    if args.chunksize < 1:
        parser.error("--chunksize must be positive")

    missing_files = [name for name in SOURCES if not (args.data_dir / name).is_file()]
    if missing_files:
        parser.error("Missing Olist source file(s): " + ", ".join(missing_files))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    columns_report: list[dict] = []
    keys_report: list[dict] = []
    distinct_values: dict[tuple[str, str], set[str]] = defaultdict(set)

    for filename, candidate_key in SOURCES.items():
        path = args.data_dir / filename
        header = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns.tolist()
        if len(set(header)) != len(header):
            raise ValueError(f"Repeated/ambiguous column names in {filename}")
        required = set(candidate_key) | set(TRACK_COLUMNS.get(filename, ()))
        missing_columns = required - set(header)
        if missing_columns:
            raise ValueError(f"Missing required columns in {filename}: {sorted(missing_columns)}")

        row_count = 0
        nulls = {col: 0 for col in header}
        existing_keys: set[tuple[str, ...]] = set()
        duplicate_key_rows = 0
        null_key_rows = 0

        # Strings preserve leading zeros in Brazilian postal prefixes and IDs.
        # Empty strings are treated as missing, not literal 'NA' text.
        reader = pd.read_csv(
            path,
            dtype="string",
            keep_default_na=False,
            na_values=[""],
            chunksize=args.chunksize,
            encoding="utf-8-sig",
        )
        for chunk in reader:
            row_count += len(chunk)
            for col in header:
                nulls[col] += int(chunk[col].isna().sum())

            if candidate_key:
                valid = chunk[list(candidate_key)].notna().all(axis=1)
                null_key_rows += int((~valid).sum())
                for key in chunk.loc[valid, list(candidate_key)].itertuples(index=False, name=None):
                    token = tuple(str(value) for value in key)
                    if token in existing_keys:
                        duplicate_key_rows += 1
                    else:
                        existing_keys.add(token)

            for col in TRACK_COLUMNS.get(filename, ()):
                values = chunk[col].dropna().unique()
                distinct_values[(filename, col)].update(str(v) for v in values)

        summary.append({
            "filename": filename, "rows": row_count, "columns": len(header),
            "file_bytes": path.stat().st_size, "sha256": sha256(path),
        })
        for col in header:
            columns_report.append({
                "filename": filename, "column": col, "missing_rows": nulls[col],
                "missing_pct": f"{100 * nulls[col] / row_count:.2f}" if row_count else "0.00",
            })
        keys_report.append({
            "filename": filename,
            "candidate_key": ", ".join(candidate_key) if candidate_key else "(not assumed unique)",
            "null_key_rows": null_key_rows if candidate_key else "n/a",
            "duplicate_key_rows": duplicate_key_rows if candidate_key else "n/a",
            "note": "diagnostic only; review_id may repeat" if filename == "olist_order_reviews_dataset.csv" else "",
        })
        print(f"Profiled {filename}: {row_count:,} rows, {len(header)} columns")

    fk_rows = []
    for child, child_col, parent, parent_col in REFERENCES:
        child_values = distinct_values[(child, child_col)]
        parent_values = distinct_values[(parent, parent_col)]
        unmatched = child_values - parent_values
        fk_rows.append({
            "child_table": child, "child_column": child_col,
            "parent_table": parent, "parent_column": parent_col,
            "distinct_child_values": len(child_values),
            "unmatched_distinct_values": len(unmatched),
        })

    write_csv(args.output_dir / "olist_files_profile.csv", summary,
              ["filename", "rows", "columns", "file_bytes", "sha256"])
    write_csv(args.output_dir / "olist_column_nulls.csv", columns_report,
              ["filename", "column", "missing_rows", "missing_pct"])
    write_csv(args.output_dir / "olist_key_checks.csv", keys_report,
              ["filename", "candidate_key", "null_key_rows", "duplicate_key_rows", "note"])
    write_csv(args.output_dir / "olist_relationship_checks.csv", fk_rows,
              ["child_table", "child_column", "parent_table", "parent_column",
               "distinct_child_values", "unmatched_distinct_values"])

    lines = [
        "# Olist source data profiling",
        "",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
        "",
        "## Source files", "",
        "| File | Rows | Columns | Size (bytes) | SHA256 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in summary:
        lines.append(f"| `{row['filename']}` | {row['rows']:,} | {row['columns']} | {row['file_bytes']:,} | `{row['sha256']}` |")
    lines += ["", "## Candidate key checks", "",
              "Duplicate counts are repeated *rows* beyond the first key occurrence.",
              "Review IDs may repeat; geolocation ZIP prefixes are not unique keys.", "",
              "| File | Candidate key | Null-key rows | Duplicate-key rows |",
              "| --- | --- | ---: | ---: |"]
    for row in keys_report:
        lines.append(f"| `{row['filename']}` | {row['candidate_key']} | {row['null_key_rows']} | {row['duplicate_key_rows']} |")
    lines += ["", "## Foreign-key candidates", "",
              "Unmatched counts are **distinct non-null child values**, not row counts. An unmatched value is a finding to investigate, not necessarily invalid source data.", "",
              "| Child column | Parent column | Distinct child values | Unmatched distinct values |",
              "| --- | --- | ---: | ---: |"]
    for row in fk_rows:
        lines.append(
            f"| `{row['child_table']}.{row['child_column']}` | "
            f"`{row['parent_table']}.{row['parent_column']}` | "
            f"{row['distinct_child_values']:,} | {row['unmatched_distinct_values']:,} |"
        )
    lines += [
        "", "## Column-level missing values", "",
        "See `olist_column_nulls.csv` for every source column. Top columns by missing-value percentage:",
        "", "| File | Column | Missing rows | Missing % |", "| --- | --- | ---: | ---: |",
    ]
    for row in sorted(columns_report, key=lambda r: float(r["missing_pct"]), reverse=True)[:20]:
        lines.append(f"| `{row['filename']}` | `{row['column']}` | {row['missing_rows']:,} | {row['missing_pct']}% |")
    lines += [
        "", "## Interpretation and next actions", "",
        "- These are source-level diagnostic observations, **not** evidence of a completed Bronze/Silver/Gold pipeline.",
        "- Keep original CSV data local; review dataset licence and attribution before redistributing derived outputs.",
        "- Review candidate keys, missing dates, join fanout, and any orphan-key findings before M2 ingestion.",
        "- Data types were intentionally read as strings to preserve raw identifiers; type inference and casting belong in Silver modelling.",
        "- File hashes help document which exact local source version was profiled.",
    ]
    report = args.output_dir / "olist_profile.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote profiling outputs to {args.output_dir}")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()