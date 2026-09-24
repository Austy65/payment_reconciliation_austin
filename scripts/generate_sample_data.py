# """
# Generate sample_events.json with ~10,000 events across 5 merchants.

# Scenarios included:
#   - Successful full flows: initiated → processed → settled
#   - Failed transactions: initiated → failed
#   - Pending settlements: initiated → processed (no settled)
#   - Duplicate events: same event_id submitted twice
#   - Inconsistent state: settled recorded for a failed transaction
#   - Orphan events: settled with no prior processed event
# """

# import json
# import random
# import uuid
# from datetime import datetime, timezone, timedelta

# MERCHANTS = [
#     {"merchant_id": "merchant_1", "merchant_name": "QuickMart"},
#     {"merchant_id": "merchant_2", "merchant_name": "FreshBasket"},
#     {"merchant_id": "merchant_3", "merchant_name": "TechZone"},
#     {"merchant_id": "merchant_4", "merchant_name": "StyleHub"},
#     {"merchant_id": "merchant_5", "merchant_name": "FoodCourt"},
# ]

# START_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
# END_DATE = datetime(2026, 9, 1, tzinfo=timezone.utc)
# RANGE_SECONDS = int((END_DATE - START_DATE).total_seconds())


# def rand_ts(base=None, offset_min=1, offset_max=300):
#     if base is None:
#         return START_DATE + timedelta(seconds=random.randint(0, RANGE_SECONDS))
#     return base + timedelta(seconds=random.randint(offset_min, offset_max))


# def make_event(event_id, event_type, transaction_id, merchant, amount, currency, timestamp):
#     return {
#         "event_id": event_id,
#         "event_type": event_type,
#         "transaction_id": transaction_id,
#         "merchant_id": merchant["merchant_id"],
#         "merchant_name": merchant["merchant_name"],
#         "amount": round(amount, 2),
#         "currency": currency,
#         "timestamp": timestamp.isoformat(),
#     }


# def build_events():
#     events = []
#     currencies = ["INR"] * 90 + ["USD"] * 5 + ["EUR"] * 5  # mostly INR

#     # 1. Successful transactions (~55% of volume → ~3850 transactions × 3 events = ~5775)
#     for _ in range(3850):
#         txn_id = str(uuid.uuid4())
#         merchant = random.choice(MERCHANTS)
#         amount = round(random.uniform(100, 50000), 2)
#         currency = random.choice(currencies)
#         t0 = rand_ts()
#         t1 = rand_ts(t0)
#         t2 = rand_ts(t1)
#         events.append(make_event(str(uuid.uuid4()), "payment_initiated",  txn_id, merchant, amount, currency, t0))
#         events.append(make_event(str(uuid.uuid4()), "payment_processed",  txn_id, merchant, amount, currency, t1))
#         events.append(make_event(str(uuid.uuid4()), "settled",            txn_id, merchant, amount, currency, t2))

#     # 2. Failed transactions (~15% → ~1050 × 2 events = ~2100)
#     for _ in range(1050):
#         txn_id = str(uuid.uuid4())
#         merchant = random.choice(MERCHANTS)
#         amount = round(random.uniform(100, 50000), 2)
#         currency = random.choice(currencies)
#         t0 = rand_ts()
#         t1 = rand_ts(t0)
#         events.append(make_event(str(uuid.uuid4()), "payment_initiated", txn_id, merchant, amount, currency, t0))
#         events.append(make_event(str(uuid.uuid4()), "payment_failed",    txn_id, merchant, amount, currency, t1))

#     # 3. Pending settlement (~15% → ~1050 × 2 events = ~2100)
#     for _ in range(1050):
#         txn_id = str(uuid.uuid4())
#         merchant = random.choice(MERCHANTS)
#         amount = round(random.uniform(100, 50000), 2)
#         currency = random.choice(currencies)
#         t0 = rand_ts()
#         t1 = rand_ts(t0)
#         events.append(make_event(str(uuid.uuid4()), "payment_initiated", txn_id, merchant, amount, currency, t0))
#         events.append(make_event(str(uuid.uuid4()), "payment_processed", txn_id, merchant, amount, currency, t1))

#     # 4. Duplicate events: copy ~200 existing events and re-add (same event_id)
#     sample_for_dup = random.sample(events, 200)
#     events.extend(sample_for_dup)

#     # 5. Discrepancy: settled on a failed transaction (~50 transactions)
#     for _ in range(50):
#         txn_id = str(uuid.uuid4())
#         merchant = random.choice(MERCHANTS)
#         amount = round(random.uniform(100, 50000), 2)
#         currency = random.choice(currencies)
#         t0 = rand_ts()
#         t1 = rand_ts(t0)
#         t2 = rand_ts(t1)
#         events.append(make_event(str(uuid.uuid4()), "payment_initiated", txn_id, merchant, amount, currency, t0))
#         events.append(make_event(str(uuid.uuid4()), "payment_failed",    txn_id, merchant, amount, currency, t1))
#         events.append(make_event(str(uuid.uuid4()), "settled",           txn_id, merchant, amount, currency, t2))

#     # 6. Conflicting events: both processed and failed on same txn (~50)
#     for _ in range(50):
#         txn_id = str(uuid.uuid4())
#         merchant = random.choice(MERCHANTS)
#         amount = round(random.uniform(100, 50000), 2)
#         currency = random.choice(currencies)
#         t0 = rand_ts()
#         t1 = rand_ts(t0)
#         t2 = rand_ts(t0)  # same base, different offset — race condition
#         events.append(make_event(str(uuid.uuid4()), "payment_initiated", txn_id, merchant, amount, currency, t0))
#         events.append(make_event(str(uuid.uuid4()), "payment_processed", txn_id, merchant, amount, currency, t1))
#         events.append(make_event(str(uuid.uuid4()), "payment_failed",    txn_id, merchant, amount, currency, t2))

#     random.shuffle(events)
#     return events


# if __name__ == "__main__":
#     random.seed(42)
#     events = build_events()
#     output_path = "sample_events.json"
#     with open(output_path, "w") as f:
#         json.dump(events, f, indent=2)
#     print(f"Generated {len(events)} events → {output_path}")
