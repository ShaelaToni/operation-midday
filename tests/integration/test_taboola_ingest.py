"""Taboola ingestion: generator emits real Backstage shape (spent/cpa_actions_num/timezone/item);
adapter maps the renamed fields to SpendRow kwargs. Timezone is EST/EDT (== our US/Eastern), so the
date maps through; the tz field is preserved in raw for lineage. url (landing page) -> raw (no column).
Written test-first (red) before the generator/adapter exist.
"""
from decimal import Decimal

import pytest


def test_generator_emits_real_taboola_shape():
    from noon.fixtures.taboola import generate_taboola_rows

    rows = generate_taboola_rows(n=5, seed=42)
    assert len(rows) == 5
    r = rows[0]
    for key in ("campaign_id", "campaign_name", "date", "spent", "impressions",
                "clicks", "cpa_actions_num", "conversions_value", "currency",
                "timezone", "item", "item_name", "url", "country"):
        assert key in r, f"raw Taboola row missing real field: {key}"
    # Taboola's own field names (the rename gotcha).
    assert "spend" not in r, "Taboola uses 'spent', not 'spend'"
    assert "conversions" not in r, "Taboola uses 'cpa_actions_num'"


def test_generator_is_deterministic_with_seed():
    from noon.fixtures.taboola import generate_taboola_rows
    assert generate_taboola_rows(n=3, seed=7) == generate_taboola_rows(n=3, seed=7)


def test_adapter_maps_renamed_fields():
    from noon.adapters.taboola import TaboolaAdapter

    raw = {
        "campaign_id": "TC1",
        "campaign_name": "Native Campaign",
        "date": "2026-01-15",
        "spent": "215.75",
        "impressions": "80000",
        "visible_impressions": "60000",
        "clicks": "300",
        "cpa_actions_num": "18",
        "conversions_value": "540.00",
        "currency": "USD",
        "timezone": "EST",
        "item": "IT1",
        "item_name": "Native Ad One",
        "url": "https://example.com/lp/offer1",
        "country": "US",
        "tracking_token": "tok_tab_1",
        "offer_id": "OFFER1",
    }
    kwargs = TaboolaAdapter().parse_row(raw)
    # 'spent' -> spend (already dollars, NOT divided).
    assert kwargs["spend"] == Decimal("215.75")
    assert isinstance(kwargs["spend"], Decimal)
    # 'cpa_actions_num' -> conversions; 'conversions_value' -> revenue.
    assert kwargs["platform_reported_conversions"] == Decimal("18")
    assert kwargs["platform_reported_revenue"] == Decimal("540.00")
    assert kwargs["source"] == "taboola"
    assert kwargs["campaign_id"] == "TC1"
    # item -> ad_id, item_name -> ad_name.
    assert kwargs["ad_id"] == "IT1"
    assert kwargs["ad_name"] == "Native Ad One"
    assert kwargs["date"] == "2026-01-15"
    assert kwargs["geo"] == "US"
    assert kwargs["tracking_token"] == "tok_tab_1"
    # url (landing page) and timezone live in raw (no dedicated columns).
    assert kwargs["raw"]["url"] == "https://example.com/lp/offer1"
    assert kwargs["raw"]["timezone"] == "EST"
    assert kwargs["ingest_key"] == "taboola:TC1:IT1:2026-01-15:US:tok_tab_1"


def test_adapter_registered_in_registry():
    import noon.adapters  # noqa: F401
    from noon.adapters.base import get_adapter
    assert get_adapter("taboola").source == "taboola"
