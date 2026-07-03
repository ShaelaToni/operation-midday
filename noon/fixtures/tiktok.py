"""TikTok fixture generator - emits /report/integrated/get/ shape: nested {dimensions, metrics}."""
from __future__ import annotations

from faker import Faker

_GEOS = ("US", "CA", "GB", "AU")


def generate_tiktok_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw TikTok rows. Deterministic per seed (isolated per-instance RNG).
    Each row is a nested {dimensions, metrics} split (fields read by NAME, order unstable).
    spend is a dollar string (NOT micros). ~40% of rows omit conversion_value (sparsity)."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        campaign_id = f"TT_C{fake.random_int(min=1000, max=9999)}"
        adgroup_id = f"AG{fake.random_int(min=100, max=999)}"
        ad_id = f"TT_AD{fake.random_int(min=100, max=999)}"
        geo = _GEOS[fake.random_int(min=0, max=len(_GEOS) - 1)]
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        spend = fake.random_int(min=100, max=50000) / 100.0
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        conversion = fake.random_int(min=0, max=int(clicks * 0.2) + 1)
        metrics = {
            "spend": f"{spend:.2f}",
            "impressions": str(impressions),
            "clicks": str(clicks),
            "conversion": str(conversion),
            "campaign_name": f"{fake.word().capitalize()} TikTok",
            "adgroup_name": f"{fake.word().capitalize()} Adgroup",
            "ad_name": f"Ad {ad_id}",
        }
        # Claim-side sparsity: ~40% of rows omit conversion_value entirely.
        if fake.random_int(min=0, max=9) >= 4 and conversion > 0:
            metrics["conversion_value"] = f"{round(conversion * fake.random_int(min=10, max=60), 2):.2f}"
        rows.append({
            "dimensions": {
                "stat_time_day": fake.date_between(start_date="-365d", end_date="today").isoformat(),
                "campaign_id": campaign_id,
                "adgroup_id": adgroup_id,
                "ad_id": ad_id,
                "country_code": geo,
            },
            "metrics": metrics,
            "tracking_token": f"tok_{campaign_id}_{ad_id}",
            "offer_id": offer_id,
        })
    return rows
