# Architecture and technical choices

## Local workflow

1. **Input:** versioned synthetic CSV order-line events in `data/raw/sample_sales.csv`.
2. **Validation:** reject rows with missing identifiers, invalid ISO dates, invalid quantity/price, or unsupported status.
3. **Bronze:** `bronze.raw_sales` stores validated raw text fields in DuckDB. Python ingestion replaces this table on each run, making demo runs deterministic.
4. **Staging:** `stg_sales` uses `row_number()` partitioned by `(order_id, line_id)` to keep the latest update, with typed dates/numbers and a deterministic sales-line key.
5. **Marts:** `fct_sales` preserves all statuses; customer and product dimensions describe reporting attributes; `daily_sales` aggregates only Completed lines.
6. **Quality:** dbt generic tests run during `dbt build`; independent unit tests check input validation.
7. **Export:** Power BI-ready CSV is generated from `analytics.daily_sales`.

## Assumptions and known gaps

- **Latest-version tie:** two updates to the same order line with identical timestamps would produce nondeterministic selection. A durable source event sequence is required in production.
- **Current-state dimensions:** max(customer_name) and max(product_name) produce sample lookup values, not history-aware SCDs. These fields are consistent in the example input.
- **Daily sales:** is sum of completed order-line prices before any taxes, discounts, refunds, exchange rates or shipping fees. It is not net revenue.
- **Data source:** fixed synthetic CSV (no live API ingestion). `requests` in the environment is reserved for future API ingestion.
- **Storage:** local DuckDB is a lightweight warehouse analogue; Databricks has not yet been integrated.
- **Execution:** manual/Compose only. No scheduling, retry or production orchestration is implemented.
- **Testing:** Python CI covers input validation; dbt build covers model tests only when manually run or as part of Compose. CI does not run a full DB build.

## Why this is useful for a graduate data consultant

The project makes the transformation logic, schema grain, business-metric definitions, failure cases and model lineage inspectable without requiring cloud credentials. It is deliberately scoped to a working local proof of concept instead of overstating cloud/platform experience.
