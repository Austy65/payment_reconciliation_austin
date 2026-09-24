# from sqlalchemy import text, func, select
# from sqlalchemy.orm import Session

# from app.models.models import Transaction, Merchant, Reconciliation
# from app.schemas.schemas import (
#     ReconciliationSummaryResponse,
#     ReconciliationSummaryRow,
#     DiscrepancyResponse,
#     DiscrepancyRow,
# )


# def get_summary(
#     db: Session,
#     merchant_id: str | None,
#     from_date: str | None,
#     to_date: str | None,
# ) -> ReconciliationSummaryResponse:
#     """
#     Aggregate transaction counts and amounts grouped by merchant, date, and status.
#     All aggregation happens in SQL.
#     """
#     sql = text("""
#         SELECT
#             t.merchant_id,
#             m.merchant_name,
#             DATE(t.created_at AT TIME ZONE 'UTC') AS date,
#             t.status,
#             COUNT(*)                               AS transaction_count,
#             SUM(t.amount)                          AS total_amount
#         FROM transactions t
#         JOIN merchants m ON m.merchant_id = t.merchant_id
#         WHERE (:merchant_id IS NULL OR t.merchant_id = :merchant_id)
#           AND (:from_date  IS NULL OR DATE(t.created_at AT TIME ZONE 'UTC') >= CAST(:from_date AS DATE))
#           AND (:to_date    IS NULL OR DATE(t.created_at AT TIME ZONE 'UTC') <= CAST(:to_date AS DATE))
#         GROUP BY t.merchant_id, m.merchant_name, DATE(t.created_at AT TIME ZONE 'UTC'), t.status
#         ORDER BY date DESC, t.merchant_id, t.status
#     """)

#     rows = db.execute(sql, {
#         "merchant_id": merchant_id,
#         "from_date": from_date,
#         "to_date": to_date,
#     }).mappings().all()

#     results = [
#         ReconciliationSummaryRow(
#             merchant_id=r["merchant_id"],
#             merchant_name=r["merchant_name"],
#             date=str(r["date"]),
#             status=r["status"],
#             transaction_count=r["transaction_count"],
#             total_amount=r["total_amount"],
#         )
#         for r in rows
#     ]

#     return ReconciliationSummaryResponse(total_rows=len(results), results=results)


# def get_discrepancies(
#     db: Session,
#     merchant_id: str | None,
#     reason_filter: str | None,
#     page: int,
#     page_size: int,
# ) -> DiscrepancyResponse:
#     """
#     Return transactions where payment state and settlement state are inconsistent.
#     Filters to rows where reconciliation.is_discrepant = TRUE.
#     """
#     base_sql = """
#         FROM reconciliation r
#         JOIN transactions t  ON t.transaction_id  = r.transaction_id
#         JOIN merchants m     ON m.merchant_id      = t.merchant_id
#         WHERE r.is_discrepant = TRUE
#           AND (:merchant_id IS NULL OR t.merchant_id = :merchant_id)
#           AND (:reason_filter IS NULL OR r.discrepancy_reason ILIKE '%' || :reason_filter || '%')
#     """

#     count_sql = text(f"SELECT COUNT(*) {base_sql}")
#     total = db.execute(count_sql, {
#         "merchant_id": merchant_id,
#         "reason_filter": reason_filter,
#     }).scalar_one()

#     data_sql = text(f"""
#         SELECT
#             t.transaction_id,
#             t.merchant_id,
#             m.merchant_name,
#             t.amount,
#             t.currency,
#             t.status,
#             r.payment_status,
#             r.settlement_status,
#             r.discrepancy_reason,
#             t.created_at
#         {base_sql}
#         ORDER BY t.created_at DESC
#         LIMIT :limit OFFSET :offset
#     """)

#     rows = db.execute(data_sql, {
#         "merchant_id": merchant_id,
#         "reason_filter": reason_filter,
#         "limit": page_size,
#         "offset": (page - 1) * page_size,
#     }).mappings().all()

