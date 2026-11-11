# Olist migration — detailed portfolio milestone plan

> **Milestone status updated 2026-11-11.** M0–M3 are completed with local evidence; M3 was merged in [PR #4](https://github.com/CandyCheng-git/end-to-end-sales-analytics-pipeline/pull/4) and has passing GitHub Actions Python/dbt fixture CI. **M4–M9 are not completed.** This file is the canonical task tracker. Do not confuse full-Olist local evidence with small-fixture GitHub CI.

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
| M1 | Olist acquisition, profiling and data dictionary | **Completed (local verification + PR #1 merged)** | 2026-10-25–26 | M0 |
| M2 | Validated Python ingestion into Bronze | **Completed — locally verified** | 2026-11-04 | M1 |
| M3 | dbt Silver source transformations | **Completed — local full-data verification + merged PR #4 + CI** | 2026-11-11 | M2 |
| M4 | Gold dimensional warehouse and reconciled KPIs | Planned | Weeks 4–5 | M3 |
| M5 | Expand Gold quality gates, reconciliation and CI | **Planned — M3 delivered the initial synthetic dbt fixture CI** | Week 6 | M2–M4 |
| M6 | Power BI dashboard and portfolio v1.0 | Planned | Weeks 7–8 | M4–M5 |
| M7 | Olist marketing funnel integration | Optional | Week 9 | M4–M6 |
| M8 | Databricks / Delta Lake implementation | Planned extension | Weeks 10–11+ | M2–M5 |
| M9 | Incremental loads and scalability benchmarks | Optional | Week 12+ | M5, ideally M8 |

## Olist flow (Bronze/Silver implemented; Gold and BI planned)

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

**Status:** **Completed (2026-10-25–26)** · **Depends on:** M0

**Objective:** Establish source semantics and profiling evidence *before* modelling.

**Tasks:**
- Download all nine CSVs from the linked Olist dataset: orders, order items, payments, customers, reviews, products, sellers, geolocation, and category-name translation.
- Keep the downloaded files under `data/raw/olist/` on your machine; extend `.gitignore` and Docker volume configuration as appropriate. Do not commit the raw dataset by default.
- Record provenance, download/revision details, licence terms, schemas, inferred grains, row counts, nulls, distinct keys, duplicate patterns and orphan candidates.
- Investigate `customer_id` versus `customer_unique_id`; `(order_id, order_item_id)` uniqueness; repeated order payments and reviews; duplicate geolocation ZIP prefixes.
- Capture source-quality findings without assuming public reference row counts exactly match the downloaded version.

**Deliverables:** `scripts/profile_olist.py`, `docs/olist_data_dictionary.md`, `docs/olist_profiling.md`, source attribution and reproduction instructions.

**Acceptance criteria:** Every CSV is profiled, key/relationship assumptions are documented, and a reviewer can reproduce reported source counts from the same files.

**Evidence and closeout:** [Merged PR #1](https://github.com/CandyCheng-git/end-to-end-sales-analytics-pipeline/pull/1) contains `scripts/profile_olist.py`, source [data dictionary](olist_data_dictionary.md), [profiling report](olist_profiling.md), [executed command record](olist-m1-execution-notes.md), and Git/Docker exclusions for raw CSVs. The supplied local logs verify all nine headers against the dictionary (52 fields), nine CSVs successfully profiled, distinct-key/foreign-key checks, product category and review-grain investigations. After the merge, the local synthetic Docker Compose pipeline loaded 11 rows, built 5 dbt models, passed 17 dbt data tests (`PASS=22 WARN=0 ERROR=0`), and exported `daily_sales.csv`. GitHub Actions passed Python unit tests, but did not independently run the raw Olist profiling or full Docker/dbt pipeline. The original Olist CSVs and generated reports are kept local.

**Following M1, M2 Bronze ingestion was completed locally on 2026-11-04.** Typed models, formal grain validation, category handling and geolocation deduplication belong to M3. Verify licence terms before redistributing any source or derivative data.

## M2 — Python ingestion and Bronze tables

**Status:** Completed (user-supplied local verification on 2026-11-04) · **Depends on:** M1

**Objective:** Load the nine sources into DuckDB without breaking the synthetic pipeline.

**Tasks:**
- Implement `scripts/ingest_olist.py` with checks for missing files, unexpected headers and parse failures.
- Create one raw/typed-as-ingested `bronze.olist_*` table per source. Record ingestion timestamp, filename/checksum and row counts in an audit log or audit table.
- Use deterministic full refresh for v1.0; do not claim incremental ingestion yet.
- Add a dedicated Docker Compose command or service for Olist ingestion; persist generated DuckDB and outputs through host volume mounts.
- Test reruns and failures; make malformed input fail visibly instead of silently dropping records.

**Deliverables:** Ingestion script, Bronze tables, tests, audit evidence, updated run instructions.

**Acceptance criteria:** All nine tables load; counts reconcile to source files; rerunning does not accidentally duplicate records; old synthetic flow remains available.

**Implementation added for review:** `scripts/ingest_olist.py`, fixture-based tests and an `olist-ingestion` Compose service. The loader creates nine all-VARCHAR Bronze tables, checks exact M1 headers, reconciles row counts, stores checksum/ingestion metadata in `bronze.olist_ingestion_audit`, and commits table replacements atomically. Existing `bronze.raw_sales` and the synthetic service remain untouched.

**Commands to verify locally after obtaining all nine ignored CSVs:**
- `docker compose build`
- `docker compose run --rm olist-ingestion`
- Re-run the Olist command to confirm deterministic table row counts.
- `docker compose run --rm pipeline` to check the synthetic baseline.
- `docker compose run --rm pipeline python -m pytest -q` for fixture-based tests.

**M2 acceptance evidence:** [Executed run notes](olist-m2-execution-notes.md) record two successful full-source Docker runs, identical counts for all nine tables (1,550,922 rows total), two audited run IDs with source/Bronze totals matching, 17 local pytest tests and successful post-M2 synthetic dbt/export regression (`PASS=22 WARN=0 ERROR=0`). Results were supplied from Candy's local terminal; the raw Kaggle CSVs were not available to GitHub Actions or this assistant for an independent full-data rerun. Per-file SHA256 values were recorded and rechecked by the loader but were not separately compared with M1 hashes in the shared console output.

**Suggested commit:** `feat(ingestion): load Olist CSV sources into DuckDB bronze`

## M3 — dbt Silver transformations

**Status:** Completed (2026-11-11; [PR #4 merged](https://github.com/CandyCheng-git/end-to-end-sales-analytics-pipeline/pull/4)) · **Depends on:** M2

**Objective:** Create reliable, explicitly-grained source models.

**Tasks:**
- Create `dbt/models/staging/olist/` and intermediate models as needed; define sources and basic dbt tests.
- Cast dates, timestamps, money, quantities and identifiers; normalise categories where supported by the translation source.
- Validate primary keys / composite keys and document null, duplicate or unmatched records; don't silently suppress exceptions.
- Use `customer_unique_id` for person-level repeat-customer measures; treat `customer_id` as the order-linked customer row.
- Aggregate or deduplicate geolocation at an intentional ZIP-prefix level before joining to avoid row multiplication.

**Deliverables:** Staging/Intermediate SQL models, YAML source definitions and tests, documented Silver model grains and exceptions.

**Acceptance evidence (owner's full local Olist run):** Nine Bronze/Silver sources reconciled at 1,550,922 rows. All nine Olist staging models and two intermediate models built with 56 data tests (`PASS=67 WARN=0 ERROR=0`); ZIP aggregation produced 19,015 unique prefixes and the audited safe order-item join retained all 112,650 order items. The separate synthetic regression returned `PASS=22 WARN=0 ERROR=0`.

**CI evidence:** GitHub Actions now runs 17 Python unit tests plus [synthetic Olist dbt integration](https://github.com/CandyCheng-git/end-to-end-sales-analytics-pipeline/blob/main/.github/workflows/dbt-silver.yml) (11 Silver models + 56 dbt tests, category/ZIP/cardinality assertions) and the original synthetic regression (5 models + 17 tests). It uses a **separate ignored `data/ci/sales.duckdb`** for Olist fixture data. CI does **not** download or validate the full Olist CSV snapshot.

**Deliverables / closeout:** [M3 execution notes](olist-m3-execution-notes.md), `dbt/models/staging/olist/`, `dbt/models/intermediate/olist/`, `scripts/ci_olist_fixtures.py`, automated GitHub Actions checks, and [merged PR #4](https://github.com/CandyCheng-git/end-to-end-sales-analytics-pipeline/pull/4).

**Accepted limitations:** 610 products missing source category, 13 unmapped category products, ZIP misses on some order-item join rows, and retained delivery/status anomalies. Olist Gold and business revenue definitions are **not** part of M3.

## M4 — Gold star schema and business metrics

**Status:** Planned · **Estimate:** Weeks 4–5 · **Depends on:** M3

**Objective:** Build analytics-ready models whose totals remain correct under joins.

**Status checklist (not yet completed):**
- [ ] Write `docs/metric_definitions.md`: item GMV vs payment value, BRL, freight, discounts/refunds, eligible order statuses, purchase vs delivery-date attribution, AOV and retention cohort rules.
- [ ] Choose `fct_order_items` / `fct_orders` / `fct_order_payments` grains and build separate payment aggregation before combining metrics.
- [ ] Resolve `customer_id` vs `customer_unique_id` dimension modelling; define seller/product/category and calendar dimensions.
- [ ] Implement Gold models and dbt uniqueness/not-null/relationships tests at defined grains.
- [ ] Add revenue/payment reconciliation and anti-fanout assertions; quantify intentional differences and original source exceptions.
- [ ] Re-run Olist Gold against full local data, preserve SQL evidence, and extend fixture-based CI with Gold assertions before accepting M4.
- [ ] Obtain code review and merge the M4 PR only after results are recorded.

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

**Objective:** Extend the M3 fixture CI foundation into broader Gold-level quality and reconciliation checks. The initial Python + dbt Silver fixture CI is **already implemented**; do not duplicate it.

**Tasks:**
- Expand Python unit/integration tests for file/schema validation, malformed records, rerun behaviour and audit outputs.
- Add dbt source/model tests: uniqueness, not-null, accepted values, relationships, critical business assertions and sales reconciliation.
- **Already implemented in M3:** synthetic fixture generation and ingestion, GitHub Actions Olist Silver dbt build/tests, ZIP/category/grain assertions and synthetic baseline/export regression.
- Extend `.github/workflows/dbt-silver.yml` or add a Gold-specific workflow to test Gold transformations, KPI reconciliation and known failure cases against a deterministic fixture.
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

## Immediate next actions (M3 complete → M4)

1. **First repair the local Windows working tree.** The owner already fast-forwarded the local `main` branch ref to merged M3 commit `4e2a299`, but checkout remained blocked by Windows/OneDrive Git process locks. Clear only confirmed stale Git processes, remove `.git/index.lock` only with no Git process running, restore deleted tracked files, then switch to `main`. GitHub cannot directly operate this Windows environment.
2. **Start M4 with definitions, not SQL:** settle order status/date eligibility and item GMV vs order payments; publish `docs/metric_definitions.md` as a reviewed metric contract.
3. Implement explicitly-grained `fct_order_items`, `fct_orders`, payment aggregates and matching dimensions in a new feature branch from current `main`.
4. Reconcile full historical Olist counts and money totals locally; update CI with small synthetic fixture tests before merging.
5. Preserve the 11-row synthetic Compose baseline and keep raw Olist files, DuckDB warehouses and credentials out of Git.

## Maintenance and evidence rules

- Update status to **In Progress** only once work actually starts; mark **Completed** only after the stated acceptance checks are evidenced.
- Keep README short; track full tasks, dependencies and decisions here. Use standalone architecture, data dictionary, metric definitions and business insights documents as they become real.
- Suggested commits are examples, **not** a claim that these Git commits exist.
- Dataset usage: attribute the Olist source, confirm the current Kaggle licence and redistribution terms before publishing derived data or charts, avoid uploading raw files by default, and never commit secrets.
- Evidence now covers Olist Silver models and fixture-based GitHub Actions CI, **not** Olist Gold facts/KPIs, full-Olist GitHub-hosted execution, a Power BI report, Databricks pipeline, production monitoring or scalable streaming.

## CV integrity rule

Describe **only completed and verified** capabilities. M1 profiling, M2 Bronze and M3 Silver now have execution and code-review evidence; GitHub CI verifies a **synthetic fixture**, not the full Olist snapshot. Do **not** claim completed Olist Gold KPIs, Power BI, Databricks, incremental processing or production deployment.
