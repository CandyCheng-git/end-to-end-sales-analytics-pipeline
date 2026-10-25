# Portfolio roadmap (not yet implemented)

1. **Verify full reproducibility:** run the Conda and Docker workflows locally; record command output and known platform constraints. Add end-to-end CI integration tests.
2. **Build dashboard:** import `data/processed/daily_sales.csv` into Power BI, add a screenshot under `docs/images/` (only after the report exists), and commit Power BI project files if appropriate.
3. **Move to Databricks:** ingest the same synthetic data into Delta tables; document Bronze → Silver → Gold design. Avoid claiming the migration is complete until demonstrated.
4. **Improve modelling:** replace basic current-state dimensions with defensible keys, historisation rules and SCD Type 2 where needed.
5. **Production concerns:** add incremental loads, checkpoints, late-arriving event logic, run observability, retries, secret management and data reconciliation.

## CV integrity rule

Describe only completed, tested features. The Conda + Docker + DuckDB starter by itself is **not** evidence that a Databricks platform or Power BI dashboard has been built.
