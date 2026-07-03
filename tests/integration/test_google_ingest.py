"""Google ingestion: generator emits real GAQL raw shape; adapter divides micros and maps to SpendRow kwargs.
Written test-first (red) before the generator/adapter exist.
"""
from decimal import Decimal

import pytest


def test_generator_emits_raw_gaql_shape():
    from noon.fixtures.google import generate_google_rows

    rows = generate_google_rows(n=5, seed=42)
    assert len(rows) == 5
    r = rows[0]
    # Real GAQL field names, un-divided micros (honest raw shape - Data-Map fidelity).
    for key in ("campaign.id", "campaign.name", "segments.date", "metrics.cost_micros",
                "metrics.impressions", "metrics.clicks", "metrics.conversions",
                "metrics.conversions_value", "geographic_view.country"):
        assert key in r, f"raw Google row missing real GAQL field: {key}"
    # cost_micros is an integer in millionths (NOT pre-divided).
    assert isinstance(r["metrics.cost_micros"], int)
    assert r["metrics.cost_micros"] > 1000  # micros are large integers


def test_generator_is_deterministic_with_seed():
    from noon.fixtures.google import generate_google_rows

    a = generate_google_rows(n=3, seed=7)
    b = generate_google_rows(n=3, seed=7)
    assert a == b, "same seed must produce identical rows (reproducible fixtures)"


def test_adapter_divides_micros_to_dollars():
    from noon.adapters.google import GoogleAdapter

    raw = {
        "campaign.id": "C123",
        "campaign.name": "Test Campaign",
        "segments.date": "2026-01-15",
        "metrics.cost_micros": 12500000,  # $12.50 in millionths
        "metrics.impressions": 1000,
        "metrics.clicks": 50,
        "metrics.conversions": 3.5,
        "metrics.conversions_value": 90.0,
        "geographic_view.country": "US",
        "ad_group_ad.ad.id": "A1",
        "ad_group_ad.ad.name": "Ad One",
        "tracking_token": "tok_abc",
        "offer_id": "OFFER1",
    }
    kwargs = GoogleAdapter().parse_row(raw)
    # THE decisive assertion: micros divided to dollars, as Decimal, exact.
    assert kwargs["spend"] == Decimal("12.50")
    assert isinstance(kwargs["spend"], Decimal)
    # Field mapping to SpendRow kwargs.
    assert kwargs["source"] == "google"
    assert kwargs["campaign_id"] == "C123"
    assert kwargs["campaign_name"] == "Test Campaign"
    assert kwargs["date"] == "2026-01-15"
    assert kwargs["geo"] == "US"
    assert kwargs["impressions"] == 1000
    assert kwargs["clicks"] == 50
    assert kwargs["platform_reported_conversions"] == Decimal("3.5")
    assert kwargs["platform_reported_revenue"] == Decimal("90.0")
    assert kwargs["tracking_token"] == "tok_abc"
    assert kwargs["offer_id"] == "OFFER1"
    # Lineage: the raw row is preserved for the caller to store in SpendRow.raw.
    assert kwargs["raw"] == raw
    # Deterministic natural key for idempotency.
    assert kwargs["ingest_key"] == "google:C123:A1:2026-01-15:US:tok_abc"


def test_adapter_registered_in_registry():
    import noon.adapters  # noqa: F401  (triggers registration)
    from noon.adapters.base import get_adapter

    adapter = get_adapter("google")
    assert adapter.source == "google"
