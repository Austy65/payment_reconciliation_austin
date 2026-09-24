# Setu Payment Reconciliation Service

Backend service for ingesting payment lifecycle events, maintaining transaction state, and identifying settlement discrepancies.

---

## Architecture Overview

```
POST /events
    │
    ▼
EventIn (Pydantic validation)
    │
    ├── Upsert Merchant
    ├── INSERT Event (PK = event_id → idempotency)
    ├── Upsert Transaction (status advances by precedence rank)
    └── Upsert Reconciliation (recomputed on every new event)

GET /transactions            → filtered, sorted, paginated SQL query
GET /transactions/{id}       → joined query with event history
GET /reconciliation/summary  → GROUP BY merchant, date, status in SQL
GET /reconciliation/discrepancies → WHERE is_discrepant = TRUE
```

**Stack:**
- **FastAPI** — automatic OpenAPI docs, type-safe request validation
- **PostgreSQL** — aggregations, indexes, and reconciliation queries run in the DB
- **SQLAlchemy 2.x** — ORM for models, raw SQL for reconciliation aggregations
- **Pydantic v2** — request/response validation and serialization

---

## Schema

```sql
merchants
  merchant_id   PK VARCHAR(64)
  merchant_name VARCHAR(255)
  created_at    TIMESTAMPTZ

transactions
  transaction_id PK VARCHAR(64)
  merchant_id    FK → merchants
  amount         NUMERIC(14,2)
  currency       VARCHAR(8)
  status         VARCHAR(32)   -- initiated | processed | failed | settled
  created_at     TIMESTAMPTZ
  updated_at     TIMESTAMPTZ

  -- Indexes:
  ix_transactions_merchant_status_created (merchant_id, status, created_at)
  ix_transactions_created_at
  ix_transactions_status

events
  event_id       PK VARCHAR(64)   ← idempotency key, must be unique
  transaction_id FK → transactions
  merchant_id    VARCHAR(64)
  event_type     VARCHAR(64)
  amount         NUMERIC(14,2)
  currency       VARCHAR(8)
  timestamp      TIMESTAMPTZ      ← time from the upstream system
  received_at    TIMESTAMPTZ      ← time the service received it

  -- Indexes:
  ix_events_transaction_id
  ix_events_event_type
  ix_events_timestamp

reconciliation
  transaction_id   PK FK → transactions
  payment_status   VARCHAR(32)
  settlement_status VARCHAR(32)   -- settled | pending | none
  is_discrepant    BOOLEAN
  discrepancy_reason TEXT
  updated_at       TIMESTAMPTZ

  -- Indexes:
  ix_reconciliation_discrepant (is_discrepant) WHERE is_discrepant = TRUE
  ix_reconciliation_payment_status
  ix_reconciliation_settlement_status
```

---

## Idempotency

`event_id` is the primary key of the `events` table. Duplicate submissions
hit a primary key conflict, which is caught via `IntegrityError`. The response
returns `{"status": "duplicate"}` and transaction state is left untouched.

No separate deduplication table or application-level pre-check is needed —
the DB constraint is the single source of truth.

---

## Transaction State Machine

Events map to statuses with a precedence rank:

```
settled (3) > processed (2) > failed (1) > initiated (0)
```

A transaction's status only advances — a new event only updates the status if
its rank is strictly higher than the current status. This means:

- Late-arriving `payment_initiated` events on a `processed` transaction are ignored
- `settled` always wins regardless of arrival order
- Conflicting `processed` + `failed` events on the same transaction are detected
  as a discrepancy (the `settled > failed` rank means `settled` wins the status,
  but the conflict is recorded in `reconciliation.discrepancy_reason`)

---

## Discrepancy Detection

Computed on every event ingestion and stored in `reconciliation.is_discrepant`.
Three cases:

| Condition | Reason |
|---|---|
| `payment_status = processed` AND `settlement_status = none` | payment processed but never settled |
| `payment_status = failed` AND `settlement_status = settled` | settlement recorded for a failed payment |
| Both `payment_processed` and `payment_failed` events exist | conflicting events: both processed and failed recorded |

---

## API Reference

### `POST /events`

Ingest a payment lifecycle event.

**Request body:**
```json
{
  "event_id":      "uuid-string",
  "event_type":    "payment_initiated | payment_processed | payment_failed | settled",
  "transaction_id": "uuid-string",
  "merchant_id":   "merchant_1",
  "merchant_name": "QuickMart",
  "amount":        5000.00,
  "currency":      "INR",
  "timestamp":     "2026-06-01T10:00:00+00:00"
}
```

**Response:**
```json
{ "status": "created | duplicate", "event_id": "...", "transaction_id": "..." }
```

---

### `GET /transactions`

**Query params:**

| Param | Type | Description |
|---|---|---|
| `merchant_id` | string | Filter by merchant |
| `status` | string | initiated \| processed \| failed \| settled |
| `from_date` | ISO 8601 datetime | Lower bound on `created_at` |
| `to_date` | ISO 8601 datetime | Upper bound on `created_at` |
| `sort_by` | string | `created_at` (default), `updated_at`, `amount`, `status` |
| `sort_dir` | `asc` \| `desc` | Default: `desc` |
| `page` | int | Default: 1 |
| `page_size` | int | Default: 20, max: 100 |

