"""Google Ads fixture generator - emits raw GAQL response shape (cost_micros un-divided).
Filler economics come from noon.fixtures.economics (coherent claim = payout x over_claim, shared token)."""
from __future__ import annotations

from decimal import Decimal

from faker import Faker

from noon.fixtures.economics import offer_economics


def generate_google_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw Google Ads rows in real GAQL shape. Deterministic for a given seed.
    cost_micros is in MILLIONTHS (un-divided). Claim (conversions_value) is a realistic over-claim
    of the offer's real payout (from economics), sharing the per-(offer,platform) token so revenue
    joins. Sparse offers emit zero claim value."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        econ = offer_economics(offer_id, seed)
        pl = econ.placements["google"]
        campaign_id = f"C{fake.random_int(min=1000, max=9999)}"
        ad_id = f"A{fake.random_int(min=100, max=999)}"
        dollars = fake.random_int(min=100, max=50000) / 100.0
        cost_micros = int(round(dollars * 1_000_000))
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        conversions = econ.conversions_weight
        mid = (pl.payout_low + pl.payout_high) / 2
        claim = Decimal("0") if econ.is_sparse else (Decimal(conversions) * mid * econ.over_claim_factor)
        rows.append({
            "campaign.id": campaign_id,
            "campaign.name": f"{fake.word().capitalize()} Campaign",
            "segments.date": fake.date_between(start_date="-365d", end_date="today").isoformat(),
            "metrics.cost_micros": cost_micros,
            "metrics.impressions": impressions,
            "metrics.clicks": clicks,
            "metrics.conversions": conversions,
            "metrics.conversions_value": f"{claim:.2f}",
            "geographic_view.country": econ.geo,
            "ad_group_ad.ad.id": ad_id,
            "ad_group_ad.ad.name": f"Ad {ad_id}",
            "tracking_token": pl.token,
            "offer_id": offer_id,
        })
    return rows
