"""Meta ingestion: generator emits real Insights shape (nested actions/action_values); adapter
flattens the configured conversion action_type (default 'lead') and maps to SpendRow kwargs.
Revenue is often absent in lead-gen (claim-side sparsity) -> platform_reported_revenue = None.
Written test-first (red) before the generator/adapter exist.
"""
from decimal import Decimal

import pytest


def test_generator_emits_real_meta_shape():
    from noon.fixtures.meta import generate_meta_rows

    rows = generate_meta_rows(n=5, seed=42)
    assert len(rows) == 5
    r = rows[0]
    for key in ("campaign_id", "campaign_name", "adset_name", "ad_name",
                "date_start", "spend", "impressions", "clicks",
                "actions", "account_currency"):
        assert key in r, f"raw Meta row missing real field: {key}"
    # spend is a normal decimal string/number, NOT micros.
    assert float(r["spend"]) < 100000  # dollars, not millionths
    # actions is a nested list of {action_type, value} dicts.
    assert isinstance(r["actions"], list)
    assert all("action_type" in a and "value" in a for a in r["actions"])


def test_generator_is_deterministic_with_seed():
    from noon.fixtures.meta import generate_meta_rows
    assert generate_meta_rows(n=3, seed=7) == generate_meta_rows(n=3, seed=7)


def test_adapter_flattens_lead_action():
    from noon.adapters.meta import MetaAdapter

    raw = {
        "campaign_id": "C1",
        "campaign_name": "Lead Campaign",
        "adset_id": "AS1",
        "adset_name": "Adset One",
        "ad_id": "AD1",
        "ad_name": "Ad One",
        "date_start": "2026-01-15",
        "date_stop": "2026-01-15",
        "spend": "340.00",
        "impressions": "10000",
        "clicks": "500",
        "actions": [
            {"action_type": "link_click", "value": "480"},
            {"action_type": "lead", "value": "40"},
        ],
        "action_values": [
            {"action_type": "lead", "value": "900.00"},
        ],
        "account_currency": "USD",
        "geo": "US",
        "tracking_token": "tok_meta_1",
        "offer_id": "OFFER1",
    }
    kwargs = MetaAdapter().parse_row(raw)
    # spend is NOT divided (already dollars) - the anti-Google case.
    assert kwargs["spend"] == Decimal("340.00")
    assert isinstance(kwargs["spend"], Decimal)
    # 'lead' flattened from the nested actions/action_values lists.
    assert kwargs["platform_reported_conversions"] == Decimal("40")
    assert kwargs["platform_reported_revenue"] == Decimal("900.00")
    assert kwargs["source"] == "meta"
    assert kwargs["campaign_id"] == "C1"
    assert kwargs["ad_id"] == "AD1"
    assert kwargs["date"] == "2026-01-15"
    assert kwargs["geo"] == "US"
    assert kwargs["tracking_token"] == "tok_meta_1"
    # adset lives in raw (no dedicated column) and in the ingest_key for uniqueness.
    assert kwargs["raw"] == raw
    assert kwargs["ingest_key"] == "meta:C1:AS1:AD1:2026-01-15:US:tok_meta_1"


def test_adapter_claim_side_sparsity_revenue_none():
    """Lead-gen often passes NO revenue value to Meta -> action_values lacks the lead entry."""
    from noon.adapters.meta import MetaAdapter

    raw = {
        "campaign_id": "C2", "campaign_name": "No-Rev Campaign",
        "adset_id": "AS2", "adset_name": "Adset Two", "ad_id": "AD2", "ad_name": "Ad Two",
        "date_start": "2026-01-16", "date_stop": "2026-01-16",
        "spend": "120.00", "impressions": "5000", "clicks": "200",
        "actions": [{"action_type": "lead", "value": "12"}],
        "action_values": [],  # NO revenue value - the sparsity case
        "account_currency": "USD", "geo": "CA",
        "tracking_token": "tok_meta_2", "offer_id": "OFFER2",
    }
    kwargs = MetaAdapter().parse_row(raw)
    assert kwargs["platform_reported_conversions"] == Decimal("12")
    assert kwargs["platform_reported_revenue"] is None  # sparsity -> None, not zero, not crash


def test_adapter_registered_in_registry():
    import noon.adapters  # noqa: F401
    from noon.adapters.base import get_adapter
    assert get_adapter("meta").source == "meta"
