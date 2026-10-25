# Olist migration — detailed portfolio milestone plan

> **Planning document · Updated 2026-10-25.** M0 records the verified synthetic-data baseline. **M1–M9 are plans, not completed features.** Keep this document in sync with actual commits and test evidence; never infer completion from a written task or proposed file path.

## Goals, scope and delivery strategy

- **Main dataset:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — nine related source CSV files containing anonymised historical e-commerce activity. The original synthetic CSV and pipeline remain available for regression testing.
- **Current stack:** Windows + VS Code; Conda (Miniforge) in Docker; Python 3.12, DuckDB, dbt Core / dbt-duckdb, SQL, pytest and GitHub Actions.
- **First release (portfolio v1.0):** M0–M6; reproducible local ingestion, tested dimensional models, documented business metrics and a real Power BI report.
- **Extensions:** M7 marketing acquisition funnel, M8 Databricks / Delta Lake, M9 incremental processing and performance benchmarking. M8 may be prioritised ahead of M7 when cloud-platform evidence is more valuable.
- **Indicative schedule:** 8–12 hours/week; weeks are estimates, not fixed deadlines. Scope and data-quality findings may change effort.
- **Definition of complete:** code and documentation committed, run instructions reproducible, outputs validated, limitations recorded, and the relevant automated or manual checks actually passed.

## Status overview

| Milestone | Outcome | Status | Indicative timing | Depends on |
| --- | --- | --- | --- | --- |
| M0 | Verified local synthetic pipeline preserved | **Completed (baseline)** | 2026-10-25 | — |
| M1 | Olist acquisition, profiling and data dictionary | Planned | Week 1 | M0 |
| M2 | Validated Python ingestion into Bronze | Planned | Week 2 | M1 |
| M3 | dbt Silver source transformations | Planned | Week 3 | M2 |
| M4 | Gold dimensional warehouse and reconciled KPIs | Planned | Weeks 4–5 | M3 |
| M5 | Quality gates, integration tests, CI | Planned | Week 6 | M2–M4 |
| M6 | Power BI dashboard and portfolio v1.0 | Planned | Weeks 7–8 | M4–M5 |
| M7 | Olist marketing funnel integration | Optional | Week 9 | M4–M6 |
| M8 | Databricks / Delta Lake implementation | Planned extension | Weeks 10–11+ | M2–M5 |
| M9 | Incremental loads and scalability benchmarks | Optional | Week 12+ | M5, ideally M8 |

## Proposed flow (future Olist pipeline)

1. Nine Olist CSV sources → Python schema validation, file metadata, ingestion.
2. DuckDB **Bronze** → separate, auditable raw-source tables.
3. dbt **Silver** → typed records, safe deduplication, consistent business keys, documented exceptions.
4. dbt **Gold** → fact and dimension tables plus explicit, reconciled business KPIs.
5. Automated quality checks → CSV/Parquet extracts → **Power BI Desktop**.
6. Later: reproduce and reconcile selected transformations in Databricks / Delta Lake.

Do **not** join order items directly to payments, reviews or raw geolocation and then sum monetary columns. These are potentially one-to-many relationships; aggregate to the intended grain before joining.

---

## M0 — Preserve the verified synthetic pipeline

**Status:** Completed for the baseline pipeline; a release tag or migration branch is *not* yet evidenced by this plan.

**Evidence (local run on 2026-10-25):**
- Docker image successfully built using Miniforge + Conda; Python 3.12.15.
- Ingested 11 synthetic rows into DuckDB.
- dbt Core 1.12.6 / dbt-duckdb 1.11.0: 5 SQL models (1 view + 4 tables), 17 data tests, `PASS=22 WARN=0 ERROR=0`.
- pytest: 11 passed; `data/processed/daily_sales.csv` exported and four daily rows checked.

**Tasks:** Keep `data/raw/sample_sales.csv`, `scripts/ingest_sales.py`, existing dbt models and tests. Before starting M1, ensure the working tree is clean; optionally tag the validated commit as `v0.1.0-synthetic-mvp` and use a feature branch for Olist.

