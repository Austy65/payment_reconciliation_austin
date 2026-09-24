import pytest
from tests.conftest import BASE_EVENT


def test_ingest_event_created(client):
    resp = client.post("/events", json=BASE_EVENT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "created"
    assert data["event_id"] == "evt-001"


def test_ingest_event_idempotent(client):
    """Submitting the same event_id twice must return 'duplicate' without error."""
    r1 = client.post("/events", json=BASE_EVENT)
    r2 = client.post("/events", json=BASE_EVENT)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["status"] == "created"
    assert r2.json()["status"] == "duplicate"


def test_ingest_invalid_event_type(client):
    bad = {**BASE_EVENT, "event_type": "refunded"}
    resp = client.post("/events", json=bad)
    assert resp.status_code == 422


def test_ingest_missing_field(client):
    bad = {k: v for k, v in BASE_EVENT.items() if k != "merchant_id"}
    resp = client.post("/events", json=bad)
    assert resp.status_code == 422


def test_transaction_status_advances(client):
    """Status should advance from initiated → processed, not regress."""
    client.post("/events", json=BASE_EVENT)  # initiated

    processed = {
        **BASE_EVENT,
        "event_id": "evt-002",
        "event_type": "payment_processed",
        "timestamp": "2026-03-01T10:05:00+00:00",
    }
    client.post("/events", json=processed)

    resp = client.get("/transactions/txn-001")
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"


def test_transaction_status_settled(client):
    """Full flow: initiated → processed → settled."""
    for evt in [
        {**BASE_EVENT, "event_id": "e1", "event_type": "payment_initiated",  "timestamp": "2026-03-01T10:00:00+00:00"},
        {**BASE_EVENT, "event_id": "e2", "event_type": "payment_processed",  "timestamp": "2026-03-01T10:01:00+00:00"},
        {**BASE_EVENT, "event_id": "e3", "event_type": "settled",            "timestamp": "2026-03-01T10:02:00+00:00"},
    ]:
        client.post("/events", json=evt)

    resp = client.get("/transactions/txn-001")
    assert resp.json()["status"] == "settled"


def test_status_does_not_regress(client):
    """A later 'initiated' event must not downgrade status from 'processed'."""
    client.post("/events", json={**BASE_EVENT, "event_id": "e1", "event_type": "payment_initiated"})
    client.post("/events", json={**BASE_EVENT, "event_id": "e2", "event_type": "payment_processed",
                                 "timestamp": "2026-03-01T10:01:00+00:00"})
    # Late-arriving duplicate of initiated with a new event_id
    client.post("/events", json={**BASE_EVENT, "event_id": "e3", "event_type": "payment_initiated",
                                 "timestamp": "2026-03-01T09:59:00+00:00"})

    resp = client.get("/transactions/txn-001")
    assert resp.json()["status"] == "processed"


def test_negative_amount_rejected(client):
    bad = {**BASE_EVENT, "amount": -500}
    resp = client.post("/events", json=bad)
    assert resp.status_code == 422
