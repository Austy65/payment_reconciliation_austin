from tests.conftest import BASE_EVENT


def _post(client, **overrides):
    client.post("/events", json={**BASE_EVENT, **overrides})


def test_summary_empty(client):
    resp = client.get("/reconciliation/summary")
    assert resp.status_code == 200
    assert resp.json()["total_rows"] == 0


def test_summary_after_events(client):
    _post(client, event_id="e1", transaction_id="txn-1")
    resp = client.get("/reconciliation/summary")
    assert resp.status_code == 200
    assert resp.json()["total_rows"] >= 1


def test_summary_filter_by_merchant(client):
    _post(client, event_id="e1", transaction_id="txn-1", merchant_id="merchant_1", merchant_name="QuickMart")
    _post(client, event_id="e2", transaction_id="txn-2", merchant_id="merchant_2", merchant_name="FreshBasket")

    resp = client.get("/reconciliation/summary?merchant_id=merchant_1")
    data = resp.json()
    assert all(r["merchant_id"] == "merchant_1" for r in data["results"])


def test_discrepancies_empty(client):
    # Clean successful flow — no discrepancy
    for evt in [
        {**BASE_EVENT, "event_id": "e1", "event_type": "payment_initiated",  "timestamp": "2026-03-01T10:00:00+00:00"},
        {**BASE_EVENT, "event_id": "e2", "event_type": "payment_processed",  "timestamp": "2026-03-01T10:01:00+00:00"},
        {**BASE_EVENT, "event_id": "e3", "event_type": "settled",            "timestamp": "2026-03-01T10:02:00+00:00"},
    ]:
        client.post("/events", json=evt)

    resp = client.get("/reconciliation/discrepancies")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_discrepancy_processed_not_settled(client):
    """processed but never settled → discrepant."""
    _post(client, event_id="e1", transaction_id="txn-ps", event_type="payment_initiated",
          timestamp="2026-03-01T10:00:00+00:00")
    _post(client, event_id="e2", transaction_id="txn-ps", event_type="payment_processed",
          timestamp="2026-03-01T10:01:00+00:00")

    resp = client.get("/reconciliation/discrepancies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "processed but never settled" in data["results"][0]["discrepancy_reason"]


def test_discrepancy_settled_on_failed(client):
    """settled after failed → discrepant."""
    _post(client, event_id="f1", transaction_id="txn-sf", event_type="payment_initiated",
          timestamp="2026-03-01T10:00:00+00:00")
    _post(client, event_id="f2", transaction_id="txn-sf", event_type="payment_failed",
          timestamp="2026-03-01T10:01:00+00:00")
    _post(client, event_id="f3", transaction_id="txn-sf", event_type="settled",
          timestamp="2026-03-01T10:02:00+00:00")

    resp = client.get("/reconciliation/discrepancies")
    data = resp.json()
    assert data["total"] >= 1
    reasons = [r["discrepancy_reason"] for r in data["results"]]
    assert any("failed payment" in r for r in reasons)


def test_discrepancy_conflicting_events(client):
    """Both processed and failed on same txn → discrepant."""
    _post(client, event_id="c1", transaction_id="txn-cf", event_type="payment_initiated",
          timestamp="2026-03-01T10:00:00+00:00")
    _post(client, event_id="c2", transaction_id="txn-cf", event_type="payment_processed",
          timestamp="2026-03-01T10:01:00+00:00")
    _post(client, event_id="c3", transaction_id="txn-cf", event_type="payment_failed",
          timestamp="2026-03-01T10:02:00+00:00")

    resp = client.get("/reconciliation/discrepancies")
    data = resp.json()
    reasons = [r["discrepancy_reason"] for r in data["results"]
               if r["transaction_id"] == "txn-cf"]
    assert any("conflicting" in r for r in reasons)


def test_discrepancy_pagination(client):
    # Create 5 processed-not-settled transactions
    for i in range(5):
        _post(client, event_id=f"p{i}a", transaction_id=f"txn-pg-{i}", event_type="payment_initiated",
              timestamp=f"2026-03-{i+1:02d}T10:00:00+00:00")
        _post(client, event_id=f"p{i}b", transaction_id=f"txn-pg-{i}", event_type="payment_processed",
              timestamp=f"2026-03-{i+1:02d}T10:01:00+00:00")

    resp = client.get("/reconciliation/discrepancies?page=1&page_size=2")
    data = resp.json()
    assert data["total"] == 5
    assert len(data["results"]) == 2