**Acceptance:** Existing Docker Compose flow and Python unit tests still pass after migration changes.

**Suggested future commit (only if new baseline housekeeping changes are made):** `chore: preserve synthetic MVP regression baseline`

## M1 — Olist acquisition and exploratory data profiling

**Status:** Planned · **Estimate:** Week 1 · **Depends on:** M0

**Objective:** Establish source semantics and profiling evidence *before* modelling.

**Tasks:**
- Download all nine CSVs from the linked Olist dataset: orders, order items, payments, customers, reviews, products, sellers, geolocation, and category-name translation.
- Keep the downloaded files under `data/raw/olist/` on your machine; extend `.gitignore` and Docker volume configuration as appropriate. Do not commit the raw dataset by default.
- Record provenance, download/revision details, licence terms, schemas, inferred grains, row counts, nulls, distinct keys, duplicate patterns and orphan candidates.
- Investigate `customer_id` versus `customer_unique_id`; `(order_id, order_item_id)` uniqueness; repeated order payments and reviews; duplicate geolocation ZIP prefixes.
- Capture source-quality findings without assuming public reference row counts exactly match the downloaded version.

**Deliverables:** `scripts/profile_olist.py`, `docs/olist_data_dictionary.md`, `docs/olist_profiling.md`, source attribution and reproduction instructions.

**Acceptance criteria:** Every CSV is profiled, key/relationship assumptions are documented, and a reviewer can reproduce reported source counts from the same files.

**Suggested commit:** `feat(data): profile Olist sources and document data dictionary`

## M2 — Python ingestion and Bronze tables

**Status:** Planned · **Estimate:** Week 2 · **Depends on:** M1

**Objective:** Load the nine sources into DuckDB without breaking the synthetic pipeline.

**Tasks:**
- Implement `scripts/ingest_olist.py` with checks for missing files, unexpected headers and parse failures.
- Create one raw/typed-as-ingested `bronze.olist_*` table per source. Record ingestion timestamp, filename/checksum and row counts in an audit log or audit table.
- Use deterministic full refresh for v1.0; do not claim incremental ingestion yet.
- Add a dedicated Docker Compose command or service for Olist ingestion; persist generated DuckDB and outputs through host volume mounts.
- Test reruns and failures; make malformed input fail visibly instead of silently dropping records.

**Deliverables:** Ingestion script, Bronze tables, tests, audit evidence, updated run instructions.

**Acceptance criteria:** All nine tables load; counts reconcile to source files; rerunning does not accidentally duplicate records; old synthetic flow remains available.

**Suggested commit:** `feat(ingestion): load Olist CSV sources into DuckDB bronze`

## M3 — dbt Silver transformations

**Status:** Planned · **Estimate:** Week 3 · **Depends on:** M2

**Objective:** Create reliable, explicitly-grained source models.

**Tasks:**
- Create `dbt/models/staging/olist/` and intermediate models as needed; define sources and basic dbt tests.
- Cast dates, timestamps, money, quantities and identifiers; normalise categories where supported by the translation source.
- Validate primary keys / composite keys and document null, duplicate or unmatched records; don't silently suppress exceptions.
- Use `customer_unique_id` for person-level repeat-customer measures; treat `customer_id` as the order-linked customer row.
- Aggregate or deduplicate geolocation at an intentional ZIP-prefix level before joining to avoid row multiplication.

**Deliverables:** Staging/Intermediate SQL models, YAML source definitions and tests, documented Silver model grains and exceptions.

**Acceptance criteria:** Silver models build successfully; grain, key uniqueness and relationships are tested; changes to row counts are explained.

**Suggested commit:** `feat(dbt): implement Olist silver staging models`

## M4 — Gold star schema and business metrics

**Status:** Planned · **Estimate:** Weeks 4–5 · **Depends on:** M3

**Objective:** Build analytics-ready models whose totals remain correct under joins.

