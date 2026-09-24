from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.config import settings
from app.schemas.schemas import ReconciliationSummaryResponse, DiscrepancyResponse
from app.services.reconciliation_service import get_summary, get_discrepancies

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.get(
    "/summary",
    response_model=ReconciliationSummaryResponse,
    summary="Reconciliation summary",
    description=(
        "Aggregated transaction counts and amounts grouped by merchant, date, and status. "
        "Supports optional filtering by merchant and date range."
    ),
)
def reconciliation_summary(
    db: Session = Depends(get_db),
    merchant_id: str | None = Query(None, description="Filter by merchant ID"),
    from_date: str | None = Query(None, description="YYYY-MM-DD lower bound"),
    to_date: str | None = Query(None, description="YYYY-MM-DD upper bound"),
):
    return get_summary(db, merchant_id, from_date, to_date)


@router.get(
    "/discrepancies",
    response_model=DiscrepancyResponse,
    summary="Reconciliation discrepancies",
    description=(
        "Returns transactions where payment state and settlement state are inconsistent. "
        "Examples: payment processed but never settled; settlement recorded for a failed payment; "
        "conflicting events (both processed and failed recorded for the same transaction)."
    ),
)
def reconciliation_discrepancies(
    db: Session = Depends(get_db),
    merchant_id: str | None = Query(None, description="Filter by merchant ID"),
    reason: str | None = Query(None, description="Substring filter on discrepancy reason"),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE_DEFAULT, ge=1, le=settings.PAGE_SIZE_MAX),
):
    return get_discrepancies(db, merchant_id, reason, page, page_size)
