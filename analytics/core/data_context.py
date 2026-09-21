"""
Atlas Analytics — Data Context

Single abstraction every engine uses to obtain warehouse tables.
Decouples KPI/Insight/Decision/Forecast/Anomaly engines from the storage
backend so Sprint 6 can swap in a live PostgreSQL-backed implementation
without touching engine code.

Two backends:
  - ParquetDataContext  : reads data/staging/*.parquet (works today, no DB)
  - SQLDataContext      : reads warehouse.* via SQLAlchemy (Sprint 6+)

Both implement the same DataContext protocol, so:
    ctx = get_data_context()
    df  = ctx.get("fact_transactions")
works identically regardless of backend.
"""

from __future__ import annotations

import abc
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Protocol

import pandas as pd
from loguru import logger

STAGING_DIR = Path("data/staging")

TABLE_NAMES = (
    "dim_customer",
    "fact_customer_journey",
    "fact_transactions",
    "fact_product_events",
    "fact_revenue",
    "fact_marketing",
    "fact_support",
    "fact_kyc_events",
)


class DataContext(Protocol):
    """Protocol every analytics data backend must satisfy."""

    def get(self, table: str) -> pd.DataFrame:
        """Return the full DataFrame for a warehouse table."""
        ...

    def as_of(self) -> date:
        """Return the effective 'today' date the engines should treat as current."""
        ...


class ParquetDataContext:
    """
    Reads warehouse-equivalent tables from data/staging/*.parquet.
    This is the Sprint 5 default backend — staging output from the ETL
    pipeline already carries surrogate keys and is fully typed, so it is
    a faithful stand-in for the warehouse schema without requiring a
    live PostgreSQL connection.

    Tables are cached in-memory after first read (per-instance cache).
    Date columns are normalised to pandas Timestamp on load.
    """

    _DATE_COLUMNS: Dict[str, list] = {
        "dim_customer": [
            "signup_date", "kyc_submission_date", "kyc_completion_date",
            "activation_date", "first_transaction_date", "premium_upgrade_date",
            "last_activity_date", "churn_date",
        ],
        "fact_customer_journey": [
            "signup_date", "kyc_submission_date", "kyc_completion_date",
            "activation_date", "first_transaction_date", "premium_upgrade_date",
            "churn_date",
        ],
        "fact_transactions": ["transaction_date"],
        "fact_product_events": ["event_date"],
        "fact_revenue": ["revenue_date"],
        "fact_marketing": ["touchpoint_date", "conversion_date"],
        "fact_support": ["created_date", "resolved_date"],
        "fact_kyc_events": ["submission_date", "completion_date"],
    }

    def __init__(self, staging_dir: Path = STAGING_DIR,
                 as_of_date: Optional[date] = None):
        self.staging_dir = Path(staging_dir)
        self._cache: Dict[str, pd.DataFrame] = {}
        # Effective "today" for all engines = max activity date in the
        # dataset, unless explicitly overridden. This makes KPI windows
        # (DAU/WAU/MAU, MoM growth) behave correctly against synthetic
        # historical data instead of relative to the real wall-clock date.
        self._as_of_override = as_of_date

    def get(self, table: str) -> pd.DataFrame:
        if table not in TABLE_NAMES:
            raise ValueError(f"Unknown table '{table}'. Valid: {TABLE_NAMES}")
        if table in self._cache:
            return self._cache[table]

        path = self.staging_dir / f"{table}.parquet"
        if not path.exists():
            logger.warning(f"[DataContext] {path} not found — returning empty DataFrame")
            df = pd.DataFrame()
        else:
            df = pd.read_parquet(path)
            for col in self._DATE_COLUMNS.get(table, []):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

        self._cache[table] = df
        return df

    def as_of(self) -> date:
        if self._as_of_override:
            return self._as_of_override
        txn = self.get("fact_transactions")
        if len(txn) and "transaction_date" in txn.columns:
            max_date = txn["transaction_date"].max()
            if pd.notna(max_date):
                return max_date.date()
        return date.today()

    def refresh(self, table: Optional[str] = None) -> None:
        """Clear cache for one table, or all tables if none specified."""
        if table:
            self._cache.pop(table, None)
        else:
            self._cache.clear()


class SQLDataContext:
    """
    Reads warehouse.* tables via a SQLAlchemy engine.
    Placeholder for Sprint 6 — defined now so engines can be written
    against the DataContext protocol without depending on a concrete backend.
    """

    def __init__(self, engine, as_of_date: Optional[date] = None):
        self.engine = engine
        self._cache: Dict[str, pd.DataFrame] = {}
        self._as_of_override = as_of_date

    def get(self, table: str) -> pd.DataFrame:
        if table not in TABLE_NAMES:
            raise ValueError(f"Unknown table '{table}'. Valid: {TABLE_NAMES}")
        if table in self._cache:
            return self._cache[table]
        df = pd.read_sql_table(table, self.engine, schema="warehouse")
        self._cache[table] = df
        return df

    def as_of(self) -> date:
        if self._as_of_override:
            return self._as_of_override
        return date.today()

    def refresh(self, table: Optional[str] = None) -> None:
        if table:
            self._cache.pop(table, None)
        else:
            self._cache.clear()


_default_context: Optional[DataContext] = None


def get_data_context() -> DataContext:
    """Return the process-wide default DataContext (lazily constructed)."""
    global _default_context
    if _default_context is None:
        _default_context = ParquetDataContext()
        logger.info(
            f"[DataContext] Using ParquetDataContext "
            f"(as_of={_default_context.as_of()})"
        )
    return _default_context


def set_data_context(ctx: DataContext) -> None:
    """Override the process-wide default DataContext (used by tests / Sprint 6)."""
    global _default_context
    _default_context = ctx
