# M3 — Olist Silver transformations: local execution and closeout evidence

**Project:** End-to-End Sales Analytics Pipeline  
**Milestone:** M3 — dbt Silver transformations  
**Date:** 2026-11-11 (Australia/Melbourne)  
**Feature branch:** feat/m3-olist-silver-transformations  
**Evidence provenance:** Results reported by the project owner from Windows PowerShell, Docker Compose and DBeaver. The original Olist data was not available to the GitHub connector or GitHub-hosted CI for independent full-data re-execution.

## Executive summary

M3 implements nine typed Olist staging models and two intermediate models in dbt/DuckDB, preserving all Bronze observations and enforcing explicit data grains. The intermediate layer produces one row per ZIP prefix to prevent geographic join fanout and one row per product with categorical translation coverage flags.

- **Olist build:** 11 models (9 staging views, 1 intermediate view, 1 intermediate table) + 56 dbt tests = **PASS=67, WARN=0, ERROR=0**.
- **Synthetic regression:** 5 existing models + 17 tests = **PASS=22, WARN=0, ERROR=0**; daily_sales.csv exported.
- **Combined test coverage:** 73 of 73 defined dbt data tests passed across two separate local executions. This is not a claim that one build executed all 73.
- **Final safe join:** 112,650 joined rows and 112,650 distinct order-item keys, with no missing core business relationships.

## Environment and reproducibility

| Component | Observed / configured |
| --- | --- |
| dbt Core | 1.12.6 |
| dbt DuckDB adapter | 1.11.1 |
| Warehouse | DuckDB, data/warehouse/sales.duckdb (local, git-ignored) |
| Execution | Docker Compose + Conda |
| Inspection | DBeaver |
| Host | Windows PowerShell / VS Code |

The Dockerfile copies project code into the image; rebuild with `docker compose build pipeline` after changing SQL/YAML files. Disconnect DBeaver before running the pipeline to avoid file-lock conflicts. The original raw Olist CSVs and local DuckDB warehouse are not committed.

M2 Bronze ingestion is a prerequisite; this milestone does **not** package or download the original Olist CSV files.

## Staging models and source reconciliation

All nine staging models retain the same number of observations as their corresponding Bronze source tables.

| Model | Grain | Bronze rows | Silver rows |
| --- | --- | ---: | ---: |
| stg_olist_orders | order_id | 99,441 | 99,441 |
| stg_olist_order_items | (order_id, order_item_id) | 112,650 | 112,650 |
| stg_olist_order_payments | (order_id, payment_sequential) | 103,886 | 103,886 |
| stg_olist_order_reviews | (review_id, order_id) | 99,224 | 99,224 |
| stg_olist_customers | customer_id | 99,441 | 99,441 |
| stg_olist_products | product_id | 32,951 | 32,951 |
| stg_olist_sellers | seller_id | 3,095 | 3,095 |
| stg_olist_geolocation | observation row (ZIP not unique) | 1,000,163 | 1,000,163 |
| stg_olist_category_name_translation | Portuguese category | 71 | 71 |
| **Total** | | **1,550,922** | **1,550,922** |

### Key design decisions

- **Orders:** Normalise order status and cast five timestamp fields without silently dropping malformed or missing records.
- **Order items:** Use a composite `order_item_key` rather than only `order_id`. Retain item grain and prices/freight.
- **Payments:** Use `(order_id, payment_sequential)`; retain multiple payments per order to avoid premature aggregation.
- **Reviews:** `review_id` alone is not unique (99,224 rows vs 98,410 distinct review IDs). The `(review_id, order_id)` composite key is unique across all 99,224 rows; deleting repeated review IDs would lose 814 records.
- **Customers:** 99,441 customer IDs, 96,096 unique customer identities and 2,997 identities appearing in multiple customer records. These identities are **not yet** a status-filtered repeat-purchase KPI.
- **ZIP prefixes:** Remain strings to preserve leading zeros. Starting-zero observations: customers 23,995; sellers 1,027; geolocation 245,733.
- **Products:** Preserve optional missing categories and measurements, and rename Olist's `lenght` fields in the staging output.

## Intermediate models

### int_olist_geolocation_zip

A materialised table aggregates 1,000,163 geolocation observations into **19,015 unique ZIP prefixes**. It uses median latitude/longitude and records the original observation count per prefix. This supports one-to-one ZIP lookup joins; source geolocation ZIP keys are not unique.

| Audit | Result |
| --- | ---: |
| Output ZIP rows | 19,015 |
| Distinct ZIP keys | 19,015 |
| SUM(observation_count) | 1,000,163 |
| Minimum observations per ZIP | 1 |
| Maximum observations per ZIP | 1,146 |
| Invalid source latitude/longitude conversion counts | 0 / 0 |
| Invalid global coordinate ranges | 0 |

Median coordinates are approximate representative points and do not establish accurate street addresses or perfect Brazilian geographic validity.

