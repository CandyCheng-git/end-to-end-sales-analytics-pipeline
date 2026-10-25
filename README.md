# End-to-End Sales Analytics Pipeline

> **Local pipeline verified · Portfolio work in progress** — a reproducible ELT project using Python, DuckDB, dbt Core, Conda (Miniforge) and Docker Compose. The local pipeline has been run successfully; Databricks integration and the Power BI dashboard are **planned, not implemented**.

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
dbt debug --project-dir dbt --profiles-dir .
dbt build --project-dir dbt --profiles-dir .
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

**Verified on Windows with Docker Desktop (2026-10-25):** the Docker image built successfully, and the full Compose command completed ingestion, dbt models/tests and CSV export. This is a local development validation, not a production deployment or a guarantee of identical results on every machine.

## Verified local execution (2026-10-25)

The following results were observed during a successful local run using `docker compose build`, `docker compose run --rm pipeline`, and `docker compose run --rm pipeline python -m pytest -q`:

| Check | Verified outcome |
| --- | --- |
| Environment | Docker image built; Python 3.12.15, dbt Core 1.12.6, dbt-duckdb 1.11.0 |
| Ingestion | 11 synthetic input rows loaded into `bronze.raw_sales` |
| dbt build | 5 SQL models built (1 view and 4 tables), 17 data tests passed |
| dbt summary | `PASS=22 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=22` |
| Python unit tests | `11 passed` using pytest |
| Data export | `data/processed/daily_sales.csv` written and verified on the Windows host |
| Metrics validation | All four exported daily rows matched the expected sample metrics below |

The earlier dbt CLI argument error was corrected in `compose.yaml`. Generic test declarations were updated to use the `arguments` property, and the subsequent dbt run showed no deprecation warnings.

### Recheck the outputs (PowerShell)

From the repository root after the pipeline finishes:

```powershell
Test-Path .\data\warehouse\sales.duckdb
Test-Path .\data\processed\daily_sales.csv
Import-Csv .\data\processed\daily_sales.csv | Format-Table -AutoSize
```

The exported CSV is ready to **import** into Power BI Desktop; a Power BI report has **not** yet been built.

## Data model and business logic

- **Grain:** `fct_sales` contains one record per `(order_id, line_id)` after choosing the latest `source_updated_at` version.
- **Dimensions:** `dim_customers` and `dim_products` are illustrative current-state dimensions (not SCD Type 2).
- **Metrics:** `line_amount = quantity × unit_price`. Daily sales include `Completed` order lines only; cancelled and returned lines remain in the fact for investigation but do not count toward reported sales.
- **Scope:** Sample dates, amounts and customer/product attributes are synthetic. No taxes, discounts, shipping, currency conversions or refunds are modelled.

See [`docs/architecture.md`](docs/architecture.md) for technical decisions.

### Verified sample metrics

From the included synthetic CSV, after keeping the latest version of each order line and excluding `Cancelled` / `Returned` lines from daily totals, the **observed exported output (2026-10-25)** was:

| Date | Completed orders | Units sold | Gross sales |
| --- | ---: | ---: | ---: |
| 2026-09-01 | 2 | 6 | 190.30 |
| 2026-09-02 | 1 | 4 | 74.00 |
| 2026-09-03 | 2 | 4 | 147.80 |
| 2026-09-04 | 1 | 6 | 142.40 |

These four rows were checked against the exported CSV after the successful local dbt/DuckDB run. They describe synthetic data only, not real customer sales.

## Data quality

dbt models declare `not_null`, `unique`, `accepted_values` and `relationships` tests. Python ingestion rejects missing fields, invalid dates, invalid quantities/prices and unknown statuses before writing the Bronze table. **All 17 dbt data tests and all 11 Python unit tests passed locally** on 2026-10-25. The GitHub Actions workflow currently executes **Python unit tests only**; it does **not** run the complete ingestion → dbt → export integration pipeline.

## Limitations / planned extensions

- [x] Python CSV ingestion into local DuckDB
- [x] SQL-based staging and dimensional models in dbt
- [x] Declarative dbt data-quality tests and unit-tested input validation
- [x] Daily-sales CSV export for a BI tool
- [x] Locally verified Docker Compose run (5 models, 17 dbt tests, 11 Python unit tests)
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

This repository demonstrates an **executed and locally validated** Conda + Docker analytics workflow, including a documented reporting grain, transformations, quality checks and reproducible commands. It is **not** presented as production-ready, an automated full-pipeline CI build, or completed Databricks / Power BI work. Screenshots and cloud integration evidence will be added only after those features are actually implemented.
