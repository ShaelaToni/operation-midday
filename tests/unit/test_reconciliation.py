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


def test_reversed_conversion_subtracts_revenue_and_count():
    from domain.reconciliation import reconcile
    # OVERNIGHT_REVERSAL shape: approved 1500 + reversed 1200 -> net revenue 300, net count 0.
    spend = [_spend(spend="800.00")]
    convs = [
        _conv(revenue="1500.00", status="approved", conv_id="TXN_A"),
        _conv(revenue="1200.00", status="reversed", conv_id="TXN_R"),
    ]
    r = reconcile(spend, convs)[0]
    assert r.reconciled_revenue == Decimal("300.00")     # 1500 - 1200
    assert r.reconciled_conversions == Decimal("0")      # 1 approved - 1 reversed
    assert r.revenue_status == "reversed"                # reversed dominates the status
    # lineage keeps BOTH contributing ids.
    assert "TXN_A" in r.source_keys and "TXN_R" in r.source_keys


def test_rejected_and_pending_excluded_from_number():
    from domain.reconciliation import reconcile
    spend = [_spend(spend="100.00")]
    convs = [
        _conv(revenue="200.00", status="approved", conv_id="TXN_OK"),
        _conv(revenue="500.00", status="rejected", conv_id="TXN_REJ"),   # excluded
        _conv(revenue="300.00", status="pending", conv_id="TXN_PEND"),   # excluded
    ]
    r = reconcile(spend, convs)[0]
    assert r.reconciled_revenue == Decimal("200.00")     # only the approved
    assert r.reconciled_conversions == Decimal("1")
    # pending present (no reversed) -> status provisional.
    assert r.revenue_status == "provisional"


def test_confirmed_status_when_all_approved():
    from domain.reconciliation import reconcile
    r = reconcile([_spend()], [_conv(revenue="300.00", status="approved", conv_id="TXN1")])[0]
    assert r.revenue_status == "confirmed"


def test_duplicate_conversion_id_counted_once_latest_status_wins():
    from domain.reconciliation import reconcile
    # Same conversion_id appears twice: first approved, then reversed (a status UPDATE, not two events).
    # Latest-wins -> the conversion is reversed; it must not be summed twice.
    spend = [_spend(spend="100.00")]
    convs = [
        _conv(revenue="400.00", status="approved", conv_id="TXN_DUP"),
        _conv(revenue="400.00", status="reversed", conv_id="TXN_DUP"),   # same id, updated status
    ]
    r = reconcile(spend, convs)[0]
    # One conversion, now reversed -> approved sum 0, reversed sum 400 -> net -400.
    assert r.reconciled_revenue == Decimal("-400.00")    # negative allowed (clawback signal)
    assert r.reconciled_conversions == Decimal("0")      # floored at 0, not -1
    assert r.revenue_status == "reversed"
    # de-dup: the id appears once in lineage, not twice.
    assert r.source_keys.count("TXN_DUP") == 1


def test_cross_platform_dedup_same_conversion_counted_once():
    from domain.reconciliation import reconcile
    # Two spend rows (different platforms) share a token; ONE conversion on that token.
    # The single conversion must attribute once, not once per platform.
    spend = [
        _spend(spend="100.00", platform="google", campaign="CG", ad="ADG", token="tok_shared"),
        _spend(spend="80.00", platform="meta", campaign="CM", ad="ADM", token="tok_shared"),
    ]
    convs = [_conv(revenue="300.00", status="approved", conv_id="TXN_ONCE", token="tok_shared")]
    results = reconcile(spend, convs)
    # Total reconciled_revenue across grains must equal 300, not 600 (no double-count).
    total_rev = sum((r.reconciled_revenue for r in results), Decimal("0"))
    assert total_rev == Decimal("300.00")
    total_conv = sum((r.reconciled_conversions for r in results), Decimal("0"))
    assert total_conv == Decimal("1")


def test_negative_net_revenue_allowed_count_floored():
    from domain.reconciliation import reconcile
    # Reversed exceeds approved: revenue goes negative (honest), count floors at zero.
    spend = [_spend(spend="100.00")]
    convs = [
        _conv(revenue="1000.00", status="approved", conv_id="TXN_A"),
        _conv(revenue="800.00", status="reversed", conv_id="TXN_R1"),
        _conv(revenue="700.00", status="reversed", conv_id="TXN_R2"),
    ]
    r = reconcile(spend, convs)[0]
    assert r.reconciled_revenue == Decimal("-500.00")    # 1000 - 800 - 700
    assert r.reconciled_conversions == Decimal("0")      # max(0, 1 - 2)
    assert r.revenue_status == "reversed"
