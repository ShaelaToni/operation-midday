"""Google Ads fixture generator - emits raw GAQL response shape (cost_micros un-divided)."""
from __future__ import annotations

from faker import Faker

_GEOS = ("US", "CA", "GB", "AU")


def generate_google_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw Google Ads rows in real GAQL shape. Deterministic for a given seed.
    cost_micros is in MILLIONTHS (un-divided) - the adapter does the division.
    Uses an ISOLATED per-instance RNG (seed_instance), so generators never share global
    Faker state - each is reproducible independent of call order or other generators.
    """
    fake = Faker()
    fake.seed_instance(seed)  # instance-level RNG, NOT the class-level Faker.seed()
    rows = []
    for _ in range(n):
        campaign_id = f"C{fake.random_int(min=1000, max=9999)}"
        ad_id = f"A{fake.random_int(min=100, max=999)}"
        geo = _GEOS[fake.random_int(min=0, max=len(_GEOS) - 1)]
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        dollars = fake.random_int(min=100, max=50000) / 100.0  # $1.00 - $500.00
        cost_micros = int(round(dollars * 1_000_000))          # back to micros (raw shape)
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        conversions = round(clicks * (fake.random_int(min=0, max=15) / 100.0), 2)
        conv_value = round(conversions * fake.random_int(min=10, max=200), 2)
        rows.append({
            "campaign.id": campaign_id,
            "campaign.name": f"{fake.word().capitalize()} Campaign",
            "segments.date": fake.date_between(start_date="-365d", end_date="today").isoformat(),
            "metrics.cost_micros": cost_micros,
            "metrics.impressions": impressions,
            "metrics.clicks": clicks,
            "metrics.conversions": conversions,
            "metrics.conversions_value": conv_value,
            "geographic_view.country": geo,
            "ad_group_ad.ad.id": ad_id,
            "ad_group_ad.ad.name": f"Ad {ad_id}",
            "tracking_token": f"tok_{campaign_id}_{ad_id}",
            "offer_id": offer_id,
        })
    return rows