| Proposed model | Intended grain | Purpose |
| --- | --- | --- |
| `fct_order_items` | One row per (order_id, order_item_id) | Item-level sales and seller/product attribution |
| `fct_orders` | One row per order_id | Order counts, date cohorts and delivery |
| `fct_order_payments` | One row per order_id + payment_sequential | Payment methods/values |
| `dim_customers` | One row per customer_unique_id (proposed) | Repeat customers / retention |
| `dim_products` | One row per product_id | Categories |
| `dim_sellers` | One row per seller_id | Seller performance |
| `dim_date` | One row per calendar date | Time-series consistency |
| `mart_daily_sales` | One row per order date | Executive sales trend |

**Tasks:**
- Implement fact/dimension models with explicitly documented keys and grain; address multiple customer addresses/orders without producing duplicate dimension rows.
- Define KPI contract in `docs/metric_definitions.md`: delivered-item GMV (sum of item price excluding freight, BRL), delivered orders, AOV, freight, payment totals, late-delivery rate, repeat-customer rate.
- Define date attribution and valid order statuses for every KPI. Payment value and item GMV are **different measures**, not necessarily equal.
- Aggregate separate child relationships before joins; test no fanout and document any reconciliation differences.
- Create suitable daily/product/seller aggregates for BI; retain exception counts and reconciliation queries.

**Deliverables:** Gold dbt models, metric definition document, revenue/payment reconciliation and grain/relationship tests.

**Acceptance criteria:** Required model keys are unique at their grains; KPI totals can be recomputed from appropriate source tables; unexplained join inflation is zero.

**Suggested commit:** `feat(dbt): build Olist gold marts and define verified KPIs`

## M5 — Data quality, end-to-end testing and CI

**Status:** Planned · **Estimate:** Week 6 · **Depends on:** M2–M4

**Objective:** Turn a locally successful pipeline into a reproducible, test-gated project.

**Tasks:**
- Expand Python unit/integration tests for file/schema validation, malformed records, rerun behaviour and audit outputs.
- Add dbt source/model tests: uniqueness, not-null, accepted values, relationships, critical business assertions and sales reconciliation.
- Build a tiny, licence-safe, committed synthetic **fixture** for GitHub Actions so CI does not require Kaggle credentials or the full Olist dataset.
- Add `.github/workflows/pipeline-integration.yml` that runs ingestion → dbt build/tests → export and verifies expected fixture totals.
- Keep full Olist dataset checks in local/manual workflow if data isn't distributed publicly; report coverage and limits clearly.

**Deliverables:** Integration-test workflow, test fixtures, quality summary and recovery/failure instructions.

**Acceptance criteria:** Pull requests fail when essential quality gates fail; a green CI run demonstrates the fixture pipeline, not falsely the entire historical Olist ingestion.

**Suggested commit:** `ci: test ingestion dbt models and exports end to end`

## M6 — Power BI and portfolio v1.0

**Status:** Planned · **Estimate:** Weeks 7–8 · **Depends on:** M4–M5

**Objective:** Turn validated Olist marts into decision-ready reporting.

**Tasks:**
- Export clean Gold tables for Power BI Desktop (or connect directly if practical), modelling relationships and DAX measures at the correct grain.
- Build three pages: (1) Executive Sales Overview; (2) Product & Seller Performance; (3) Delivery & Customer Experience.
- Clearly label BRL, date ranges, delivered-only metrics, item GMV vs payment totals, and data exclusions.
- Write at least three evidence-based insights, with practical implications and limitations; add real report screenshots only after they exist.
- Document report refresh/reproduction steps, technical trade-offs, provenance and the remaining limitations in README/docs.

**Deliverables:** `powerbi/olist_sales_analytics.pbix` (or version-controlled Power BI project), screenshots, `docs/business_insights.md`, updated README.

**Acceptance criteria:** A reviewer can follow documented steps to regenerate validated data, open the report and reproduce headline KPI values. Publish **v1.0** only then.

**Suggested commit:** `feat(bi): deliver Olist Power BI dashboard and portfolio evidence`

## M7 — Olist marketing funnel (optional)

