"""
Atlas – Operations Intelligence API

Implements the six Sprint 6 Operations endpoints:
    GET /operations/summary
    GET /operations/kpis
    GET /operations/kyc
    GET /operations/fraud
    GET /operations/support
    GET /operations/transactions

All business logic stays in analytics/kpis/operations_kpis.py and
analytics/anomaly/anomaly_engine.py — this module only validates
request params, calls backend/app/services/operations_service.py, and
wraps the result in the standard envelope. No new KPI or analytics
logic was added; registry.py was not modified for this module (all six
Operations KPIs were already registered in the Sprint 5 baseline).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.schemas.envelope import envelope
from backend.app.services import operations_service

router = make_hub_router(prefix="/operations", tag="Operations")


@router.get("/summary", summary="Operations intelligence summary")
def get_summary(as_of: Optional[date] = None) -> dict:
    data = operations_service.get_summary(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get("/kpis", summary="All operations-domain KPIs")
def get_all_kpis(as_of: Optional[date] = None) -> dict:
    data = operations_service.get_all_kpis(as_of=as_of)
    return envelope(data)


@router.get(
    "/kyc",
    summary="KYC approval rate, processing time, and delay anomalies",
    description=(
        "Composes kyc_approval_rate, kyc_processing_time, and "
        "analytics.anomaly.anomaly_engine.detect_kyc_delay_anomalies() "
        "— no new KYC business logic."
    ),
)
def get_kyc(as_of: Optional[date] = None) -> dict:
    data = operations_service.get_kyc(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get(
    "/fraud",
    summary="Fraud rate and fraud anomalies",
    description=(
        "Composes fraud_rate and "
        "analytics.anomaly.anomaly_engine.detect_fraud_anomalies() — "
        "no new fraud-scoring logic."
    ),
)
def get_fraud(as_of: Optional[date] = None) -> dict:
    data = operations_service.get_fraud(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get(
    "/support",
    summary="Support resolution time and CSAT",
    description="Composes support_resolution_time and csat — both already include priority/tier breakdowns.",
)
def get_support(as_of: Optional[date] = None) -> dict:
    data = operations_service.get_support(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get(
    "/transactions",
    summary="Failed transaction rate and transaction-failure anomalies",
    description=(
        "Composes failed_transaction_rate and "
        "analytics.anomaly.anomaly_engine.detect_transaction_failure_anomalies() "
        "— no new transaction-analysis logic."
    ),
)
def get_transactions(as_of: Optional[date] = None) -> dict:
    data = operations_service.get_transactions(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])
