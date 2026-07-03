"""Affiliate/postback fixture generator - emits raw server-to-server postback shape (REVENUE side)."""
from __future__ import annotations

from faker import Faker

_GEOS = ("US", "CA", "GB", "AU")
# Realistic status mix: mostly approved/pending, some rejected/reversed (the reversal reality).
_STATUS_WEIGHTS = (
    ("approved", 55),
    ("pending", 25),
    ("rejected", 12),
    ("reversed", 8),
)


def _weighted_status(fake: Faker) -> str:
    roll = fake.random_int(min=1, max=100)
    cumulative = 0
    for status, weight in _STATUS_WEIGHTS:
        cumulative += weight
        if roll <= cumulative:
            return status
    return "approved"


def generate_affiliate_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw affiliate postback rows (REVENUE side). Deterministic per seed.
    transaction_id = unique conversion id. sub_id = the tracking token (join key). payout = real
    money (always present). status = provisional state (reversal mechanism). geo stays 2-char."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for i in range(n):
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        geo = _GEOS[fake.random_int(min=0, max=len(_GEOS) - 1)]
        payout = round(fake.random_int(min=500, max=15000) / 100.0, 2)  # $5.00 - $150.00
        d = fake.date_between(start_date="-365d", end_date="today")
        hour = fake.random_int(min=0, max=23)
        minute = fake.random_int(min=0, max=59)
        rows.append({
            "transaction_id": f"TXN{seed}_{i}_{fake.random_int(min=10000, max=99999)}",
            "sub_id": f"tok_C{fake.random_int(min=1000, max=9999)}_A{fake.random_int(min=100, max=999)}",
            "offer_id": offer_id,
            "payout": f"{payout:.2f}",
            "status": _weighted_status(fake),
            "timestamp": f"{d.isoformat()}T{hour:02d}:{minute:02d}:00Z",
            "geo": geo,
        })
    return rows