#     results = [
#         DiscrepancyRow(
#             transaction_id=r["transaction_id"],
#             merchant_id=r["merchant_id"],
#             merchant_name=r["merchant_name"],
#             amount=r["amount"],
#             currency=r["currency"],
#             status=r["status"],
#             payment_status=r["payment_status"],
#             settlement_status=r["settlement_status"],
#             discrepancy_reason=r["discrepancy_reason"],
#             created_at=r["created_at"],
#         )
#         for r in rows
#     ]

#     return DiscrepancyResponse(
#         total=total,
#         page=page,
#         page_size=page_size,
#         results=results,
#     )

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.schemas import (
    ReconciliationSummaryResponse,
    ReconciliationSummaryRow,
    DiscrepancyResponse,
    DiscrepancyRow,
)


def get_summary(
    db: Session,
    merchant_id: str | None,
    from_date: str | None,
    to_date: str | None,
) -> ReconciliationSummaryResponse:
    """
    Aggregate transaction counts and amounts grouped by merchant, date, and status.
    All aggregation happens in SQL.
    """

    sql = text("""
        SELECT
            t.merchant_id,
            m.merchant_name,
            DATE(t.created_at) AS date,
            t.status,
            COUNT(*) AS transaction_count,
            SUM(t.amount) AS total_amount
        FROM transactions t
        JOIN merchants m ON m.merchant_id = t.merchant_id
        WHERE (:merchant_id IS NULL OR t.merchant_id = :merchant_id)
          AND (:from_date IS NULL OR DATE(t.created_at) >= DATE(:from_date))
          AND (:to_date IS NULL OR DATE(t.created_at) <= DATE(:to_date))
        GROUP BY
            t.merchant_id,
            m.merchant_name,
            DATE(t.created_at),
            t.status
        ORDER BY date DESC, t.merchant_id, t.status
    """)

    rows = db.execute(
        sql,
        {
            "merchant_id": merchant_id,
            "from_date": from_date,
            "to_date": to_date,
        },
    ).mappings().all()

    results = [
        ReconciliationSummaryRow(
            merchant_id=r["merchant_id"],
            merchant_name=r["merchant_name"],
            date=str(r["date"]),
            status=r["status"],
            transaction_count=r["transaction_count"],
            total_amount=r["total_amount"],
        )
        for r in rows
    ]

    return ReconciliationSummaryResponse(
        total_rows=len(results),
        results=results,
    )


def get_discrepancies(
    db: Session,
    merchant_id: str | None,
    reason_filter: str | None,
    page: int,
    page_size: int,
) -> DiscrepancyResponse:
    """
    Return transactions where payment state and settlement state are inconsistent.
    Filters to rows where reconciliation.is_discrepant = TRUE.
    """

    base_sql = """
        FROM reconciliation r
        JOIN transactions t
            ON t.transaction_id = r.transaction_id
        JOIN merchants m
            ON m.merchant_id = t.merchant_id
        WHERE r.is_discrepant = TRUE
          AND (:merchant_id IS NULL OR t.merchant_id = :merchant_id)
          AND (
              :reason_filter IS NULL
              OR LOWER(r.discrepancy_reason)
                 LIKE LOWER('%' || :reason_filter || '%')
          )
    """

    count_sql = text(f"""
        SELECT COUNT(*)
        {base_sql}
    """)

    total = db.execute(
        count_sql,
        {
            "merchant_id": merchant_id,
            "reason_filter": reason_filter,
        },
    ).scalar_one()

    data_sql = text(f"""
        SELECT
            t.transaction_id,
            t.merchant_id,
            m.merchant_name,
            t.amount,
            t.currency,
            t.status,
            r.payment_status,
            r.settlement_status,
            r.discrepancy_reason,
            t.created_at
        {base_sql}
        ORDER BY t.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    rows = db.execute(
        data_sql,
        {
            "merchant_id": merchant_id,
            "reason_filter": reason_filter,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
    ).mappings().all()

    results = [
        DiscrepancyRow(
            transaction_id=r["transaction_id"],
            merchant_id=r["merchant_id"],
            merchant_name=r["merchant_name"],
            amount=r["amount"],
            currency=r["currency"],
            status=r["status"],
            payment_status=r["payment_status"],
            settlement_status=r["settlement_status"],
            discrepancy_reason=r["discrepancy_reason"],
            created_at=r["created_at"],
        )
        for r in rows
    ]

    return DiscrepancyResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
    )