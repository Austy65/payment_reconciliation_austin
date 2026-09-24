from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models.models import Transaction, Merchant, Event
from app.schemas.schemas import (
    PaginatedTransactions,
    TransactionSummary,
    TransactionDetail,
    MerchantBrief,
    EventOut,
)


def list_transactions(
    db: Session,
    merchant_id: str | None,
    status: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    sort_by: str,
    sort_dir: str,
    page: int,
    page_size: int,
) -> PaginatedTransactions:
    stmt = (
        select(Transaction, Merchant.merchant_name)
        .join(Merchant, Transaction.merchant_id == Merchant.merchant_id)
    )

    if merchant_id:
        stmt = stmt.where(Transaction.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Transaction.status == status)
    if from_date:
        stmt = stmt.where(Transaction.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.created_at <= to_date)

    # Count before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Sorting
    sort_col = getattr(Transaction, sort_by, Transaction.created_at)
    if sort_dir == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    # Pagination
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(stmt).all()

    results = [
        TransactionSummary(
            transaction_id=tx.transaction_id,
            merchant_id=tx.merchant_id,
            merchant_name=name,
            amount=tx.amount,
            currency=tx.currency,
            status=tx.status,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )
        for tx, name in rows
    ]

    return PaginatedTransactions(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
    )


def get_transaction_detail(db: Session, transaction_id: str) -> TransactionDetail | None:
    stmt = (
        select(Transaction)
        .where(Transaction.transaction_id == transaction_id)
        .options(
            joinedload(Transaction.merchant),
            selectinload(Transaction.events),
        )
    )
    tx = db.execute(stmt).unique().scalar_one_or_none()
    if tx is None:
        return None

    return TransactionDetail(
        transaction_id=tx.transaction_id,
        merchant=MerchantBrief(
            merchant_id=tx.merchant.merchant_id,
            merchant_name=tx.merchant.merchant_name,
        ),
        amount=tx.amount,
        currency=tx.currency,
        status=tx.status,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
        events=[
            EventOut(
                event_id=e.event_id,
                event_type=e.event_type,
                transaction_id=e.transaction_id,
                merchant_id=e.merchant_id,
                amount=e.amount,
                currency=e.currency,
                timestamp=e.timestamp,
                received_at=e.received_at,
            )
            for e in tx.events
        ],
    )
