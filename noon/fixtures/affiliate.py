"""Affiliate/postback fixture generator - raw server-to-server postback shape (REVENUE side).
Filler payout/token come from noon.fixtures.economics so revenue JOINS the spend side."""
from __future__ import annotations

from faker import Faker

from noon.fixtures.economics import offer_economics, placement_for

_SPEND_PLATFORMS = ("google", "meta", "taboola", "tiktok")
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
    """Generate n raw affiliate postback rows (REVENUE side). Deterministic per seed. payout is the
    REAL money, drawn from the offer+platform placement band; sub_id is that placement's token so
    revenue joins the spend row. geo comes from the offer's economics."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for i in range(n):
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        econ = offer_economics(offer_id, seed)
        for platform in _SPEND_PLATFORMS:
            pl = placement_for(offer_id, platform, seed)
            low = float(pl.payout_low)
            high = float(pl.payout_high)
            # One postback per conversion (conversions_weight), per platform - matches each
            # platform's claimed conversions with that platform's real payouts.
            for c in range(econ.conversions_weight):
                payout = round(fake.random_int(min=int(low * 100), max=int(high * 100)) / 100.0, 2)
                d = fake.date_between(start_date="-365d", end_date="today")
                hour = fake.random_int(min=0, max=23)
                minute = fake.random_int(min=0, max=59)
                rows.append({
                    "transaction_id": f"TXN{seed}_{i}_{platform}_{c}_{fake.random_int(min=10000, max=99999)}",
                    "sub_id": pl.token,
                    "offer_id": offer_id,
                    "payout": f"{payout:.2f}",
                    "status": _weighted_status(fake),
                    "timestamp": f"{d.isoformat()}T{hour:02d}:{minute:02d}:00Z",
                    "geo": econ.geo,
                })
    return rows
