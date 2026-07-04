"""Taboola/Backstage fixture generator - raw native-ads shape (spent, cpa_actions_num, item).
Filler economics come from noon.fixtures.economics (coherent claim, shared token)."""
from __future__ import annotations

from decimal import Decimal

from faker import Faker

from noon.fixtures.economics import offer_economics


def generate_taboola_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw Taboola Backstage rows. Deterministic per seed. conversions_value = realistic
    over-claim of the offer's real payout (economics); sparse offers emit 0 claim. Shared token."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        econ = offer_economics(offer_id, seed)
        pl = econ.placements["taboola"]
        campaign_id = f"TC{fake.random_int(min=1000, max=9999)}"
        item = f"IT{fake.random_int(min=100, max=999)}"
        spent = fake.random_int(min=100, max=50000) / 100.0
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        visible = int(impressions * 0.75)
        cpa_actions = econ.conversions_weight
        mid = (pl.payout_low + pl.payout_high) / 2
        claim = Decimal("0") if econ.is_sparse else (Decimal(cpa_actions) * mid * econ.over_claim_factor)
        rows.append({
            "campaign_id": campaign_id,
            "campaign_name": f"{fake.word().capitalize()} Native",
            "date": fake.date_between(start_date="-365d", end_date="today").isoformat(),
            "spent": f"{spent:.2f}",
            "impressions": str(impressions),
            "visible_impressions": str(visible),
            "clicks": str(clicks),
            "cpa_actions_num": str(cpa_actions),
            "conversions_value": f"{claim:.2f}",
            "currency": "USD",
            "timezone": "EST",
            "item": item,
            "item_name": f"Native Ad {item}",
            "url": f"https://example.com/lp/{offer_id.lower()}",
            "country": econ.geo,
            "tracking_token": pl.token,
            "offer_id": offer_id,
        })
    return rows
