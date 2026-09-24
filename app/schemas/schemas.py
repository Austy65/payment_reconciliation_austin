from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


# ── Event ──────────────────────────────────────────────────────────────────────

EventType = Literal[
    "payment_initiated",
    "payment_processed",
    "payment_failed",
    "settled",
]


class EventIn(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=64)
    event_type: EventType
    transaction_id: str = Field(..., min_length=1, max_length=64)
    merchant_id: str = Field(..., min_length=1, max_length=64)
    merchant_name: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="INR", max_length=8)
    timestamp: datetime

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, v: str) -> str:
        return v.upper()


class EventOut(BaseModel):
    event_id: str
    event_type: str
    transaction_id: str
    merchant_id: str
    amount: Decimal
    currency: str
    timestamp: datetime
    received_at: datetime

    model_config = {"from_attributes": True}


class EventIngestResponse(BaseModel):
    status: Literal["created", "duplicate"]
    event_id: str
    transaction_id: str


# ── Transaction ────────────────────────────────────────────────────────────────

class MerchantBrief(BaseModel):
    merchant_id: str
    merchant_name: str

    model_config = {"from_attributes": True}


class TransactionSummary(BaseModel):
    transaction_id: str
    merchant_id: str
    merchant_name: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionDetail(BaseModel):
    transaction_id: str
    merchant: MerchantBrief
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    events: list[EventOut]

    model_config = {"from_attributes": True}


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[TransactionSummary]


# ── Reconciliation ─────────────────────────────────────────────────────────────

class ReconciliationSummaryRow(BaseModel):
    merchant_id: str
    merchant_name: str
    date: str          # YYYY-MM-DD
    status: str
    transaction_count: int
    total_amount: Decimal

    model_config = {"from_attributes": True}


class ReconciliationSummaryResponse(BaseModel):
    total_rows: int
    results: list[ReconciliationSummaryRow]


class DiscrepancyRow(BaseModel):
    transaction_id: str
    merchant_id: str
    merchant_name: str
    amount: Decimal
    currency: str
    status: str
    payment_status: str
    settlement_status: str
    discrepancy_reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscrepancyResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[DiscrepancyRow]
