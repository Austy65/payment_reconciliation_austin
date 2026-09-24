"""
Seed the service by POSTing all events from sample_events.json.
Uses batched concurrent requests for speed.

Usage:
    python scripts/seed.py [--url http://localhost:8000] [--file sample_events.json]
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

BATCH_SIZE = 50
WORKERS = 10


def post_event(client: httpx.Client, url: str, event: dict) -> dict:
    resp = client.post(url, json=event, timeout=15)
    resp.raise_for_status()
    return resp.json()


def seed(base_url: str, events_file: str):
    endpoint = f"{base_url}/events"
    with open(events_file) as f:
        events = json.load(f)

    print(f"Seeding {len(events)} events to {endpoint} …")
    created = duplicate = error = 0
    start = time.time()

    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(post_event, client, endpoint, ev): ev for ev in events}
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result()
                    if result["status"] == "created":
                        created += 1
                    else:
                        duplicate += 1
                except Exception as e:
                    error += 1
                    if error <= 5:
                        print(f"  error: {e}")
                if i % 500 == 0:
                    elapsed = time.time() - start
                    print(f"  {i}/{len(events)} ({elapsed:.1f}s) — created={created} dup={duplicate} err={error}")

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s — created={created}, duplicate={duplicate}, error={error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--file", default="sample_events.json")
    args = parser.parse_args()
    seed(args.url, args.file)
