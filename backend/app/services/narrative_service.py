"""
Atlas – Narrative Service. Orchestrates insight_engine/decision_engine/
anomaly_engine — no narrative-generation logic here; headlines/rationale
come from the engines' own output types.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.anomaly.anomaly_engine import detect_all_anomalies
from analytics.core.types import Severity
from analytics.decision.decision_engine import generate_recommendations
from analytics.insights.insight_engine import (
    generate_executive_insights, generate_opportunity_insights, generate_risk_insights,
)

_SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}


def get_insights(category: str = "all", max_insights: int = 10, as_of: Optional[date] = None) -> dict:
    if category == "risk":
        insights = generate_risk_insights(as_of=as_of)[:max_insights]
    elif category == "opportunity":
        insights = generate_opportunity_insights(as_of=as_of)[:max_insights]
    else:
        insights = generate_executive_insights(as_of=as_of, max_insights=max_insights)
    return {"category": category, "count": len(insights), "insights": [i.to_dict() for i in insights]}


def get_risk_summary(as_of: Optional[date] = None) -> dict:
    risk_insights = generate_risk_insights(as_of=as_of)
    anomalies = sorted(detect_all_anomalies(), key=lambda a: _SEVERITY_ORDER.get(a.severity, 99))
    risk_recommendations = [r for r in generate_recommendations(as_of=as_of) if r.category == "risk"]
    return {
        "risk_insight_count": len(risk_insights),
        "anomaly_count": len(anomalies),
        "risk_recommendation_count": len(risk_recommendations),
        "risk_insights": [i.to_dict() for i in risk_insights],
        "anomalies": [a.to_dict() for a in anomalies],
        "risk_recommendations": [r.to_dict() for r in risk_recommendations],
    }


def get_briefing(max_insights: int = 5, max_recommendations: int = 5, as_of: Optional[date] = None) -> dict:
    all_insights = generate_executive_insights(as_of=as_of, max_insights=max_insights)
    all_recommendations = generate_recommendations(as_of=as_of)[:max_recommendations]
    risk_count = sum(1 for i in all_insights if i.is_risk)
    opportunity_count = sum(1 for i in all_insights if i.is_opportunity)
    return {
        "insight_count": len(all_insights),
        "risk_count": risk_count,
        "opportunity_count": opportunity_count,
        "recommendation_count": len(all_recommendations),
        "top_insights": [i.to_dict() for i in all_insights],
        "top_recommendations": [r.to_dict() for r in all_recommendations],
    }