### int_olist_products_enriched

A LEFT JOIN preserves **all 32,951 products**, attaching the English category if present and a transparent mapping status otherwise.

| Category mapping status | Products |
| --- | ---: |
| translated | 32,328 |
| missing_source_category | 610 |
| unmapped_translation | 13 |
| **Total** | **32,951** |

Unmapped source categories are `portateis_cozinha_e_preparadores_de_alimentos` (10 products) and `pc_gamer` (3 products). No invented translation or product deletion was performed.

## Validation evidence

### Full Olist Silver build

```powershell
docker compose build pipeline
docker compose run --rm pipeline dbt build --project-dir dbt --profiles-dir . --select "stg_olist_*" "int_olist_*"
```

Reported terminal result: **PASS=67 WARN=0 ERROR=0 TOTAL=67** (11 models + 56 dbt data tests). This included relationship tests for Order Items, Payments and Reviews to Orders and Orders to Customers.

### Existing synthetic regression

```powershell
docker compose run --rm pipeline
```

Reported terminal result: **PASS=22 WARN=0 ERROR=0 TOTAL=22** (5 models + 17 data tests). Loaded 11 synthetic rows and exported `/app/data/processed/daily_sales.csv`.

The default pipeline's `--select stg_sales+` keeps the synthetic regression separate from Olist source-dependent models.

### Explicit type-conversion checks

For non-empty Bronze values that fail the specified `TRY_CAST`:

| Dataset | Fields audited | Invalid conversions |
| --- | ---: | ---: |
| Orders | 5 timestamps | 0 |
| Order items | 4 | 0 |
| Payments | 3 | 0 |
| Reviews | 3 | 0 |
| Products | 7 numeric | 0 |
| Geolocation | 2 coordinates | 0 |

These checks do not establish all business invariants or whether rounding is appropriate for every numeric measure.

### Final multi-table cardinality audit

A LEFT JOIN from staging order items to Orders, Customers, enriched Products, Sellers and **two joins to the ZIP-level geolocation lookup** produced:

| Metric | Count |
| --- | ---: |
| Joined rows | 112,650 |
| Distinct order item keys | 112,650 |
| Missing orders | 0 |
| Missing customers | 0 |
| Missing products | 0 |
| Missing sellers | 0 |
| Unmatched customer ZIP rows | 302 |
| Unmatched seller ZIP rows | 253 |

**Acceptance:** The audited join path maintained order-item grain with no row multiplication, and no missing core business relationships.

The unmatched ZIP numbers are measured at joined **order-item** grain, not distinct ZIPs or distinct customer/seller records. LEFT JOINs retain transactional rows without geolocation matches. This audit does **not** establish that directly joining raw payments or reviews onto order items would be cardinality-safe.

## Retained data quality exceptions and limitations

| Condition | Observed count | Decision |
| --- | ---: | --- |
| Delivered orders without customer delivery date | 8 | Retain / document |
| Canceled orders with customer delivery date | 6 | Retain / document |
| Products without category | 610 | Preserve NULL |
| Products with untranslated category | 13 | Flag |
| Products without weight | 2 | Preserve NULL |
| Products lacking one or more dimensions | 2 | Preserve NULL |
| Unmatched customer geolocation (item-grain rows) | 302 | Preserve via LEFT JOIN |
| Unmatched seller geolocation (item-grain rows) | 253 | Preserve via LEFT JOIN |

Type casting and global coordinate ranges passed, but detailed business-rule validity, geography accuracy and downstream metric semantics remain separate concerns. Payment and order-item grain differences must be explicitly reconciled in Gold models. A final repeat-purchase KPI requires a business definition of eligible order statuses.

## M3 acceptance checklist

- [x] Nine Bronze sources modelled as typed staging views
- [x] Nine Bronze–Silver row-count reconciliations
- [x] Composite keys and source-level grain preserved
- [x] Two intermediate models with unique geographic/product grain
- [x] Key / relationship dbt tests passed
- [x] Orders, products and other typed-field conversion audits passed
- [x] Geolocation and product-category reconciliation passed
- [x] Olist full build: 67/67 successful
- [x] Synthetic regression: 22/22 successful
- [x] Order-item multi-table join cardinality audit: 112,650 / 112,650
- [ ] GitHub-hosted validation against full Olist CSV data (not included in repo)
- [ ] PR reviewed and merged (separate integration step)

**Conclusion:** M3 implementation and local validation acceptance are evidenced. M4 should define business metrics and fact-table grain before implementing revenue, payment reconciliation, repeat-customer KPIs and seller performance. Do not directly join multiple one-to-many payment/review tables onto order items.

**Source-control note:** This GitHub branch was reconstructed from the explicitly recorded M3 SQL/YAML snippets and local validation transcript. It is not a byte-for-byte push of the owner's uncommitted Windows working tree; compare any local differences before syncing or overwriting either side.
