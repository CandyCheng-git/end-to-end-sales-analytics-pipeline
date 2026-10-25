# Olist E-Commerce — Source Data Profiling & Quality Findings

**Milestone:** M1 — Dataset Acquisition & Profiling
**Assessment date:** 2026-10-25 (local execution)
**Source:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
**Execution:** `docker compose run --rm pipeline python scripts/profile_olist.py` and targeted Pandas / PowerShell checks
**Data status:** Historical, anonymised public source; original CSV files retained locally and excluded from Git.

> This document records verified results supplied from the local run. It is not a claim that the data has been loaded into DuckDB or that M2 has started. Check the source's current licence and redistribution terms before publishing underlying data.

## Acquisition and reproducibility

- Nine CSV source files downloaded to `data/raw/olist/`.
- `.gitignore` excludes `data/raw/olist/`; a local `.dockerignore` change excludes the same directory from image build context.
- Docker image build succeeded after the ignore change; build context decreased from 126.26 MB to 1.66 kB (the build used cache, so timing is not a controlled performance benchmark).
- The Docker Compose runtime binds `./data:/app/data`, permitting container reads of the locally downloaded data without baking it into the image.
- Profiling generated five local-only files in `data/processed/olist/`: `olist_profile.md`, `olist_files_profile.csv`, `olist_column_nulls.csv`, `olist_key_checks.csv`, and `olist_relationship_checks.csv`.

## Source file inventory

| File | Rows | Columns | Bytes | SHA256 |
| --- | ---: | ---: | ---: | --- |
| `olist_orders_dataset.csv` | 99,441 | 8 | 17,654,914 | `8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf` |
| `olist_order_items_dataset.csv` | 112,650 | 7 | 15,438,671 | `0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279` |
| `olist_order_payments_dataset.csv` | 103,886 | 5 | 5,777,138 | `4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0` |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 | 14,451,670 | `012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7` |
| `olist_customers_dataset.csv` | 99,441 | 5 | 9,033,957 | `983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2` |
| `olist_products_dataset.csv` | 32,951 | 9 | 2,379,446 | `3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc` |
| `olist_sellers_dataset.csv` | 3,095 | 4 | 174,703 | `1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e` |
| `olist_geolocation_dataset.csv` | 1,000,163 | 5 | 61,273,883 | `b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6` |
| `product_category_name_translation.csv` | 71 | 2 | 2,613 | `a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278` |

SHA256 values are copied from the local profiling report; use the local generated report as the authoritative comparison if any copy error is suspected.

## Candidate keys and grains

| Source | Candidate key | Verified outcome |
| --- | --- | --- |
| Orders | `order_id` | 0 duplicate-key rows; 0 null-key rows |
| Order items | (`order_id`, `order_item_id`) | 0 duplicate-key rows; 0 null-key rows |
| Payments | (`order_id`, `payment_sequential`) | 0 duplicate-key rows; 0 null-key rows |
| Reviews | (`review_id`, `order_id`) | **0 duplicate pairs**, verified in a separate Pandas check; `review_id` alone is **not unique** |
| Customers | `customer_id` | 0 duplicate-key rows; 0 null-key rows |
| Products | `product_id` | 0 duplicate-key rows; 0 null-key rows |
| Sellers | `seller_id` | 0 duplicate-key rows; 0 null-key rows |
| Geolocation | No unique key assumed | ZIP prefixes repeat; aggregate deliberately before joins |
| Category translation | `product_category_name` | 0 duplicate-key rows; 0 null-key rows |

A candidate key is observed unique for this dataset snapshot; it is not an upstream-enforced constraint.

### Review identity and fanout risk — verified

- Review rows: **99,224**.
- **789 distinct `review_id` values** occur more than once, adding **814 rows** beyond first `review_id` occurrences.
- All 789 repeated Review IDs are linked to **multiple distinct orders**.
- Duplicate (`review_id`, `order_id`) pairs: **0**.
- Completely identical review rows: **0**.
- **547 orders** have multiple review rows.

