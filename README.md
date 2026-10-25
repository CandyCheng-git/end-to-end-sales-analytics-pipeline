# End-to-End Sales Analytics Pipeline

> **Portfolio starter · Work in progress** — a reproducible local analytics pipeline using Python, DuckDB, dbt Core, Conda and Docker. Databricks integration and the Power BI report are **planned**, not implemented.

## Project overview

Sales data often arrives as raw transaction records with repeated updates, mixed status values and fields unsuitable for reporting. This project demonstrates a local ELT workflow that validates sample order-line data, stores it in a Bronze table, deduplicates and models it with dbt, tests warehouse models, and exports a daily-sales summary suitable for a downstream BI tool.

The provided dataset is **synthetic demonstration data**, not client or employer information.

## Architecture

```mermaid
flowchart LR
    A[Sample CSV] --> B[Python ingestion & validation]
    B --> C[(DuckDB: bronze.raw_sales)]
    C --> D[dbt staging / deduplication]
    D --> E[dbt marts: dimensions + fact]
    E --> F[dbt tests]
    E --> G[Gold: daily_sales]
    G --> H[CSV export]
    H -. Planned .-> I[Power BI report]
    E -. Future migration .-> J[Databricks]
```

**Stack currently in the project:** Python 3.12 · DuckDB · SQL · dbt-duckdb · Conda · Docker Compose · pytest · GitHub Actions (unit-test workflow).

| Layer | Implementation | Purpose |
| --- | --- | --- |
| Input | `data/raw/sample_sales.csv` | Synthetic transaction lines, including an updated version of a record |
| Bronze | `scripts/ingest_sales.py` | Validate records and load `bronze.raw_sales` into DuckDB |
| Staging | `dbt/models/staging/stg_sales.sql` | Cast fields, remove outdated duplicates, calculate line amounts |
| Marts | `dbt/models/marts/` | `dim_customers`, `dim_products`, `fct_sales`, `daily_sales` |
| Quality | dbt generic tests + Python unit tests | Primary-key, null, value and relationship checks |
| Export | `scripts/export_gold.py` | Write `data/processed/daily_sales.csv` |

## Run locally with Conda

Install [Conda](https://docs.conda.io/) (or a compatible distribution), then run from the **repository root**:

```bash
conda env create -f environment.yml
conda activate sales-analytics
python scripts/ingest_sales.py
dbt --project-dir dbt --profiles-dir . debug
dbt --project-dir dbt --profiles-dir . build
python scripts/export_gold.py
python -m pytest -q
```

Expected warehouse file: `data/warehouse/sales.duckdb`.
Expected exported file: `data/processed/daily_sales.csv`.

For repeat runs, ingestion replaces the Bronze table from the local CSV, and `dbt build` refreshes the models; the output is **not yet an incremental or scheduled production pipeline**.

## Run with Docker Compose

Requires Docker Desktop or Docker Engine with Compose. From the repository root:

```bash
docker compose build
docker compose run --rm pipeline
```

The Compose command runs ingestion, dbt models/tests and CSV export in order. `data/` is mounted to persist generated warehouse and CSV artifacts on your host.

> Docker configuration is provided for reproducibility. Validate it on your own machine; container execution has not been verified in this exported starter.

## Data model and business logic

- **Grain:** `fct_sales` contains one record per `(order_id, line_id)` after choosing the latest `source_updated_at` version.
- **Dimensions:** `dim_customers` and `dim_products` are illustrative current-state dimensions (not SCD Type 2).
- **Metrics:** `line_amount = quantity × unit_price`. Daily sales include `Completed` order lines only; cancelled and returned lines remain in the fact for investigation but do not count toward reported sales.
- **Scope:** Sample dates, amounts and customer/product attributes are synthetic. No taxes, discounts, shipping, currency conversions or refunds are modelled.

See [`docs/architecture.md`](docs/architecture.md) for technical decisions.

### Expected sample metrics

From the included synthetic CSV, after keeping the latest version of each order line and excluding `Cancelled` / `Returned` lines from daily totals, the **expected** output is:

| Date | Completed orders | Units sold | Gross sales |
| --- | ---: | ---: | ---: |
| 2026-09-01 | 2 | 6 | 190.30 |
| 2026-09-02 | 1 | 4 | 74.00 |
| 2026-09-03 | 2 | 4 | 147.80 |
| 2026-09-04 | 1 | 6 | 142.40 |

These figures are calculated from the example input and should be independently verified with the full dbt/DuckDB workflow before claiming a successful end-to-end run.

## Data quality

dbt models declare `not_null`, `unique`, `accepted_values` and `relationships` tests. Python ingestion rejects missing fields, invalid dates, invalid quantities/prices and unknown statuses before writing the Bronze table. The GitHub Actions workflow runs **Python unit tests only**, not a full warehouse integration test.

## Limitations / planned extensions

- [x] Python CSV ingestion into local DuckDB
- [x] SQL-based staging and dimensional models in dbt
- [x] Declarative dbt data-quality tests and unit-tested input validation
- [x] Daily-sales CSV export for a BI tool
- [ ] Run and document a working Databricks implementation
- [ ] Build a real Power BI dashboard and add screenshots / report files
- [ ] Add automated end-to-end integration tests and pipeline scheduling
- [ ] Add incremental ingestion, late-arriving records and SCD Type 2

See [`docs/portfolio-next-steps.md`](docs/portfolio-next-steps.md) for the development roadmap.

## Repository guide

```text
.
├── .github/workflows/unit-tests.yml
├── data/raw/sample_sales.csv
├── dbt/models/{staging,marts}/
├── docs/
├── scripts/{ingest_sales,export_gold}.py
├── src/sales_analytics/validation.py
├── tests/test_validation.py
├── environment.yml
├── profiles.yml
├── Dockerfile
└── compose.yaml
```

## About this portfolio

This repository starts with a *local Conda + Docker analytics pipeline* to demonstrate data modelling, testing and reproducibility. It is not presented as production deployment or as completed Databricks / Power BI work. Replace these notes with measured outcomes, actual screenshots and verified execution results as the project progresses.
