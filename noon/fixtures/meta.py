"""Meta/Facebook fixture generator - emits raw Insights shape (nested actions/action_values).
Filler economics come from noon.fixtures.economics (coherent claim, shared token)."""
from __future__ import annotations

from decimal import Decimal

from faker import Faker

from noon.fixtures.economics import offer_economics


def generate_meta_rows(n: int = 100, seed: int = 0) -> list[dict]:
    """Generate n raw Meta Insights rows. Deterministic per seed. Revenue nested in action_values;
    claim = realistic over-claim of the offer's real payout (economics). Sparse offers omit the
    revenue entry (empty action_values), preserving claim-side sparsity."""
    fake = Faker()
    fake.seed_instance(seed)
    rows = []
    for _ in range(n):
        offer_id = f"OFFER{fake.random_int(min=1, max=20)}"
        econ = offer_economics(offer_id, seed)
        pl = econ.placements["meta"]
        campaign_id = f"C{fake.random_int(min=1000, max=9999)}"
        adset_id = f"AS{fake.random_int(min=100, max=999)}"
        ad_id = f"AD{fake.random_int(min=100, max=999)}"
        spend = fake.random_int(min=100, max=50000) / 100.0
        clicks = fake.random_int(min=0, max=500)
        impressions = clicks * fake.random_int(min=10, max=100)
        leads = econ.conversions_weight
        actions = [
            {"action_type": "link_click", "value": str(clicks)},
            {"action_type": "lead", "value": str(leads)},
        ]
        mid = (pl.payout_low + pl.payout_high) / 2
        claim = Decimal(leads) * mid * econ.over_claim_factor
        # Sparse offers pass NO revenue value (empty action_values) - claim-side sparsity.
        if not econ.is_sparse and leads > 0:
            action_values = [{"action_type": "lead", "value": f"{claim:.2f}"}]
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
            "date_stop": None,
            "spend": f"{spend:.2f}",
            "impressions": str(impressions),
            "clicks": str(clicks),
            "actions": actions,
            "action_values": action_values,
            "account_currency": "USD",
            "geo": econ.geo,
            "tracking_token": pl.token,
            "offer_id": offer_id,
        })
        rows[-1]["date_stop"] = rows[-1]["date_start"]
    return rows
