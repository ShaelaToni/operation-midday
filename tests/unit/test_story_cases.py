"""The four demo story cases as an assertable answer key (SPEC 3F: seed data and demo are one design).
These invariants define what each case MEANS; the seeder plants them and Stage 3's golden eval asserts
the reconciler reproduces them. Written test-first (red) before noon/fixtures/story.py exists.
"""
from decimal import Decimal

import pytest


def test_story_offers_exist_and_are_distinct():
    from noon.fixtures.story import STORY_OFFERS

    # Four named story cases, each keyed by a stable offer_id.
    assert set(STORY_OFFERS.keys()) == {
        "HIDDEN_WINNER", "ZOMBIE", "OVERNIGHT_REVERSAL", "ID_MISMATCH"
    }
    offer_ids = [c["offer_id"] for c in STORY_OFFERS.values()]
    assert len(offer_ids) == len(set(offer_ids)), "story offer_ids must be distinct"


def test_each_case_has_required_answer_key_fields():
    from noon.fixtures.story import STORY_OFFERS

    for name, case in STORY_OFFERS.items():
        for field in ("offer_id", "geo", "tracking_token", "total_spend",
                      "platform_claimed_revenue", "real_payout", "expected_true_profit"):
            assert field in case, f"{name} missing answer-key field: {field}"
        # Money fields are Decimal (never float).
        for money in ("total_spend", "platform_claimed_revenue", "real_payout", "expected_true_profit"):
            assert isinstance(case[money], Decimal), f"{name}.{money} must be Decimal"


def test_hidden_winner_real_payout_exceeds_platform_claim():
    from noon.fixtures.story import STORY_OFFERS
    w = STORY_OFFERS["HIDDEN_WINNER"]
    # The whole point: platforms UNDER-claim; real payout is much higher -> hidden profit.
    assert w["real_payout"] > w["platform_claimed_revenue"]
    assert w["expected_true_profit"] > Decimal("0")
    # Platforms make it look marginal; reality is strongly positive.
    assert w["real_payout"] > w["total_spend"] * Decimal("2")


def test_zombie_real_payout_near_zero_against_real_spend():
    from noon.fixtures.story import STORY_OFFERS
    z = STORY_OFFERS["ZOMBIE"]
    # Steady spend, real payout ~0 -> a drainer. True profit is negative.
    assert z["total_spend"] > Decimal("0")
    assert z["real_payout"] < z["total_spend"] * Decimal("0.25")
    assert z["expected_true_profit"] < Decimal("0")


def test_overnight_reversal_has_reversed_portion():
    from noon.fixtures.story import STORY_OFFERS
    r = STORY_OFFERS["OVERNIGHT_REVERSAL"]
    # Revenue looked good then reversed: the case must carry a reversed amount that
    # drops real payout below the pre-reversal figure.
    assert "pre_reversal_payout" in r and "reversed_amount" in r
    assert r["reversed_amount"] > Decimal("0")
    assert r["real_payout"] == r["pre_reversal_payout"] - r["reversed_amount"]
    assert r["real_payout"] < r["pre_reversal_payout"]


def test_id_mismatch_token_does_not_match_spend_side():
    from noon.fixtures.story import STORY_OFFERS
    m = STORY_OFFERS["ID_MISMATCH"]
    # The revenue-side token deliberately differs from the spend-side token, forcing
    # the offer+geo+date fallback join (proves the reconciler handles messy data).
    assert "spend_tracking_token" in m and "revenue_tracking_token" in m
    assert m["spend_tracking_token"] != m["revenue_tracking_token"]
