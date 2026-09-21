# Atlas Dataset Versions

Immutable snapshot store for all generated synthetic datasets.

## Directory Structure

```
data/
  versions/
    v001_<timestamp>_seed<N>[_label]/
      metadata.json        ← version ID, seed, row counts, config
      dim_customer.parquet
      fact_transactions.parquet
      fact_product_events.parquet
      fact_revenue.parquet
      fact_customer_journey.parquet
      fact_marketing.parquet
      fact_support.parquet
      fact_kyc_events.parquet
      reproducibility_proof.json
      validation_report.json
  raw/
    .version_pointer.json  ← which version raw/ currently reflects
    *.parquet              ← copy of the promoted version's files
  staging/
    *.parquet              ← ETL transform output (cleaned, typed, enriched)
    rejects_<run_id>.parquet
```

## Version Lifecycle

```
1. Generation:  python -m etl.extractors.pipeline_orchestrator
                  → writes to data/raw/
                  → calls snapshot_raw_to_version() → data/versions/v00N_...

2. ETL reads:   python -m etl.pipeline --dry-run
                  → reads from data/raw/  (stable path)
                  → OR: --source-version v001_... → promotes that version to raw/

3. Version selection:
   python -m etl.pipeline --list-versions
   python -m etl.pipeline --source-version v001_20240115_seed42
   python -m etl.pipeline --snapshot  (snapshots raw/ before running)
```

## Version Metadata Schema

```json
{
  "version_id":        "v001_20240115_143022_seed42_sprint3_approved",
  "created_at":        "2024-01-15T14:30:22.123456",
  "generator_version": "1.2",
  "seed":              42,
  "row_counts": {
    "dim_customer":          2000,
    "fact_transactions":     19399,
    "fact_product_events":   34705,
    "fact_revenue":          17772,
    "fact_customer_journey": 2000,
    "fact_marketing":        2000,
    "fact_support":          1077,
    "fact_kyc_events":       2093
  },
  "source": "snapshot_raw"
}
```

## Rules

1. **Versions are immutable.** Never modify files inside a version directory.
2. **Never delete versions manually.** Use the versioning API.
3. **data/raw/ is always a copy** of the promoted version — never a source of truth.
4. **The ETL always reads from data/raw/**, regardless of which version was promoted.
5. **Staging output is not versioned** — it is regenerated on every ETL run.
