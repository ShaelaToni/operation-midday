"""Economics module (single source of per-offer economic truth for filler) - PURE, deterministic.
Real benchmark bands (cited in the module): over-claim 1.15-1.5x (Meta ~26%, Google ~15-20%),
per-conversion payout from realistic ROAS. Tokens are per (offer, platform) so each platform's spend
joins its own payout - no cross-platform shared-token false-zombie cascade. Written test-first (red).
"""
from decimal import Decimal

import pytest


def test_offer_economics_is_deterministic():
    from noon.fixtures.economics import offer_economics
    a = offer_economics("OFFER7", seed=0)
    b = offer_economics("OFFER7", seed=0)
    assert a == b  # same offer + seed -> identical economics


def test_different_offers_differ():
    from noon.fixtures.economics import offer_economics
    a = offer_economics("OFFER1", seed=0)
    b = offer_economics("OFFER2", seed=0)
    # Per-offer variation (geo or over-claim differs across offers).
    assert (a.over_claim_factor, a.geo) != (b.over_claim_factor, b.geo)


def test_over_claim_factor_in_researched_band():
    from noon.fixtures.economics import offer_economics
    for i in range(1, 21):
        e = offer_economics(f"OFFER{i}", seed=0)
        assert Decimal("1.15") <= e.over_claim_factor <= Decimal("1.5"), (
            f"OFFER{i} over_claim {e.over_claim_factor} outside researched 1.15-1.5")


def test_geo_is_two_char():
    from noon.fixtures.economics import offer_economics
    e = offer_economics("OFFER3", seed=0)
    assert len(e.geo) == 2


def test_placement_for_any_platform_is_deterministic_and_tokened():
    from noon.fixtures.economics import placement_for
    # Every offer runs on every platform (model a): a valid placement for all four, always.
    for platform in ("google", "meta", "taboola", "tiktok"):
        p = placement_for("OFFER5", platform, seed=0)
        assert p.platform == platform
        assert p.token == f"tok_OFFER5_{platform}"          # deterministic, unique per (offer, platform)
        assert p.payout_low <= p.payout_high
        # deterministic: same call -> same result
        assert placement_for("OFFER5", platform, seed=0) == p
    # Tokens differ across platforms for the same offer (no shared token -> no false-zombie).
    tokens = {placement_for("OFFER5", p, seed=0).token for p in ("google", "meta", "taboola", "tiktok")}
    assert len(tokens) == 4


def test_some_offers_are_sparse():
    from noon.fixtures.economics import offer_economics
    sparse = [offer_economics(f"OFFER{i}", seed=0).is_sparse for i in range(1, 21)]
    assert any(sparse) and not all(sparse), "expected a realistic mix of sparse and non-sparse offers"


def test_offer_has_deterministic_conversions_weight():
    from noon.fixtures.economics import offer_economics
    e = offer_economics("OFFER7", seed=0)
    # A positive, deterministic per-offer conversion-volume weight - both sides scale to it.
    assert e.conversions_weight > 0
    assert offer_economics("OFFER7", seed=0).conversions_weight == e.conversions_weight
    # Varies across offers (not a constant).
    weights = {offer_economics(f"OFFER{i}", seed=0).conversions_weight for i in range(1, 21)}
    assert len(weights) > 1
