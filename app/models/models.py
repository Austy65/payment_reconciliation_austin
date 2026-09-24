from datetime import datetime, timezone
from sqlalchemy import (
    String, Numeric, DateTime, Boolean, Text, ForeignKey,
    UniqueConstraint, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="merchant")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("merchants.merchant_id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    # Canonical status: initiated | processed | failed | settled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="initiated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")
    events: Mapped[list["Event"]] = relationship(back_populates="transaction", order_by="Event.timestamp")
    reconciliation: Mapped["Reconciliation"] = relationship(back_populates="transaction", uselist=False)

    __table_args__ = (
        Index("ix_transactions_merchant_status_created", "merchant_id", "status", "created_at"),
        Index("ix_transactions_created_at", "created_at"),
        Index("ix_transactions_status", "status"),
    )


class Event(Base):
    __tablename__ = "events"

    # event_id is the canonical idempotency key — must be unique
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("transactions.transaction_id"), nullable=False
    )
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    transaction: Mapped["Transaction"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_events_transaction_id", "transaction_id"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_timestamp", "timestamp"),
    )


class Reconciliation(Base):
    __tablename__ = "reconciliation"

    transaction_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("transactions.transaction_id"), primary_key=True
    )
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    # settled  | none
    settlement_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    is_discrepant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discrepancy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    transaction: Mapped["Transaction"] = relationship(back_populates="reconciliation")

    __table_args__ = (
        Index("ix_reconciliation_discrepant", "is_discrepant"),
        Index("ix_reconciliation_payment_status", "payment_status"),
        Index("ix_reconciliation_settlement_status", "settlement_status"),
    )