**Decision for M3:** Preserve every source review record. Do not deduplicate on `review_id` or `order_id`. Treat (`review_id`, `order_id`) as an observed unique candidate; validate it automatically in Silver. Use an explicit order-level aggregation rule before joining reviews into an order-grain fact/mart.

## Relationship checks — verified

| Child → Parent | Distinct child keys | Unmatched distinct keys |
| --- | ---: | ---: |
| Orders.customer_id → Customers.customer_id | 99,441 | 0 |
| Order items.order_id → Orders.order_id | 98,666 | 0 |
| Order items.product_id → Products.product_id | 32,951 | 0 |
| Order items.seller_id → Sellers.seller_id | 3,095 | 0 |
| Payments.order_id → Orders.order_id | 99,440 | 0 |
| Reviews.order_id → Orders.order_id | 98,673 | 0 |
| Products.product_category_name → Category translation.product_category_name | 73 | **2** |

Unmatched counts above are **distinct non-null child key values**, not record counts. While all non-null child order keys are represented in Orders, the reverse is not guaranteed. The counts imply **775 order IDs with no item row, one order ID with no payment row, and 768 order IDs with no review row**, assuming the source uniqueness and key coverage from this profiling run. These gaps are source coverage findings, not automatically errors.

## Missing categories — verified

Two product category values are not found in the Portuguese-to-English category translation mapping:

| Unmapped Portuguese category | Affected product rows |
| --- | ---: |
| `pc_gamer` | 3 |
| `portateis_cozinha_e_preparadores_de_alimentos` | 10 |
| **Total** | **13** |

**Decision for M3:** Retain the original category name and expose a translation-missing indicator or explicitly documented fallback. Do not silently drop the 13 products or invent a mapping in the source layer.

## Missing delivery timestamps — verified

| `order_status` | Orders | Missing `order_delivered_customer_date` |
| --- | ---: | ---: |
| delivered | 96,478 | 8 |
| invoiced | 314 | 314 |
| shipped | 1,107 | 1,107 |
| processing | 301 | 301 |
| unavailable | 609 | 609 |
| canceled | 625 | 619 |
| created | 5 | 5 |
| approved | 2 | 2 |
| **Total** | **99,441** | **2,965** |

Most missing delivery dates correspond to non-delivered statuses. **Eight** delivered orders have no delivery timestamp; **six** canceled orders *do* have a delivery timestamp. These are cases for investigation, not proof of bad data and not grounds for deleting rows.

## Other missing values — verified from profiling excerpt

| File / column | Missing rows | Missing share |
| --- | ---: | ---: |
| Reviews — `review_comment_title` | 87,656 | 88.34% |
| Reviews — `review_comment_message` | 58,247 | 58.70% |
| Orders — `order_delivered_customer_date` | 2,965 | 2.98% |

Review text is optional for many use cases; missing optional text must not cause entire review rows to be discarded. For the full per-column statistics use the locally generated `data/processed/olist/olist_column_nulls.csv`.

## Follow-up acceptance checks

- [x] Download and confirm nine source CSVs.
- [x] Run source-level row count, null, key and FK profiling.
- [x] Investigate unmatched categories and order delivery date gaps.
- [x] Validate Review ID repetition, composite key uniqueness and whole-row duplicates.
- [x] Verify dictionary field names and ordering directly against all nine local CSV headers (52 columns matched; local Docker/Pandas check, 2026-10-26).
- [x] Commit profiling script, documentation and ignore rules; [PR #1 merged to `main`](https://github.com/CandyCheng-git/end-to-end-sales-analytics-pipeline/pull/1).
- [x] Rerun existing synthetic Compose regression after merge (11 rows ingested; 5 dbt models; 17 data tests; `PASS=22 WARN=0 ERROR=0`; CSV exported).

**Scope boundary:** No Bronze/DuckDB ingestion of Olist has been completed under this milestone; that work belongs to M2.