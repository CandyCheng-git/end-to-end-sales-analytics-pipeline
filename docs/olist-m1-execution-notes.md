# M1 — Executed Commands, Python Analysis & Evidence

**Project:** End-to-End Sales Analytics Pipeline  
**Dataset:** [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)  
**Evidence date:** 2026-10-25, from the user's local PowerShell/Docker terminal output.  
**Status:** M1 source profiling ran successfully; this note records observed results, not a fresh remote re-run. M2 ingestion and dbt Olist models are not implemented by these commands.

## Environment and data handling

- Windows, VS Code PowerShell, Docker Compose, Miniforge/Conda Python 3.12 in container, pandas.
- The user verified **9 CSV files** under `data/raw/olist/`.
- The local `.gitignore` excluded `data/raw/olist/` (`git check-ignore -v` passed); the local `.dockerignore` was changed to exclude the same folder and the build context decreased from **126.26 MB** to **1.66 kB**.
- The Docker Compose bind mount `./data:/app/data` exposes local CSVs at `/app/data/raw/olist/` at runtime.
- Never commit raw CSV files, Kaggle tokens or other credentials. `data/processed/` reports remain local unless deliberately reviewed for publication.

## A. Full source profiling — executed successfully

**Reusable source script:** [`scripts/profile_olist.py`](../scripts/profile_olist.py)

Run from the project root:

```powershell
docker compose build
docker compose run --rm pipeline python scripts/profile_olist.py
Get-ChildItem .\data\processed\olist\
Get-Content .\data\processed\olist\olist_profile.md -TotalCount 60
```

Observed script output:

```text
Profiled olist_orders_dataset.csv: 99,441 rows, 8 columns
Profiled olist_order_items_dataset.csv: 112,650 rows, 7 columns
Profiled olist_order_payments_dataset.csv: 103,886 rows, 5 columns
Profiled olist_order_reviews_dataset.csv: 99,224 rows, 7 columns
Profiled olist_customers_dataset.csv: 99,441 rows, 5 columns
Profiled olist_products_dataset.csv: 32,951 rows, 9 columns
Profiled olist_sellers_dataset.csv: 3,095 rows, 4 columns
Profiled olist_geolocation_dataset.csv: 1,000,163 rows, 5 columns
Profiled product_category_name_translation.csv: 71 rows, 2 columns

Wrote profiling outputs to data/processed/olist
Report: data/processed/olist/olist_profile.md
```

Generated (local, Git-ignored): `olist_profile.md`, `olist_files_profile.csv`, `olist_column_nulls.csv`, `olist_key_checks.csv`, `olist_relationship_checks.csv`.

## B. Unmapped product categories — executed in PowerShell

These commands were run directly against the original CSVs, and the counts below were observed after reloading the Products variable:

```powershell
$products = @(Import-Csv .\data\raw\olist\olist_products_dataset.csv)
"Products loaded: $($products.Count)"

$missingCategories = @(
    "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos"
)

$products |
    Where-Object { $_.product_category_name -in $missingCategories } |
    Group-Object product_category_name |
    Select-Object Name, Count |
    Format-Table -AutoSize
```

Observed: `Products loaded: 32951`; `pc_gamer`: **3** products; `portateis_cozinha_e_preparadores_de_alimentos`: **10** products. Thus **13** products are associated with **2** missing translation categories. These category names were originally identified by comparing the source Products and Translation CSV values; the script above counts their impacted products.

**Modelling decision (proposed, not yet implemented):** retain original Portuguese category and flag or explicitly map missing English translations in Silver rather than dropping records.

## C. Missing delivery dates by order status — executed in PowerShell

```powershell
$orders = Import-Csv .\data\raw\olist\olist_orders_dataset.csv
$orders |
    Group-Object order_status |
    ForEach-Object {
        [PSCustomObject]@{
            Status = $_.Name
            Orders = $_.Count
            MissingDeliveryDate = @(
                $_.Group | Where-Object { -not $_.order_delivered_customer_date }
            ).Count
        }
    } |
    Format-Table -AutoSize
```

| Status | Orders | Missing delivery dates |
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

**Observed exceptions:** 8 delivered orders had no delivered-customer date; 6 canceled orders had a non-empty delivered-customer date. A blank delivery date on an undelivered order should not automatically be classed as invalid.

## D. Duplicate review-ID investigation — executed in Docker/Pandas

The user first tried PowerShell `Group-Object` over ~99K review records; it stalled / did not yield a reliable result. The output `Duplicated review IDs: 1` and `Extra duplicate-key rows: -1` came from an unset/empty variable and must **not** be reused as findings. The Pandas computation below completed successfully.

```powershell
docker compose run --rm pipeline python -c "import pandas as pd; df = pd.read_csv('/app/data/raw/olist/olist_order_reviews_dataset.csv', dtype=str); g = df.groupby('review_id')['order_id'].agg(['size', 'nunique']); dup = g[g['size'] > 1]; print('Reviews loaded:', len(df)); print('Duplicated review IDs:', len(dup)); print('Extra duplicate-key rows:', int((dup['size'] - 1).sum())); print('Review IDs linked to multiple orders:', int((dup['nunique'] > 1).sum())); print(dup.head(10).to_string())"
```

Observed output (summary):

```text
Reviews loaded: 99224
Duplicated review IDs: 789
Extra duplicate-key rows: 814
Review IDs linked to multiple orders: 789
```

**Interpretation:** Every repeated `review_id` in this source snapshot appeared against more than one distinct `order_id`. Do not deduplicate on `review_id` alone.

## E. Review composite-key and row duplication — executed in Docker/Pandas

```powershell
docker compose run --rm pipeline python -c "import pandas as pd; df = pd.read_csv('/app/data/raw/olist/olist_order_reviews_dataset.csv', dtype=str); print('Total review rows:', len(df)); print('Duplicate (review_id, order_id) rows:', int(df.duplicated(['review_id', 'order_id']).sum())); print('Exact duplicate rows:', int(df.duplicated().sum())); print('Orders with multiple review rows:', int((df.groupby('order_id').size() > 1).sum()))"
```

Observed output:

```text
Total review rows: 99224
Duplicate (review_id, order_id) rows: 0
Exact duplicate rows: 0
Orders with multiple review rows: 547
```

**Verified key constraint in this snapshot:** (`review_id`, `order_id`) is unique, while each individual column is not guaranteed unique. Source review grain is a review/order association. In later Gold models, avoid order-level metric duplication when joining to reviews; define explicit review aggregation logic.

## F. Next steps and reproducibility

1. Review `docs/olist_profiling.md` and `docs/olist_data_dictionary.md`, especially any schema-field definitions still awaiting verification against local headers.
2. After reviewing the proposed branch and local uncommitted changes, integrate the source profiler + notes into the working branch without overwriting local edits.
3. Introduce data-quality tests for key uniqueness, translated-category coverage, order status/delivery consistency, and join cardinality when implementing M2/M3.
4. Re-run commands against the same local Kaggle CSV snapshot when investigating changed results. The profiler emits file hashes to identify a source snapshot; results here refer to the user's 2026-10-25 local execution.

**Evidence standard:** Console outputs were supplied by the user from local execution; these results have not been independently recomputed against the user's local CSVs by a GitHub runner.
