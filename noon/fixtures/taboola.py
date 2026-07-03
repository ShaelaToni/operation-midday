"""Taboola/Backstage fixture generator - emits raw native-ads shape (spent, cpa_actions_num, timezone, item)."""
from __future__ import annotations

from faker import Faker

_GEOS = ("US", "CA", "GB", "AU")


def generate_taboola_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw Taboola Backstage rows. Deterministic per seed (isolated per-instance RNG).
    Taboola's own field names: 'spent' (dollar string, NOT micros), 'cpa_actions_num', 'conversions_value'.
    Response carries its own 'timezone' (EST/EDT). Ad-level fields are item/item_name/url."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        campaign_id = f"TC{fake.random_int(min=1000, max=9999)}"
        item = f"IT{fake.random_int(min=100, max=999)}"
        geo = _GEOS[fake.random_int(min=0, max=len(_GEOS) - 1)]
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        spent = fake.random_int(min=100, max=50000) / 100.0  # $1.00 - $500.00 dollars
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        visible = int(impressions * 0.75)
        cpa_actions = fake.random_int(min=0, max=int(clicks * 0.2) + 1)
        conv_value = round(cpa_actions * fake.random_int(min=10, max=60), 2)
        rows.append({
            "campaign_id": campaign_id,
            "campaign_name": f"{fake.word().capitalize()} Native",
            "date": fake.date_between(start_date="-365d", end_date="today").isoformat(),
            "spent": f"{spent:.2f}",
            "impressions": str(impressions),
            "visible_impressions": str(visible),
            "clicks": str(clicks),
            "cpa_actions_num": str(cpa_actions),
            "conversions_value": f"{conv_value:.2f}",
            "currency": "USD",
            "timezone": "EST",
            "item": item,
            "item_name": f"Native Ad {item}",
            "url": f"https://example.com/lp/{offer_id.lower()}",
            "country": geo,
            "tracking_token": f"tok_{campaign_id}_{item}",
            "offer_id": offer_id,
        })
    return rows
