"""
Atlas ETL – Main Pipeline Entry Point
Sprint 4: Complete Extract → Transform → Load → Validate pipeline.

Usage:
    python -m etl.pipeline                     # full run
    python -m etl.pipeline --dry-run           # transform only, skip DB load
    python -m etl.pipeline --source-version v001_20240115_seed42
    python -m etl.pipeline --list-versions     # show available datasets
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from etl.core.context import ETLContext
from etl.core.versioning import (
    get_latest_version, get_raw_version, get_version_by_id,
    list_versions, promote_to_raw, snapshot_raw_to_version,
)
from etl.extractors.extract import extract_all
from etl.transformers.transform import transform_all
from etl.loaders.load import check_db_available, load_all
from etl.validators.validate import validate_all

REPORTS_DIR = Path("etl/reports")
STAGING_DIR = Path("data/staging")


def _configure_logging(run_id: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
    log_path = Path("logs") / f"etl_{run_id}.log"
    log_path.parent.mkdir(exist_ok=True)
    logger.add(log_path, level="DEBUG",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


def _print_report(ctx: ETLContext) -> None:
    r = ctx.build_report()
    s = r["summary"]
    print("\n" + "=" * 64)
    print("  ATLAS ETL EXECUTION REPORT")
    print("=" * 64)
    print(f"  Run ID:            {r['run_id']}")
    print(f"  Source Version:    {r['source_version']}")
    print(f"  Status:            {r['overall_status']}")
    print(f"  Elapsed:           {r['elapsed_seconds']:.1f}s")
    print(f"  DQ Score:          {r['data_quality_score']}/100")
    print()
    print(f"  Rows Extracted:    {s['rows_extracted']:>10,}")
    print(f"  Rows Transformed:  {s['rows_transformed']:>10,}")
    print(f"  Rows Loaded:       {s['rows_loaded']:>10,}")
    print(f"  Rows Rejected:     {s['rows_rejected']:>10,}")
    print(f"  DQ Checks Passed:  {s['dq_checks_passed']:>10,}")
    print(f"  DQ Checks Failed:  {s['dq_checks_failed']:>10,}")
    print()
    print("  Stage Summary:")
    for name, st in r["stages"].items():
        status = "PASS" if st["status"] == "PASS" else "FAIL"
        print(f"    {name:<28} {st['rows_in']:>7,} → {st['rows_out']:>7,}  "
              f"{st['duration_s']:>6.2f}s  [{status}]")
    if r["warnings"]:
        print(f"\n  Warnings ({len(r['warnings'])}):")
        for w in r["warnings"][:10]:
            print(f"    ⚠ {w}")
        if len(r["warnings"]) > 10:
            print(f"    ... and {len(r['warnings'])-10} more")
    if r["errors"]:
        print(f"\n  Errors ({len(r['errors'])}):")
        for e in r["errors"]:
            print(f"    ✗ {e}")
    print("=" * 64)


def run_pipeline(raw_dir: Path,
                  source_version: str,
                  dry_run: bool = False,
                  save_staging: bool = True) -> ETLContext:
    """Execute the complete ETL pipeline. Returns the run context."""
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    _configure_logging(run_id)

    ctx = ETLContext(
        run_id=run_id,
        source_version=source_version,
        raw_dir=raw_dir,
        staging_dir=STAGING_DIR,
    )

    logger.info("=" * 64)
    logger.info("ATLAS ETL PIPELINE — Sprint 4")
    logger.info(f"Run ID:          {run_id}")
    logger.info(f"Source version:  {source_version}")
    logger.info(f"Raw dir:         {raw_dir}")
    logger.info(f"Mode:            {'DRY-RUN' if dry_run else 'FULL'}")
    logger.info("=" * 64)

    # ── Check DB ──────────────────────────────────────────────────────────────
    db_ok = False if dry_run else check_db_available()
    if not db_ok and not dry_run:
        ctx.warn("PostgreSQL not reachable — running in dry-run mode")
        logger.warning("DB unavailable — pipeline will transform but not load")

    # ── Extract ───────────────────────────────────────────────────────────────
    raw_tables = extract_all(ctx)
    if not raw_tables:
        ctx.error("Extract returned no tables — aborting")
        return ctx

    # ── Transform ─────────────────────────────────────────────────────────────
    transformed, rejects = transform_all(raw_tables, ctx)

    # Save staging (cleaned parquet before DB load) — always, regardless of DB
    if save_staging:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        for table, df in transformed.items():
            df.to_parquet(STAGING_DIR / f"{table}.parquet", index=False)
        logger.info(f"[STAGING] {len(transformed)} tables written to {STAGING_DIR}")
        ctx.log_audit("staging", "write", sum(len(v) for v in transformed.values()),
                      f"parquet files in {STAGING_DIR}")

    # Save reject log
    if rejects:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        reject_df = pd.DataFrame(rejects)
        reject_path = STAGING_DIR / f"rejects_{run_id}.parquet"
        reject_df.to_parquet(reject_path, index=False)
        logger.info(f"[STAGING] {len(rejects):,} rejected rows → {reject_path}")

    # ── Load ──────────────────────────────────────────────────────────────────
    loaded_counts = load_all(transformed, ctx, db_available=db_ok)

    # ── Validate ──────────────────────────────────────────────────────────────
    validate_all(transformed, loaded_counts, ctx, db_available=db_ok)

    # ── Report ────────────────────────────────────────────────────────────────
    report_path = ctx.write_report(REPORTS_DIR)
    _print_report(ctx)
    logger.success(f"Report written → {report_path}")

    return ctx


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlas ETL Pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Transform only; skip DB load")
    parser.add_argument("--source-version", type=str, default=None,
                        help="Version ID to process (default: latest)")
    parser.add_argument("--list-versions", action="store_true",
                        help="List available dataset versions and exit")
    parser.add_argument("--snapshot", action="store_true",
                        help="Snapshot current data/raw/ into versions/ before running")
    args = parser.parse_args()

    if args.list_versions:
        versions = list_versions()
        if not versions:
            print("No versioned datasets found in data/versions/")
            print("Run: python -m etl.extractors.pipeline_orchestrator to generate data")
        else:
            print(f"\n{'Version ID':<50} {'Created':<22} {'Rows'}")
            print("-" * 90)
            for v in versions:
                rc = v.get("row_counts", {})
                total = sum(rc.values()) if rc else 0
                print(f"  {v['version_id']:<48} {v.get('created_at','')[:19]:<22} {total:,}")
        return

    # Resolve source directory
    if args.snapshot:
        vdir = snapshot_raw_to_version(seed=42, label="pre_etl")
        source_version = vdir.name
        raw_dir = Path("data/raw")
    elif args.source_version:
        vdir = get_version_by_id(args.source_version)
        if not vdir:
            print(f"Version not found: {args.source_version}")
            sys.exit(1)
        promote_to_raw(vdir)
        raw_dir = Path("data/raw")
        source_version = args.source_version
    else:
        raw_dir = Path("data/raw")
        source_version = get_raw_version() or "unversioned_raw"

    ctx = run_pipeline(
        raw_dir=raw_dir,
        source_version=source_version,
        dry_run=args.dry_run,
    )
    sys.exit(0 if ctx.overall_status != "FAILED" else 1)


if __name__ == "__main__":
    main()
