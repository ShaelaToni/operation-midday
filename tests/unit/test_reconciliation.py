"""Reconciliation core (crown jewel) - PURE domain, no Django, no DB. The reconciler joins spend to
revenue on the tracking token, aggregates to the grain, and produces ProfitResult facts whose
reconciled_revenue is the REAL affiliate payout (trust the revenue side, not the platform claim).
Written test-first (red). Smallest-first: single-to-single, then multiple-per-grain aggregation.
"""
from datetime import date
from decimal import Decimal

import pytest

from domain.records import SpendRecord, ConversionRecord, ProfitResult


def _spend(token="tok_a", offer="OFFER1", geo="US", spend="100.00", platform="google",
           campaign="C1", ad="AD1", d=date(2026, 1, 15), claim="120.00"):
    return SpendRecord(
        date=d, platform=platform, campaign_id=campaign, campaign_name=f"{campaign} name",
        ad_id=ad, ad_name=f"{ad} name", offer_id=offer, geo=geo, tracking_token=token,
        spend=Decimal(spend), impressions=1000, clicks=50,
        platform_reported_conversions=Decimal("5"),
        platform_reported_revenue=(Decimal(claim) if claim is not None else None),
    )


def _conv(token="tok_a", offer="OFFER1", geo="US", revenue="300.00", status="approved",
          conv_id="TXN1", d=date(2026, 1, 15)):
    return ConversionRecord(
        conversion_id=conv_id, date=d, offer_id=offer, geo=geo, tracking_token=token,
        revenue=Decimal(revenue), status=status,
    )


def test_happy_path_single_spend_single_conversion():
    from domain.reconciliation import reconcile
    results = reconcile([_spend(spend="100.00", claim="120.00")],
                        [_conv(revenue="300.00")])
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, ProfitResult)
    # reconciled_revenue is the AFFILIATE payout (the truth), NOT the platform claim.
    assert r.reconciled_revenue == Decimal("300.00")
    assert r.platform_reported_revenue == Decimal("120.00")   # claim carried through for the gap
    assert r.spend == Decimal("100.00")                        # spend carried through
    assert r.offer_id == "OFFER1"
    assert r.geo == "US"
    assert r.platform == "google"
    # true profit is reconciled_revenue - spend = 200.00 (computed by caller, but components exact).
    assert r.reconciled_revenue - r.spend == Decimal("200.00")
    # lineage: the contributing conversion id is recorded.
    assert "TXN1" in r.source_keys


def test_multiple_conversions_same_grain_aggregate_then_join():
    from domain.reconciliation import reconcile
    # One spend grain, THREE approved conversions on the same token -> summed, counted once each.
    spend = [_spend(spend="100.00")]
    convs = [
        _conv(revenue="300.00", conv_id="TXN1"),
        _conv(revenue="150.00", conv_id="TXN2"),
        _conv(revenue="50.00", conv_id="TXN3"),
    ]
    results = reconcile(spend, convs)
    assert len(results) == 1
    r = results[0]
    # Aggregate-then-join: 300 + 150 + 50 = 500, no double-count.
    assert r.reconciled_revenue == Decimal("500.00")
    assert r.reconciled_conversions == Decimal("3")
    # All three conversion ids in the lineage.
    for cid in ("TXN1", "TXN2", "TXN3"):
        assert cid in r.source_keys


def test_reconciled_revenue_is_decimal_not_float():
    from domain.reconciliation import reconcile
    results = reconcile([_spend()], [_conv(revenue="300.00")])
    assert isinstance(results[0].reconciled_revenue, Decimal)
    assert isinstance(results[0].spend, Decimal)
