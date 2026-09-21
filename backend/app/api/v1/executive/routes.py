"""Atlas – Executive Command Center API. See executive_service.py for logic."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.schemas.envelope import envelope
from backend.app.services import executive_service

router = make_hub_router(prefix="/executive", tag="Executive")


@router.get("/kpis", summary="Executive KPI summary")
def get_executive_kpis(as_of: Optional[date] = None) -> dict:
    data = executive_service.get_executive_kpis(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get("/health-score", summary="Composite business health score")
def get_health_score(as_of: Optional[date] = None) -> dict:
    data = executive_service.get_health_score_components(as_of=as_of)
    return envelope(data, as_of_date=data["as_of_date"])


@router.get("/risk-alerts", summary="Active risk alerts, sorted by severity")
def get_risk_alerts() -> dict:
    alerts = executive_service.get_risk_alerts()
    return envelope([a.to_dict() for a in alerts])
