"""M2 ingestion integration tests using tiny generated CSV fixtures (no Kaggle data)."""

import csv
from pathlib import Path

import duckdb
import pytest

from scripts import ingest_olist as loader


@pytest.fixture
def olist_sources(tmp_path: Path) -> Path:
    root = tmp_path / "olist"
    root.mkdir()
    for filename, (_, headers) in loader.SOURCE_SCHEMAS.items():
        values = [f"sample_{column}" for column in headers]
        for i, column in enumerate(headers):
            if column.endswith("zip_code_prefix"):
                values[i] = "00007"
            elif column == "review_comment_message":
                values[i] = "Arrived, thank you!\nSecond line"
        with (root / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerow(values)
    return root


def test_loads_all_nine_tables_and_audits_source_counts(
    olist_sources: Path, tmp_path: Path
) -> None:
    db_path = tmp_path / "warehouse" / "sales.duckdb"
    result = loader.ingest_olist(olist_sources, db_path)
    assert len(result) == 9
    assert sum(record["rows"] for record in result) == 9

    with duckdb.connect(str(db_path)) as conn:
        for filename, (table, headers) in loader.SOURCE_SCHEMAS.items():
            assert conn.execute(f'SELECT COUNT(*) FROM bronze."{table}"').fetchone()[0] == 1
            actual_columns = [
                row[0] for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'bronze' AND table_name = ? "
                    "ORDER BY ordinal_position",
                    [table],
                ).fetchall()
            ]
            assert actual_columns == list(headers), filename
        assert conn.execute(
            "SELECT COUNT(*) FROM bronze.olist_ingestion_audit"
        ).fetchone()[0] == 9
        assert conn.execute(
            "SELECT COUNT(DISTINCT run_id) FROM bronze.olist_ingestion_audit"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT customer_zip_code_prefix FROM bronze.olist_customers"
        ).fetchone()[0] == "00007"
        assert conn.execute(
            "SELECT review_comment_message FROM bronze.olist_order_reviews"
        ).fetchone()[0] == "Arrived, thank you!\nSecond line"
        assert conn.execute(
            "SELECT COUNT(*) FROM bronze.olist_ingestion_audit "
            "WHERE source_row_count = bronze_row_count AND length(source_sha256) = 64"
        ).fetchone()[0] == 9


def test_rerun_replaces_bronze_rows_without_duplication(
    olist_sources: Path, tmp_path: Path
) -> None:
    db_path = tmp_path / "sales.duckdb"
    loader.ingest_olist(olist_sources, db_path)
    loader.ingest_olist(olist_sources, db_path)

    with duckdb.connect(str(db_path)) as conn:
        for table, _ in loader.SOURCE_SCHEMAS.values():
            assert conn.execute(f'SELECT COUNT(*) FROM bronze."{table}"').fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM bronze.olist_ingestion_audit"
        ).fetchone()[0] == 18
        assert conn.execute(
            "SELECT COUNT(DISTINCT run_id) FROM bronze.olist_ingestion_audit"
        ).fetchone()[0] == 2


def test_missing_file_rejected_before_database_created(
    olist_sources: Path, tmp_path: Path
) -> None:
    (olist_sources / "olist_sellers_dataset.csv").unlink()
    db_path = tmp_path / "sales.duckdb"
    with pytest.raises(ValueError, match="Missing Olist source file"):
        loader.ingest_olist(olist_sources, db_path)
    assert not db_path.exists()


def test_unexpected_headers_rejected(
    olist_sources: Path, tmp_path: Path
) -> None:
    path = olist_sources / "olist_orders_dataset.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["wrong_header"])
        writer.writerow(["abc"])
    db_path = tmp_path / "sales.duckdb"
    with pytest.raises(ValueError, match="unexpected headers"):
        loader.ingest_olist(olist_sources, db_path)
    assert not db_path.exists()


def test_malformed_record_rejected_instead_of_silently_dropped(
    olist_sources: Path, tmp_path: Path
) -> None:
    path = olist_sources / "olist_orders_dataset.csv"
    with path.open("a", encoding="utf-8", newline="") as stream:
        stream.write("broken,short\n")
    db_path = tmp_path / "sales.duckdb"
    with pytest.raises(ValueError, match="malformed CSV record"):
        loader.ingest_olist(olist_sources, db_path)
    assert not db_path.exists()


def test_failed_refresh_rolls_back_and_preserves_synthetic_pipeline(
    olist_sources: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "sales.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute("CREATE SCHEMA bronze")
        conn.execute("CREATE TABLE bronze.raw_sales (source VARCHAR)")
        conn.execute("INSERT INTO bronze.raw_sales VALUES ('synthetic')")

    loader.ingest_olist(olist_sources, db_path)

    original_sha256 = loader.sha256_file
    checks = 0

    def simulate_changed_source(path: Path) -> str:
        nonlocal checks
        checks += 1
        # First nine checks are preflight; the first source is loaded before
        # this forced hash mismatch on the second source.
        if checks == len(loader.SOURCE_SCHEMAS) + 2:
            return "0" * 64
        return original_sha256(path)

    monkeypatch.setattr(loader, "sha256_file", simulate_changed_source)
    with pytest.raises(ValueError, match="source changed during ingestion"):
        loader.ingest_olist(olist_sources, db_path)

    with duckdb.connect(str(db_path)) as conn:
        assert conn.execute(
            "SELECT source FROM bronze.raw_sales"
        ).fetchone()[0] == "synthetic"
        assert conn.execute(
            "SELECT COUNT(*) FROM bronze.olist_ingestion_audit"
        ).fetchone()[0] == 9
        for table, _ in loader.SOURCE_SCHEMAS.values():
            assert conn.execute(f'SELECT COUNT(*) FROM bronze."{table}"').fetchone()[0] == 1
