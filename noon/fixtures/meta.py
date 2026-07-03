"""Meta/Facebook fixture generator - emits raw Insights shape (nested actions/action_values)."""
from __future__ import annotations

from faker import Faker

_GEOS = ("US", "CA", "GB", "AU")


def generate_meta_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw Meta Insights rows. Deterministic per seed (isolated per-instance RNG).
    spend is a dollar STRING (NOT micros). Conversions/revenue are nested in actions/action_values
    as lists of {action_type, value}. Some rows omit the revenue entry (claim-side sparsity)."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        campaign_id = f"C{fake.random_int(min=1000, max=9999)}"
        adset_id = f"AS{fake.random_int(min=100, max=999)}"
        ad_id = f"AD{fake.random_int(min=100, max=999)}"
        geo = _GEOS[fake.random_int(min=0, max=len(_GEOS) - 1)]
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        spend = fake.random_int(min=100, max=50000) / 100.0  # $1.00 - $500.00 dollars
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        leads = fake.random_int(min=0, max=int(clicks * 0.2) + 1)
        actions = [
            {"action_type": "link_click", "value": str(clicks)},
            {"action_type": "lead", "value": str(leads)},
        ]
        # Claim-side sparsity: ~40% of rows pass NO revenue value to the platform.
        has_revenue = fake.random_int(min=0, max=9) >= 4
        if has_revenue and leads > 0:
            revenue = round(leads * fake.random_int(min=10, max=60), 2)
            action_values = [{"action_type": "lead", "value": f"{revenue:.2f}"}]
        else:
            action_values = []
        rows.append({
            "campaign_id": campaign_id,
            "campaign_name": f"{fake.word().capitalize()} Campaign",
            "adset_id": adset_id,
            "adset_name": f"{fake.word().capitalize()} Adset",
            "ad_id": ad_id,
            "ad_name": f"Ad {ad_id}",
            "date_start": fake.date_between(start_date="-365d", end_date="today").isoformat(),
            "date_stop": None,  # set equal to date_start below
            "spend": f"{spend:.2f}",
            "impressions": str(impressions),
            "clicks": str(clicks),
            "actions": actions,
            "action_values": action_values,
            "account_currency": "USD",
            "geo": geo,
            "tracking_token": f"tok_{campaign_id}_{ad_id}",
            "offer_id": offer_id,
        })
        rows[-1]["date_stop"] = rows[-1]["date_start"]
    return rows
