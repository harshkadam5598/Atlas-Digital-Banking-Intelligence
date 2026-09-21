"""Atlas – Growth Intelligence Hub API. See growth_service.py for logic."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.api.v1.base import make_hub_router
from backend.app.core.exceptions import InvalidParameterError
from backend.app.schemas.envelope import envelope
from backend.app.services import growth_service

router = make_hub_router(prefix="/growth", tag="Growth")


@router.get("/funnel", summary="Registration-to-transaction funnel")
def get_funnel(as_of: Optional[date] = None) -> dict:
    data = growth_service.get_funnel(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/cac-by-channel", summary="Customer acquisition cost by channel")
def get_cac_by_channel(as_of: Optional[date] = None) -> dict:
    data = growth_service.get_cac_by_channel(as_of=as_of)
    return envelope(data, as_of_date=data["as_of"])


@router.get("/activation-trend", summary="Activation rate trend")
def get_activation_trend(months: int = 6, as_of: Optional[date] = None) -> dict:
    if months < 1 or months > 24:
        raise InvalidParameterError("months must be between 1 and 24")
    data = growth_service.get_activation_trend(months=months, as_of=as_of)
    return envelope(data)
