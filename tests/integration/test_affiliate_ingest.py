"""Affiliate ingestion (REVENUE side): generator emits real postback shape; adapter maps to
ConversionRow kwargs (NOT SpendRow). conversion_id = idempotency key; sub_id/click_id ->
tracking_token (the join key that ties revenue back to spend); payout -> revenue (real money,
trust over platform claims); status pending|approved|rejected|reversed makes revenue provisional.
Written test-first (red) before the generator/adapter exist.
"""
from decimal import Decimal

import pytest


def test_generator_emits_real_postback_shape():
    from noon.fixtures.affiliate import generate_affiliate_rows

    rows = generate_affiliate_rows(n=10, seed=42)
    # n is offer-iterations; each emits (4 platforms x that offer's conversions_weight >= 1)
    # postbacks, so the count is at least 4*n. This also validates the per-platform emission.
    assert len(rows) >= 4 * 10, f"expected >= 4*n postbacks (4 platforms x weight), got {len(rows)}"
    r = rows[0]
    for key in ("transaction_id", "sub_id", "offer_id", "payout",
                "status", "timestamp", "geo"):
        assert key in r, f"raw affiliate postback missing field: {key}"
    # status is one of the four provisional states.
    assert all(row["status"] in ("pending", "approved", "rejected", "reversed") for row in rows)


def test_generator_is_deterministic_with_seed():
    from noon.fixtures.affiliate import generate_affiliate_rows
    assert generate_affiliate_rows(n=3, seed=7) == generate_affiliate_rows(n=3, seed=7)


def test_adapter_maps_to_conversion_row():
    from noon.adapters.affiliate import AffiliateAdapter

    raw = {
        "transaction_id": "TXN123",
        "sub_id": "tok_meta_1",       # THE join key -> tracking_token
        "offer_id": "OFFER1",
        "payout": "45.00",
        "status": "approved",
        "timestamp": "2026-01-15T14:30:00Z",
        "geo": "US",
    }
    kwargs = AffiliateAdapter().parse_row(raw)
    # Maps to ConversionRow fields (NOT SpendRow).
    assert kwargs["source"] == "affiliate"
    assert kwargs["conversion_id"] == "TXN123"   # transaction_id -> conversion_id (idempotency)
    assert kwargs["tracking_token"] == "tok_meta_1"  # sub_id -> tracking_token (THE join key)
    assert kwargs["offer_id"] == "OFFER1"
    assert kwargs["revenue"] == Decimal("45.00")  # payout -> revenue (real money)
    assert isinstance(kwargs["revenue"], Decimal)
    assert kwargs["status"] == "approved"
    assert kwargs["date"] == "2026-01-15"         # date extracted from timestamp
    assert kwargs["geo"] == "US"
    assert kwargs["raw"] == raw
    # ConversionRow has NO spend/campaign fields - assert they're absent.
    assert "spend" not in kwargs
    assert "campaign_id" not in kwargs


def test_adapter_revenue_present_across_statuses():
    """Revenue (payout) is populated regardless of status; status governs whether it counts.
    A reversed conversion still carries the payout it would have paid."""
    from noon.adapters.affiliate import AffiliateAdapter

    raw = {
        "transaction_id": "TXN_REV", "sub_id": "tok_x", "offer_id": "OFFER2",
        "payout": "60.00", "status": "reversed",
        "timestamp": "2026-01-16T09:00:00Z", "geo": "CA",
    }
    kwargs = AffiliateAdapter().parse_row(raw)
    assert kwargs["revenue"] == Decimal("60.00")  # payout present even when reversed
    assert kwargs["status"] == "reversed"          # status is what flags it for reconciliation


def test_adapter_registered_in_registry():
    import noon.adapters  # noqa: F401
    from noon.adapters.base import get_adapter
    assert get_adapter("affiliate").source == "affiliate"
