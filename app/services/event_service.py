"""
Event ingestion service.

State machine:
  initiated → processed → settled
  initiated → failed

Precedence for resolving status when multiple events exist:
  settled > processed > failed > initiated

Idempotency: event_id is the primary key. Duplicate submissions
return status="duplicate" without touching transaction state.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import Event, Merchant, Transaction, Reconciliation
from app.schemas.schemas import EventIn, EventIngestResponse

# Higher rank = higher precedence
STATUS_RANK: dict[str, int] = {
    "initiated": 0,
    "failed": 1,
    "processed": 2,
    "settled": 3,
}

EVENT_TO_STATUS: dict[str, str] = {
    "payment_initiated": "initiated",
    "payment_processed": "processed",
    "payment_failed": "failed",
    "settled": "settled",
}


# def _settlement_status(tx_status: str) -> str:
#     return "settled" if tx_status == "settled" else "pending" if tx_status == "processed" else "none"
def _settlement_status(event_types: set[str]) -> str:
    return "settled" if "settled" in event_types else "none"


# def _discrepancy_reason(payment_status: str, settlement_status: str, event_types: set[str]) -> str | None:
#     reasons = []

#     if payment_status == "failed" and settlement_status == "settled":
#         reasons.append("settlement recorded for a failed payment")

#     if payment_status == "processed" and settlement_status == "none":
#         reasons.append("payment processed but never settled")

#     # Detect conflicting state transitions: both processed and failed events
#     if "payment_processed" in event_types and "payment_failed" in event_types:
#         reasons.append("conflicting events: both processed and failed recorded")

#     return "; ".join(reasons) if reasons else None

def _discrepancy_reason(
    payment_status: str,
    settlement_status: str,
    event_types: set[str],
) -> str | None:
    reasons = []

    if "payment_failed" in event_types and "settled" in event_types:
        reasons.append("settlement recorded for a failed payment")

    if payment_status == "processed" and settlement_status == "none":
        reasons.append("payment processed but never settled")

    if (
        "payment_processed" in event_types
        and "payment_failed" in event_types
    ):
        reasons.append("conflicting events: both processed and failed recorded")

    return "; ".join(reasons) if reasons else None

def ingest_event(db: Session, payload: EventIn) -> EventIngestResponse:
    # Upsert merchant
    merchant = db.get(Merchant, payload.merchant_id)
    if merchant is None:
        merchant = Merchant(
            merchant_id=payload.merchant_id,
            merchant_name=payload.merchant_name,
        )
        db.add(merchant)
        db.flush()

    # Create the event row — primary key uniqueness enforces idempotency
    event = Event(
        event_id=payload.event_id,
        transaction_id=payload.transaction_id,
        merchant_id=payload.merchant_id,
        event_type=payload.event_type,
        amount=float(payload.amount),
        currency=payload.currency,
        timestamp=payload.timestamp,
    )
    try:
        db.add(event)
        db.flush()
    except IntegrityError:
        db.rollback()
        return EventIngestResponse(
            status="duplicate",
            event_id=payload.event_id,
            transaction_id=payload.transaction_id,
        )

    # Upsert transaction
    tx = db.get(Transaction, payload.transaction_id)
    new_status = EVENT_TO_STATUS[payload.event_type]

    if tx is None:
        tx = Transaction(
            transaction_id=payload.transaction_id,
            merchant_id=payload.merchant_id,
            amount=float(payload.amount),
            currency=payload.currency,
            status=new_status,
        )
        db.add(tx)
        db.flush()
    else:
        # Only advance if the new event carries higher precedence
        if STATUS_RANK.get(new_status, 0) > STATUS_RANK.get(tx.status, 0):
            tx.status = new_status
            tx.updated_at = datetime.now(timezone.utc)

    # Recompute reconciliation
    # Fetch all distinct event types for this transaction to detect conflicts
    from sqlalchemy import select, distinct
    event_types_result = db.execute(
        select(distinct(Event.event_type)).where(Event.transaction_id == payload.transaction_id)
    ).scalars().all()
    event_types_set = set(event_types_result)

    payment_status = tx.status
    # settlement_status = _settlement_status(tx.status)
    settlement_status = _settlement_status(event_types_set)
    reason = _discrepancy_reason(payment_status, settlement_status, event_types_set)

    recon = db.get(Reconciliation, payload.transaction_id)
    if recon is None:
        recon = Reconciliation(
            transaction_id=payload.transaction_id,
            payment_status=payment_status,
            settlement_status=settlement_status,
            is_discrepant=bool(reason),
            discrepancy_reason=reason,
        )
        db.add(recon)
    else:
        recon.payment_status = payment_status
        recon.settlement_status = settlement_status
        recon.is_discrepant = bool(reason)
        recon.discrepancy_reason = reason
        recon.updated_at = datetime.now(timezone.utc)

    db.commit()
    return EventIngestResponse(
        status="created",
        event_id=payload.event_id,
        transaction_id=payload.transaction_id,
    )
