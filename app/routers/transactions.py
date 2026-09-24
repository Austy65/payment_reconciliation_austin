from datetime import datetime
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.config import settings
from app.schemas.schemas import PaginatedTransactions, TransactionDetail
from app.services.transaction_service import list_transactions, get_transaction_detail

router = APIRouter(prefix="/transactions", tags=["Transactions"])

VALID_STATUSES = {"initiated", "processed", "failed", "settled"}
VALID_SORT_FIELDS = {"created_at", "updated_at", "amount", "status"}


@router.get(
    "",
    response_model=PaginatedTransactions,
    summary="List transactions",
    description="Filterable, sortable, paginated list of transactions.",
)
def get_transactions(
    db: Session = Depends(get_db),
    merchant_id: str | None = Query(None, description="Filter by merchant ID"),
    status: str | None = Query(None, description="Filter by status: initiated | processed | failed | settled"),
    from_date: datetime | None = Query(None, description="ISO 8601 lower bound on created_at"),
    to_date: datetime | None = Query(None, description="ISO 8601 upper bound on created_at"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        settings.PAGE_SIZE_DEFAULT,
        ge=1,
        le=settings.PAGE_SIZE_MAX,
        description="Results per page",
    ),
):
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}",
        )
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort_by '{sort_by}'. Must be one of: {sorted(VALID_SORT_FIELDS)}",
        )
    return list_transactions(
        db=db,
        merchant_id=merchant_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetail,
    summary="Fetch transaction detail",
    description="Returns full transaction detail including event history.",
)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    result = get_transaction_detail(db, transaction_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found.",
        )
    return result
