# Setu Payment Reconciliation Service

Production-minded FastAPI + PostgreSQL backend for ingesting payment lifecycle events, maintaining transaction/reconciliation state, and exposing operations APIs.

## Demo Links

- API Base URL: `https://paymen-rec-austin-production.up.railway.app` - This is a blank page (Use the swagger Docs to test the API)
- Swagger Docs: `https://paymen-rec-austin-production.up.railway.app/docs`
- Health Check: `https://paymen-rec-austin-production.up.railway.app/health`
- Demo Recording: `ADD_YOUR_VIDEO_LINK_HERE` - update

## Architecture Overview

Event ingestion writes to normalized tables and computes reconciliation state on every new event:

1. Validate inbound payload with Pydantic.
2. Upsert merchant.
3. Insert event using `event_id` as the idempotency key.
4. Upsert/advance transaction status using precedence rules.
5. Recompute reconciliation row for the transaction.

Read endpoints are optimized for operations workflows:

- `GET /transactions`: filter + sort + pagination in SQL.
- `GET /transactions/{transaction_id}`: transaction + merchant + ordered event history.
- `GET /reconciliation/summary`: grouped aggregate by merchant/date/status.
- `GET /reconciliation/discrepancies`: indexed retrieval of inconsistent transactions.

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Pydantic v2
- Pytest
- Docker / Docker Compose
- Railway

## Data Model

Core entities:

- `merchants`
- `transactions`
- `events`
- `reconciliation`

### Key Design Choices

- **Idempotency:** `events.event_id` is the primary key and canonical dedupe key.
- **State handling:** transaction status only advances by rank:
  - `settled (3) > processed (2) > failed (1) > initiated (0)`
- **Reconciliation on write:** discrepancies are precomputed and stored for fast reads.

### Indexing Strategy

- `transactions`: `(merchant_id, status, created_at)`, `created_at`, `status`
- `events`: `transaction_id`, `event_type`, `timestamp`
- `reconciliation`: `is_discrepant`, `payment_status`, `settlement_status`

## Idempotency Behavior

`POST /events` is idempotent by `event_id`.

- First submission -> `{"status":"created", ...}`
- Repeat same `event_id` -> `{"status":"duplicate", ...}`
- Duplicate inserts do not corrupt transaction state or event history.

## Reconciliation Rules

A transaction is marked discrepant when any of the following are true:

1. Payment processed but never settled.
2. Settlement recorded for a failed payment.
3. Both `payment_processed` and `payment_failed` exist for the same transaction.

## API Reference

### 1) Ingest Events

- **POST** `/events`
- Accepts event types:
  - `payment_initiated`
  - `payment_processed`
  - `payment_failed`
  - `settled`

Example request:

```json
{
  "event_id": "b768e3a7-9eb3-4603-b21c-a54cc95661bc",
  "event_type": "payment_initiated",
  "transaction_id": "2f86e94c-239c-4302-9874-75f28e3474ee",
  "merchant_id": "merchant_2",
  "merchant_name": "FreshBasket",
  "amount": 15248.29,
  "currency": "INR",
  "timestamp": "2026-01-08T12:11:58.085567+00:00"
}
```

### 2) List Transactions

- **GET** `/transactions`
- Supports:
  - `merchant_id`
  - `status` (`initiated|processed|failed|settled`)
  - `from_date`, `to_date`
  - `sort_by` (`created_at|updated_at|amount|status`)
  - `sort_dir` (`asc|desc`)
  - `page`, `page_size`

### 3) Fetch Transaction Details

- **GET** `/transactions/{transaction_id}`
- Returns:
  - transaction fields
  - current status
  - merchant details
  - full event history

### 4) Reconciliation Summary

- **GET** `/reconciliation/summary`
- Optional filters:
  - `merchant_id`
  - `from_date` (`YYYY-MM-DD`)
  - `to_date` (`YYYY-MM-DD`)

### 5) Reconciliation Discrepancies

- **GET** `/reconciliation/discrepancies`
- Optional filters:
  - `merchant_id`
  - `reason`
  - `page`, `page_size`

## Local Setup (Incase Railway hosted App doesn't work)

### Option A: Full Docker Compose

```bash
docker compose up --build
```

### Option B: API local (venv) + Postgres in Docker

1. Start DB:

```bash
docker compose up -d db
```

2. Create and activate venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/setu_recon
APP_ENV=development
```

4. Run API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Verify:

```bash
curl http://localhost:8000/health
open http://localhost:8000/docs
```

## Sample Data

- `sample_events.json` is included and contains high-volume mixed scenarios.
- Dataset includes successful flows, failed flows, duplicates, and discrepancy seeds.

Seed command:

```bash
python scripts/seed.py --url http://localhost:8000 --file sample_events.json
```

## Testing

Run:

```bash
pytest
```

Current automated coverage includes:

- event ingestion + idempotency
- status advancement/non-regression
- transaction list filters/pagination/sorting
- transaction detail history
- reconciliation summary/discrepancy logic

Test count in repository: **25** (`8 + 9 + 8` across events, transactions, reconciliation suites).

## Deployment (Railway)

`railway.toml` is configured with:

- Dockerfile build
- start command: `python start.py`
- health check path: `/health`

```bash
python scripts/seed.py --url https://YOUR-RAILWAY-URL
```

## Assumptions and Tradeoffs

- Synchronous SQLAlchemy was chosen for clarity and assignment speed.
- Reconciliation is computed on write, making discrepancy reads fast.
- `Base.metadata.create_all()` is used for local/dev simplicity (Alembic recommended for production).
- Tests run on SQLite in-memory for speed and no external dependency.

## AI Usage Disclosure

AI assistance (Claude) was used for drafting and iteration support. Final implementation logic, API behavior, and test expectations were reviewed and validated manually.
