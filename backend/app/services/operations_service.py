"""
Atlas – Operations Service

Orchestration layer for the Operations Intelligence API. Every number
traces to a real function in analytics/kpis/operations_kpis.py or
analytics/anomaly/anomaly_engine.py — no new formulas are computed
here, and no registry changes were made.

All six requested Operations capabilities were verified present before
implementation (see the prior analysis turn):
  - kyc_approval_rate, kyc_processing_time    -> operations_kpis.py
  - fraud_rate                                -> operations_kpis.py
  - support_resolution_time, csat             -> operations_kpis.py
  - failed_transaction_rate                   -> operations_kpis.py
  - detect_fraud_anomalies                    -> anomaly_engine.py
  - detect_kyc_delay_anomalies                -> anomaly_engine.py
  - detect_transaction_failure_anomalies      -> anomaly_engine.py

No genuine capability gap was found for this module — unlike Growth,
no analytics addition was needed.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.anomaly.anomaly_engine import (
    detect_fraud_anomalies,
    detect_kyc_delay_anomalies,
    detect_transaction_failure_anomalies,
)
from analytics.kpis.registry import compute, compute_all


def get_summary(as_of: Optional[date] = None) -> dict:
    kyc = compute("kyc_approval_rate", as_of=as_of)
    fraud = compute("fraud_rate", as_of=as_of)
    support = compute("support_resolution_time", as_of=as_of)
    satisfaction = compute("csat", as_of=as_of)
    failed_txn = compute("failed_transaction_rate", as_of=as_of)

    return {
        "kyc_approval_rate": kyc.value,
        "fraud_rate": fraud.value,
        "support_resolution_time": support.value,
        "csat": satisfaction.value,
        "failed_transaction_rate": failed_txn.value,
        "as_of_date": kyc.as_of.isoformat(),
    }


def get_all_kpis(as_of: Optional[date] = None) -> dict:
    results = compute_all(as_of=as_of, domain="operations")
    return {
        "domain": "operations",
        "count": len(results),
        "kpis": {name: r.to_dict() for name, r in results.items()},
    }


def get_kyc(as_of: Optional[date] = None) -> dict:
    approval = compute("kyc_approval_rate", as_of=as_of)
    processing_time = compute("kyc_processing_time", as_of=as_of)
    anomalies = detect_kyc_delay_anomalies()
    return {
        "kyc_approval_rate": approval.to_dict(),
        "kyc_processing_time": processing_time.to_dict(),
        "anomalies": [a.to_dict() for a in anomalies],
        "as_of_date": approval.as_of.isoformat(),
    }


def get_fraud(as_of: Optional[date] = None) -> dict:
    rate = compute("fraud_rate", as_of=as_of)
    anomalies = detect_fraud_anomalies()
    return {
        "fraud_rate": rate.to_dict(),
        "anomalies": [a.to_dict() for a in anomalies],
        "as_of_date": rate.as_of.isoformat(),
    }


def get_support(as_of: Optional[date] = None) -> dict:
    resolution = compute("support_resolution_time", as_of=as_of)
    satisfaction = compute("csat", as_of=as_of)
    return {
        "support_resolution_time": resolution.to_dict(),
        "csat": satisfaction.to_dict(),
        "as_of_date": resolution.as_of.isoformat(),
    }


def get_transactions(as_of: Optional[date] = None) -> dict:
    failed_rate = compute("failed_transaction_rate", as_of=as_of)
    anomalies = detect_transaction_failure_anomalies()
    return {
        "failed_transaction_rate": failed_rate.to_dict(),
        "anomalies": [a.to_dict() for a in anomalies],
        "as_of_date": failed_rate.as_of.isoformat(),
    }
