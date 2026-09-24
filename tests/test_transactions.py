import pytest
from tests.conftest import BASE_EVENT


def _seed(client, n=5):
    """Seed n distinct transactions for merchant_1."""
    for i in range(n):
        client.post("/events", json={
            **BASE_EVENT,
            "event_id": f"e-{i}",
            "transaction_id": f"txn-{i:03d}",
            "timestamp": f"2026-03-{i+1:02d}T10:00:00+00:00",
        })


def test_list_transactions_empty(client):
    resp = client.get("/transactions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_transactions(client):
    _seed(client, 5)
    resp = client.get("/transactions")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


def test_filter_by_merchant(client):
    _seed(client, 3)
    # Add one for merchant_2
    client.post("/events", json={
        **BASE_EVENT,
        "event_id": "e-m2",
        "transaction_id": "txn-m2",
        "merchant_id": "merchant_2",
        "merchant_name": "FreshBasket",
    })
    resp = client.get("/transactions?merchant_id=merchant_2")
    data = resp.json()
    assert data["total"] == 1
    assert data["results"][0]["merchant_id"] == "merchant_2"


def test_filter_by_status(client):
    _seed(client, 3)
    # Advance txn-000 to processed
    client.post("/events", json={
        **BASE_EVENT,
        "event_id": "e-p",
        "event_type": "payment_processed",
        "transaction_id": "txn-000",
        "timestamp": "2026-03-01T10:05:00+00:00",
    })
    resp = client.get("/transactions?status=processed")
    data = resp.json()
    assert data["total"] == 1
    assert data["results"][0]["transaction_id"] == "txn-000"


def test_invalid_status_filter(client):
    resp = client.get("/transactions?status=refunded")
    assert resp.status_code == 422


def test_pagination(client):
    _seed(client, 10)
    resp = client.get("/transactions?page=1&page_size=3")
    data = resp.json()
    assert data["total"] == 10
    assert len(data["results"]) == 3
    assert data["page"] == 1


def test_get_transaction_detail(client):
    client.post("/events", json=BASE_EVENT)
    resp = client.get("/transactions/txn-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_id"] == "txn-001"
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "payment_initiated"


def test_get_transaction_not_found(client):
    resp = client.get("/transactions/does-not-exist")
    assert resp.status_code == 404


def test_event_history_preserved(client):
    """All events for a transaction appear in the detail, duplicates excluded."""
    for evt in [
        {**BASE_EVENT, "event_id": "e1", "event_type": "payment_initiated",  "timestamp": "2026-03-01T10:00:00+00:00"},
        {**BASE_EVENT, "event_id": "e2", "event_type": "payment_processed",  "timestamp": "2026-03-01T10:01:00+00:00"},
        # duplicate of e1 — should not appear twice
        {**BASE_EVENT, "event_id": "e1", "event_type": "payment_initiated",  "timestamp": "2026-03-01T10:00:00+00:00"},
    ]:
        client.post("/events", json=evt)

    resp = client.get("/transactions/txn-001")
    assert resp.status_code == 200
    event_ids = [e["event_id"] for e in resp.json()["events"]]
    assert len(event_ids) == 2  # e1 and e2 only
    assert event_ids.count("e1") == 1
