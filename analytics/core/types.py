"""
Atlas Analytics — Shared Types

Typed result structures used across every engine (KPI, Insight, Decision,
Forecast, Anomaly). Centralising these avoids duplicated dataclass
definitions and gives Sprint 6 API layer one stable contract to serialise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class Trend(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class KPIResult:
    """
    Standard output of every KPI calculation function.

    `value` is the headline number. `breakdown` carries optional
    dimensional cuts (by product, country, segment) as nested dicts so
    the Insight Engine can attribute "what changed" without recomputing.
    """
    name: str
    value: float
    unit: str                              # "count", "gbp", "percent", "ratio", "days", "hours"
    as_of: date
    period_label: str = ""                 # e.g. "2024-12", "last_30_days"
    previous_value: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    trend: Optional[Trend] = None
    breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.previous_value is not None and self.delta is None:
            self.delta = round(self.value - self.previous_value, 4)
            if self.previous_value != 0:
                self.delta_pct = round(
                    100 * self.delta / abs(self.previous_value), 2
                )
            if self.trend is None:
                if self.delta > 0:
                    self.trend = Trend.UP
                elif self.delta < 0:
                    self.trend = Trend.DOWN
                else:
                    self.trend = Trend.FLAT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "as_of": self.as_of.isoformat(),
            "period_label": self.period_label,
            "previous_value": self.previous_value,
            "delta": self.delta,
            "delta_pct": self.delta_pct,
            "trend": self.trend.value if self.trend else None,
            "breakdown": self.breakdown,
            "metadata": self.metadata,
        }


@dataclass
class Insight:
    """Output of the Executive Insight Engine — explains a KPI movement."""
    headline: str                          # "Premium revenue grew 12.3% in December"
    category: str                          # "revenue", "customer", "product", "operations"
    direction: Trend
    magnitude_pct: float
    primary_driver: str                    # "FX_STANDARD product adoption in GB"
    contributing_factors: List[str] = field(default_factory=list)
    supporting_kpis: List[str] = field(default_factory=list)
    is_opportunity: bool = False
    is_risk: bool = False
    confidence: str = "medium"             # "low", "medium", "high"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "category": self.category,
            "direction": self.direction.value,
            "magnitude_pct": self.magnitude_pct,
            "primary_driver": self.primary_driver,
            "contributing_factors": self.contributing_factors,
            "supporting_kpis": self.supporting_kpis,
            "is_opportunity": self.is_opportunity,
            "is_risk": self.is_risk,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Recommendation:
    """Output of the Decision Intelligence Engine."""
    title: str                             # "Increase Premium marketing to high-FX users"
    rationale: str
    supporting_kpis: List[str]
    estimated_impact: str                  # qualitative + quantitative if available
    priority: Priority
    category: str                          # "growth", "retention", "operations", "risk"
    rule_id: str                           # traceable rule that fired this recommendation
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "rationale": self.rationale,
            "supporting_kpis": self.supporting_kpis,
            "estimated_impact": self.estimated_impact,
            "priority": self.priority.value,
            "category": self.category,
            "rule_id": self.rule_id,
            "metadata": self.metadata,
        }


@dataclass
class ForecastPoint:
    period: str                            # "2025-01"
    predicted_value: float
    lower_bound: float
    upper_bound: float


@dataclass
class ForecastResult:
    """Output of the Forecast Engine."""
    metric: str                            # "revenue", "customer_growth", etc.
    method: str                            # "linear_trend", "moving_average", "exponential_smoothing"
    historical: List[Dict[str, Any]]       # [{period, actual}, ...]
    forecast: List[ForecastPoint]
    accuracy_note: str                     # plain-language interpretability note
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "method": self.method,
            "historical": self.historical,
            "forecast": [
                {
                    "period": f.period,
                    "predicted_value": f.predicted_value,
                    "lower_bound": f.lower_bound,
                    "upper_bound": f.upper_bound,
                }
                for f in self.forecast
            ],
            "accuracy_note": self.accuracy_note,
            "metadata": self.metadata,
        }


@dataclass
class Anomaly:
    """Output of the Anomaly Detection Engine."""
    metric: str                            # "revenue", "fraud_rate", "kyc_processing_time"
    detected_at: date
    severity: Severity
    observed_value: float
    expected_value: float
    deviation_pct: float
    detection_reason: str                  # "3-sigma z-score breach on weekly revenue"
    business_impact: str
    suggested_investigation: str
    dimension: Optional[str] = None        # e.g. "country=PL" if dimension-scoped
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity.value,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "deviation_pct": self.deviation_pct,
            "detection_reason": self.detection_reason,
            "business_impact": self.business_impact,
            "suggested_investigation": self.suggested_investigation,
            "dimension": self.dimension,
            "metadata": self.metadata,
        }
