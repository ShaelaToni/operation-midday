"""TikTok fixture generator - /report/integrated/get/ shape: nested {dimensions, metrics}.
Filler economics come from noon.fixtures.economics (coherent claim, shared token)."""
from __future__ import annotations

from decimal import Decimal

from faker import Faker

from noon.fixtures.economics import offer_economics


def generate_tiktok_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw TikTok rows. Deterministic per seed. conversion_value = realistic over-claim
    of the offer's real payout (economics); sparse offers omit conversion_value. Shared token."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        econ = offer_economics(offer_id, seed)
        pl = econ.placements["tiktok"]
        campaign_id = f"TT_C{fake.random_int(min=1000, max=9999)}"
        adgroup_id = f"AG{fake.random_int(min=100, max=999)}"
        ad_id = f"TT_AD{fake.random_int(min=100, max=999)}"
        spend = fake.random_int(min=100, max=50000) / 100.0
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        conversion = econ.conversions_weight
        metrics = {
            "spend": f"{spend:.2f}",
            "impressions": str(impressions),
            "clicks": str(clicks),
            "conversion": str(conversion),
            "campaign_name": f"{fake.word().capitalize()} TikTok",
            "adgroup_name": f"{fake.word().capitalize()} Adgroup",
            "ad_name": f"Ad {ad_id}",
        }
        # Sparse offers omit conversion_value entirely (claim-side sparsity).
        if not econ.is_sparse and conversion > 0:
            mid = (pl.payout_low + pl.payout_high) / 2
            claim = Decimal(conversion) * mid * econ.over_claim_factor
            metrics["conversion_value"] = f"{claim:.2f}"
        rows.append({
            "dimensions": {
                "stat_time_day": fake.date_between(start_date="-365d", end_date="today").isoformat(),
                "campaign_id": campaign_id,
                "adgroup_id": adgroup_id,
                "ad_id": ad_id,
                "country_code": econ.geo,
            },
            "metrics": metrics,
            "tracking_token": pl.token,
            "offer_id": offer_id,
        })
    return rows
