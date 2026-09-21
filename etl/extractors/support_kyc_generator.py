"""
Atlas – Support Ticket & KYC Event Generator
Support: 130,000 tickets across 37% of activated customers
KYC: 560,000 events (500K submissions + 60K resubmissions)
"""

from datetime import date, timedelta
from typing import Any, Dict, List

import numpy as np

from etl.extractors.config import CONFIG, GenerationConfig
from etl.extractors.seed_manager import get_customer_rng

ISSUE_TYPES = [
    ("transaction_dispute", 0.28),
    ("card_issue",          0.22),
    ("account_access",      0.18),
    ("kyc_query",           0.12),
    ("fee_complaint",       0.08),
    ("fraud_report",        0.06),
    ("product_question",    0.04),
    ("other",               0.02),
]
ISSUE_CODES   = [i[0] for i in ISSUE_TYPES]
ISSUE_WEIGHTS = [i[1] for i in ISSUE_TYPES]

REJECTION_REASONS = [
    "identity_mismatch", "address_unverifiable", "sanctions_match",
    "document_expired", "poor_image_quality", "pep_match",
]


def generate_support_tickets(customer: Dict[str, Any],
                              config: GenerationConfig) -> List[Dict[str, Any]]:
    """
    Generate 0 or more support tickets for a customer.
    Only 37% of activated customers raise tickets (amended from 88%).
    """
    cid = customer["customer_id"]
    activation_date = customer.get("activation_date")
    is_premium = customer["premium_status"]
    churn_date = customer.get("churn_date")
    end_date = date(2024, 12, 31)

    if not activation_date:
        return []

    rng = get_customer_rng(cid, "support", config.master_seed)

    # 37% of activated customers raise any ticket
    if rng.random() > config.support_ticket_customer_pct:
        return []

    active_days = (min(churn_date or end_date, end_date) - activation_date).days
    # Ticket count: Poisson, average 1.8 tickets for those who raise any
    ticket_count = max(1, round(rng.poisson(1.8)))
    tickets = []

    for _ in range(ticket_count):
        # Ticket date: random within active window
        day_offset = int(rng.integers(0, max(1, active_days)))
        created_date = activation_date + timedelta(days=day_offset)
        if created_date > end_date:
            continue

        issue_type = str(rng.choice(ISSUE_CODES, p=ISSUE_WEIGHTS))

        # Priority
        if is_premium:
            priority = str(rng.choice(["P1", "P2", "P3"], p=[0.40, 0.45, 0.15]))
        else:
            priority = str(rng.choice(["P1", "P2", "P3"], p=[0.08, 0.52, 0.40]))

        # Resolution time (hours)
        if priority == "P1":
            resolution_hours = max(0.5, rng.lognormal(mean=1.2, sigma=0.6))
        elif priority == "P2":
            resolution_hours = max(1.0, rng.lognormal(mean=2.8, sigma=0.7))
        else:
            resolution_hours = max(2.0, rng.lognormal(mean=3.8, sigma=0.8))

        # First response (subset of resolution time)
        first_response_hours = max(0.1, resolution_hours * rng.uniform(0.05, 0.30))

        # Status
        if rng.random() < 0.91:
            status = "resolved"
            resolved_date = created_date + timedelta(hours=resolution_hours)
        else:
            status = str(rng.choice(["open", "in_progress"], p=[0.3, 0.7]))
            resolved_date = None

        # CSAT (only for resolved, 82% rate)
        satisfaction_score = None
        if status == "resolved" and rng.random() < 0.82:
            # Premium customers score higher on average
            if is_premium:
                satisfaction_score = int(rng.choice([3, 4, 5], p=[0.10, 0.35, 0.55]))
            else:
                satisfaction_score = int(rng.choice([1, 2, 3, 4, 5], p=[0.05, 0.10, 0.20, 0.35, 0.30]))

        tickets.append({
            "customer_id":            cid,
            "country_code":           customer["country_code"],
            "created_date":           created_date,
            "resolved_date":          resolved_date,
            "issue_type":             issue_type,
            "priority":               priority,
            "status":                 status,
            "channel":                str(rng.choice(["chat", "email", "phone", "in_app"],
                                                      p=[0.45, 0.25, 0.15, 0.15])),
            "resolution_time_hours":  round(float(resolution_hours), 2),
            "first_response_time_hrs":round(float(first_response_hours), 2),
            "satisfaction_score":     satisfaction_score,
            "is_premium_customer":    is_premium,
        })

    return tickets


def generate_kyc_events(customer: Dict[str, Any],
                         config: GenerationConfig) -> List[Dict[str, Any]]:
    """
    Generate KYC submission events.
    Approved/pending: 1 submission.
    Rejected: 1–2 resubmissions possible (60% retry once, 30% retry twice).
    """
    cid = customer["customer_id"]
    kyc_status = customer["kyc_status"]
    kyc_submission_date = customer.get("kyc_submission_date")
    kyc_completion_date = customer.get("kyc_completion_date")

    if not kyc_submission_date:
        return []

    rng = get_customer_rng(cid, "kyc_events", config.master_seed)
    events = []

    def _make_event(submission_date, outcome, attempt, processing_hours=None,
                    is_resubmission=False, rejection_reason=None):
        return {
            "customer_id":         cid,
            "country_code":        customer["country_code"],
            "submission_date":     submission_date,
            "completion_date":     (submission_date + timedelta(hours=processing_hours)
                                    if processing_hours else None),
            "kyc_type":            "standard",
            "outcome":             outcome,
            "rejection_reason":    rejection_reason,
            "processing_time_hours": round(float(processing_hours), 2) if processing_hours else None,
            "is_resubmission":     is_resubmission,
            "attempt_number":      attempt,
        }

    if kyc_status in ("approved", "pending"):
        proc_hours = max(0.5, rng.lognormal(mean=2.2, sigma=0.9))
        events.append(_make_event(
            kyc_submission_date, kyc_status, 1,
            proc_hours if kyc_status == "approved" else None
        ))
    else:
        # Rejected: initial submission
        proc_hours_1 = max(0.5, rng.lognormal(mean=2.5, sigma=0.8))
        reason_1 = str(rng.choice(REJECTION_REASONS))
        events.append(_make_event(kyc_submission_date, "rejected", 1,
                                   proc_hours_1, False, reason_1))

        # 60% retry once
        if rng.random() < 0.60:
            days_gap = int(rng.integers(1, 8))
            sub_date_2 = kyc_submission_date + timedelta(days=days_gap)
            proc_hours_2 = max(0.5, rng.lognormal(mean=2.3, sigma=0.8))
            outcome_2 = "approved" if rng.random() < 0.65 else "rejected"
            reason_2 = None if outcome_2 == "approved" else str(rng.choice(REJECTION_REASONS))
            events.append(_make_event(sub_date_2, outcome_2, 2,
                                       proc_hours_2, True, reason_2))

            # 30% retry a third time if still rejected
            if outcome_2 == "rejected" and rng.random() < 0.30:
                days_gap_3 = int(rng.integers(3, 14))
                sub_date_3 = sub_date_2 + timedelta(days=days_gap_3)
                proc_hours_3 = max(0.5, rng.lognormal(mean=2.1, sigma=0.7))
                outcome_3 = "approved" if rng.random() < 0.55 else "rejected"
                reason_3 = None if outcome_3 == "approved" else str(rng.choice(REJECTION_REASONS))
                events.append(_make_event(sub_date_3, outcome_3, 3,
                                           proc_hours_3, True, reason_3))

    return events
