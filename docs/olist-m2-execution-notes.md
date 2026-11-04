# M2 — Olist Bronze ingestion: local execution and closeout evidence

**Project:** End-to-End Sales Analytics Pipeline  
**Date:** 2026-11-04 (Australia/Melbourne)  
**Milestone:** M2 — Python ingestion and Bronze tables  
**Evidence provenance:** Console logs pasted by Candy from Windows PowerShell with Docker Desktop; the assistant did not access or independently reprocess the local Kaggle CSVs.

## Implementation and source control

- Feature branch: `feat/m2-olist-bronze-ingestion`; initial feature commit `0e46fe7`.
- `docker compose config --services` listed `olist-ingestion` and `pipeline`.
- `docker compose build` built both service images successfully.
- Raw source files remained in local Git-ignored `data/raw/olist/`. No Kaggle CSV files, DuckDB binaries or credentials were committed.
- Nine all-VARCHAR `bronze.olist_*` tables are full-refreshed transactionally; audit history is stored in `bronze.olist_ingestion_audit`.

## Real Olist source load — observed twice

Commands executed:

```powershell
docker compose run --rm olist-ingestion
docker compose run --rm olist-ingestion
```

| Source file | Target Bronze table | First run | Second run |
| --- | --- | ---: | ---: |
| `olist_orders_dataset.csv` | `bronze.olist_orders` | 99,441 | 99,441 |
| `olist_order_items_dataset.csv` | `bronze.olist_order_items` | 112,650 | 112,650 |
| `olist_order_payments_dataset.csv` | `bronze.olist_order_payments` | 103,886 | 103,886 |
| `olist_order_reviews_dataset.csv` | `bronze.olist_order_reviews` | 99,224 | 99,224 |
| `olist_customers_dataset.csv` | `bronze.olist_customers` | 99,441 | 99,441 |
| `olist_products_dataset.csv` | `bronze.olist_products` | 32,951 | 32,951 |
| `olist_sellers_dataset.csv` | `bronze.olist_sellers` | 3,095 | 3,095 |
| `olist_geolocation_dataset.csv` | `bronze.olist_geolocation` | 1,000,163 | 1,000,163 |
| `product_category_name_translation.csv` | `bronze.olist_category_name_translation` | 71 | 71 |
| **Total** | **9 tables** | **1,550,922** | **1,550,922** |

Both runs printed `M2 Bronze full refresh committed: 9 tables; 1,550,922 total rows`. These totals match the M1 row-count snapshot. The equal row counts on rerun and deterministic replacement implementation support the no-accumulation criterion.

## Audit table — observed

The user executed a DuckDB audit query grouped by `run_id`:

```sql
SELECT run_id, COUNT(*) AS files,
       SUM(source_row_count) AS source_rows,
       SUM(bronze_row_count) AS bronze_rows
FROM bronze.olist_ingestion_audit
GROUP BY run_id;
```

| Run ID | Files | Source rows | Bronze rows |
| --- | ---: | ---: | ---: |
| `af67e035-9abd-4f54-b04b-225902f17da0` | 9 | 1,550,922 | 1,550,922 |
| `531dc059-b143-49f1-a5d2-a1cabb11fa47` | 9 | 1,550,922 | 1,550,922 |

Audit confirms that both runs recorded all nine source files, with source and Bronze totals matching. The ingestion script computes SHA256 and rechecks source file content before committing; the supplied audit query did not display the SHA256 values, so a separate byte-for-byte comparison to M1 source hashes is **not evidenced** here.

## Synthetic regression after M2 and Python tests

Following the real-source ingestion, the user closed a competing DBeaver connection that had prevented DuckDB file access, then executed:

```powershell
docker compose run --rm pipeline
```

Observed output:

- `Loaded 11 synthetic rows into ... bronze.raw_sales`.
- Five dbt SQL models built: one view and four tables.
- 17 dbt data tests passed.
- `PASS=22 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=22`.
- `data/processed/daily_sales.csv` exported.

The user also executed `docker compose run --rm pipeline python -m pytest -q` after synchronising the feature branch: **17 passed in 2.13s**. GitHub Actions independently passed all 17 fixture-based tests, but did not ingest the nine original Olist CSV files.

## Operational finding

An initial `Permission denied` opening `data/warehouse/sales.duckdb` occurred while DBeaver was connected. After releasing the competing connection, the synthetic dbt pipeline and audit query succeeded. Avoid simultaneous DuckDB read-write connections from DBeaver and Docker to the same file. The repository resides under OneDrive; file locking/synchronisation deserves caution in future work.

## Scope and limitations

- M2 Bronze ingestion acceptance is evidenced for the local Olist snapshot; no incremental pipeline is claimed.
- Olist Silver transformations, Gold business models, Power BI and Databricks remain unimplemented.
- No raw source records or generated warehouse files are committed or redistributed.
- Source hash values are stored in the local audit table, but not included in the transcript and not independently cross-checked against M1 SHA256 values.
- The full-source Docker execution was validated on Candy's machine, not on GitHub-hosted CI.

**M2 closeout conclusion:** Locally verified and ready for PR review. Merge remains a separate review/approval decision.
