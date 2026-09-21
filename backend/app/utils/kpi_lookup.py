"""
Atlas – Shared KPI Lookup Helper

Used by any hub router that exposes a generic "/kpis/{name}" single-KPI
lookup endpoint restricted to its own domain (Customer, Product, and
potentially future hubs). Centralised because Customer and Product both
need identical logic: validate the name belongs to the hub's registry
domain, then call the registry, else raise a 404 with a helpful message
listing the valid names for that domain.

This is a thin wrapper around analytics.kpis.registry — it adds no new
KPI logic, only the domain-scoping + 404 behaviour the API layer needs.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.core.types import KPIResult
from analytics.kpis.registry import compute, list_kpis

from backend.app.core.exceptions import ResourceNotFoundError


def compute_in_domain(name: str, domain: str, as_of: Optional[date] = None, **kwargs) -> KPIResult:
    """
    Compute a registered KPI, but only if it belongs to `domain`.
    Raises ResourceNotFoundError (-> 404) for a name that either doesn't
    exist at all or exists in a different domain — e.g. calling
    /product/kpis/churn_rate should 404, not silently return the
    customer-domain churn_rate.
    """
    valid_names = list_kpis(domain)
    if name not in valid_names:
        raise ResourceNotFoundError(
            f"'{name}' is not a {domain}-domain KPI. Available: {valid_names}"
        )
    return compute(name, as_of=as_of, **kwargs)