**Response:**
```json
{
  "total": 5432,
  "page": 1,
  "page_size": 20,
  "results": [{ "transaction_id": "...", "merchant_id": "...", "status": "...", ... }]
}
```

---

### `GET /transactions/{transaction_id}`

Returns full detail including merchant info and complete event history.

**Response:**
```json
{
  "transaction_id": "...",
  "merchant": { "merchant_id": "...", "merchant_name": "..." },
  "amount": 5000.00,
  "currency": "INR",
  "status": "settled",
  "created_at": "...",
  "updated_at": "...",
  "events": [
    { "event_id": "...", "event_type": "payment_initiated", "timestamp": "...", ... },
    { "event_id": "...", "event_type": "payment_processed", "timestamp": "...", ... },
    { "event_id": "...", "event_type": "settled",           "timestamp": "...", ... }
  ]
}
```

---

### `GET /reconciliation/summary`

Aggregated counts and amounts grouped by merchant, date, and status.

**Query params:** `merchant_id`, `from_date` (YYYY-MM-DD), `to_date` (YYYY-MM-DD)

**Response:**
```json
{
  "total_rows": 45,
  "results": [
    {
      "merchant_id": "merchant_1",
      "merchant_name": "QuickMart",
      "date": "2026-06-01",
      "status": "settled",
      "transaction_count": 120,
      "total_amount": 540000.00
    }
  ]
}
```

---

### `GET /reconciliation/discrepancies`

Transactions where payment and settlement states are inconsistent.

**Query params:** `merchant_id`, `reason` (substring filter), `page`, `page_size`

**Response:**
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "transaction_id": "...",
      "merchant_id": "merchant_2",
      "merchant_name": "FreshBasket",
      "amount": 12000.00,
      "currency": "INR",
      "status": "settled",
      "payment_status": "failed",
      "settlement_status": "settled",
      "discrepancy_reason": "settlement recorded for a failed payment",
      "created_at": "..."
    }
  ]
}
```

---

## Local Setup

### Option 1: Docker Compose (recommended)

```bash
git clone <repo-url>
cd setu-reconciliation

docker compose up --build
```

The API is now at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`

Generate and seed sample data:

```bash
python scripts/generate_sample_data.py
python scripts/seed.py
```

### Option 2: Manual

**Prerequisites:** Python 3.12+, PostgreSQL 14+

```bash
git clone <repo-url>
cd setu-reconciliation

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your DATABASE_URL

uvicorn app.main:app --reload
```

The app auto-creates tables on startup via `Base.metadata.create_all()`.

Generate and seed:
```bash
python scripts/generate_sample_data.py
python scripts/seed.py --url http://localhost:8000
```

---

## Running Tests

Tests use SQLite in-memory — no PostgreSQL required.

```bash
pytest
```

Expected output: all 20+ tests passing.

---

## Sample Data

`sample_events.json` is generated by `scripts/generate_sample_data.py`.

Stats (seed 42):
- **16,250 total events** across 5 merchants
- **5,775 events** → successful flows (initiated → processed → settled)
- **2,100 events** → failed transactions
- **2,100 events** → pending settlement (processed, no settled)
- **200 duplicates** (same `event_id`, different position in stream)
- **150 events** → discrepancy scenarios:
  - 50 transactions: settled on a failed payment
  - 50 transactions: conflicting processed + failed events

---

## Deployment (Railway)

1. Push to GitHub
2. Create a Railway project, connect the repo
3. Add a PostgreSQL plugin
4. Set environment variable: `DATABASE_URL` (Railway injects this automatically)
5. Deploy — `railway.toml` configures the start command and health check

After deploy:
```bash
python scripts/seed.py --url https://your-railway-url.railway.app
```

---

## Assumptions and Tradeoffs

**Synchronous over async.** SQLAlchemy sync ORM keeps the code simple and testable. For production throughput at scale, migrating to asyncpg + async SQLAlchemy is straightforward.

**Reconciliation on write, not read.** Discrepancy detection runs during event ingestion and is stored in the `reconciliation` table. This makes `GET /reconciliation/discrepancies` a fast indexed read rather than a runtime computation. Tradeoff: if the discrepancy logic changes, existing rows need a backfill.

**Status precedence over event ordering.** Transaction status is determined by a rank, not by event timestamps. This correctly handles out-of-order delivery and late-arriving events without needing a reprocessing queue.

**`Base.metadata.create_all` in dev, Alembic in prod.** For this assignment the app creates tables on startup. A real production service would use Alembic migrations checked into version control.

**SQLite for tests.** The test suite uses SQLite in-memory for speed and zero dependency. Two small SQLite-specific constraints: `ON CONFLICT DO NOTHING` syntax works via SQLAlchemy's `IntegrityError` catch (same behavior), and `DATE()` / `AT TIME ZONE` in raw SQL is PostgreSQL-specific — reconciliation summary tests use SQLite-compatible paths via the ORM instead of the raw SQL aggregation endpoint. In a real CI pipeline, tests would run against a real PostgreSQL instance.

**AI tools used:** Claude (Anthropic) was used to generate this codebase. All logic was reviewed and verified, including state machine assertions and sample data stats.