**Status:** Optional / not started · **Estimate:** Week 9 · **Depends on:** M4–M6

**Objective:** Connect sampled seller lead/deal activity with order performance.

**Tasks:** Profile Olist's separate [Marketing Funnel dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist); model marketing-qualified leads and closed deals at their correct grains; link by seller_id with explicit many-to-one handling; segment matched seller cohorts; explain selection and sample limitations.

**Deliverables:** Bronze/Silver marketing sources, seller funnel marts, tests, a documented funnel page or case study.

**Acceptance criteria:** Conversion denominators, joins and population coverage are clearly defined; no claim that the sample represents Olist's full sales funnel.

**Suggested commit:** `feat(marketing): link Olist seller funnel to performance`

## M8 — Databricks and Delta Lake migration

**Status:** Planned extension / not started · **Estimate:** Weeks 10–11+ · **Depends on:** M2–M5

**Objective:** Demonstrate comparable cloud transformations, not simply a notebook screenshot.

**Tasks:** Recreate appropriate Olist Bronze/Silver/Gold processing with Databricks Free Edition, PySpark and Delta where supported; investigate available authentication/external connections and optional `dbt-databricks`; reconcile model counts/keys/metrics with the DuckDB baseline; document compute limitations, elapsed time and costs (if applicable). **Do not assume Free Edition supports every integration.**

**Deliverables:** Runnable notebooks/jobs where available, Databricks architecture, reconciliation evidence, setup guidance without credentials.

**Acceptance criteria:** A reproducible cloud run produces independently checked outputs aligned with local definitions, or platform-related differences are explicitly documented. Do not claim completed integration until verified.

**Suggested commit:** `feat(databricks): reproduce Olist analytics on Delta Lake`

## M9 — Incremental processing and benchmarking (optional)

**Status:** Optional / not started · **Estimate:** Week 12+ · **Depends on:** M5, ideally M8

**Objective:** Investigate repeatable processing under evolving data and higher scale.

**Tasks:** Model historical batch replay with watermarks/checkpoints, idempotent upserts, late-arriving events, retries and observability; compare CSV/Parquet and DuckDB/Databricks execution under documented hardware/compute settings; optionally benchmark a separately licensed, larger public dataset. Distinguish **historical replay simulation** from real streaming.

**Deliverables:** Benchmark methodology, run logs, metrics (time, memory, rows), limitations and any follow-up improvements.

**Acceptance criteria:** Results are repeatable, recorded with test environment and input sizes, and make no unsupported distributed-scale or production streaming claims.

**Suggested commit:** `perf: benchmark incremental replay and query execution`

---

## Immediate next actions (start M1)

1. Preserve the verified synthetic baseline; inspect `git status` and choose a clean migration feature branch.
2. Download the nine Olist CSVs into a local ignored `data/raw/olist/` directory, verify dataset terms and record source attribution.
3. Implement profiling **before** ingesting into Bronze; inspect grain, duplicate keys, dates, nulls, orphan joins and row counts.
4. Commit the profiling script, data dictionary and reproducible instructions **without** uploading Olist raw data or credentials.
5. Begin M2 only when the M1 acceptance criteria above are met.

## Maintenance and evidence rules

- Update status to **In Progress** only once work actually starts; mark **Completed** only after the stated acceptance checks are evidenced.
- Keep README short; track full tasks, dependencies and decisions here. Use standalone architecture, data dictionary, metric definitions and business insights documents as they become real.
- Suggested commits are examples, **not** a claim that these Git commits exist.
- Dataset usage: attribute the Olist source, confirm the current Kaggle licence and redistribution terms before publishing derived data or charts, avoid uploading raw files by default, and never commit secrets.
- No current proof exists here of a Power BI report, Databricks pipeline, Olist ingestion, full integration CI, production monitoring or scalable streaming.

## CV integrity rule

Describe **only completed and verified** capabilities. The successful local Conda + Docker + DuckDB synthetic pipeline is valuable evidence for reproducibility, transformation and testing, but not evidence of a completed Olist, Power BI, Databricks or production deployment.
