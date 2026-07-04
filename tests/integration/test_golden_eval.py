"""GOLDEN EVAL - the answer-key assertion (SPEC 3I).

The seeded story cases ARE the answer key. This runs the full pipeline (seed -> adapters -> ORM ->
pure reconcile -> persisted ProfitFacts) and asserts every story offer reproduces its known-truth
profit, revenue, status, and attribution EXACTLY. It proves the pipeline's DECISIONS are right, not
just that individual functions work. Any future change that breaks a story case fails this test.
"""
from decimal import Decimal

import pytest
from django.core.management import call_command

from noon.models import ProfitFact
from noon.fixtures.story import STORY_OFFERS

pytestmark = pytest.mark.django_db


@pytest.fixture
def reconciled():
    call_command("seed_demo", filler=0)   # story cases only - deterministic answer key
    call_command("reconcile")


def _story_fact(offer_id):
    """The single ProfitFact for a story offer (asserts single-grain: exactly one)."""
    facts = ProfitFact.objects.filter(offer_id=offer_id)
    assert facts.count() == 1, f"{offer_id}: expected exactly one grain, got {facts.count()}"
    return facts.get()


def test_golden_all_four_true_profits(reconciled):
    # The headline: every story offer's true profit == the answer key, to the cent.
    for name, ans in STORY_OFFERS.items():
        pf = _story_fact(ans["offer_id"])
        profit = pf.reconciled_revenue - pf.spend
        assert profit == ans["expected_true_profit"], (
            f"{name}: profit {profit} != expected {ans['expected_true_profit']}")


def test_golden_reconciled_revenue_is_real_payout(reconciled):
    # reconciled_revenue is the real payout (net of reversals), never the platform claim.
    for name, ans in STORY_OFFERS.items():
        pf = _story_fact(ans["offer_id"])
        assert pf.reconciled_revenue == ans["real_payout"], (
            f"{name}: revenue {pf.reconciled_revenue} != payout {ans['real_payout']}")


def test_golden_hidden_winner_reveals_the_gap(reconciled):
    # The whole thesis: platform claims 1400, real payout is 3600 - the gap is visible.
    ans = STORY_OFFERS["HIDDEN_WINNER"]
    pf = _story_fact(ans["offer_id"])
    assert pf.platform_reported_revenue == ans["platform_claimed_revenue"]  # 1400 carried
    assert pf.reconciled_revenue == ans["real_payout"]                      # 3600 truth
    assert pf.reconciled_revenue != pf.platform_reported_revenue            # the gap exists
    assert pf.attribution == "token"


def test_golden_overnight_reversal_nets_and_flags(reconciled):
    # Reversal: 1500 approved netted against 1200 reversed = 300; grain flagged reversed.
    ans = STORY_OFFERS["OVERNIGHT_REVERSAL"]
    pf = _story_fact(ans["offer_id"])
    assert pf.reconciled_revenue == ans["real_payout"]        # 300.00 netted
    assert pf.revenue_status == "reversed"                    # the flip signal (Beat 4)


def test_golden_id_mismatch_recovered_via_fallback(reconciled):
    # Broken tracking token recovered on offer+geo+date - the win is not dropped.
    ans = STORY_OFFERS["ID_MISMATCH"]
    pf = _story_fact(ans["offer_id"])
    assert pf.reconciled_revenue == ans["real_payout"]        # 1100 recovered
    assert pf.attribution == "fallback"                       # via the fallback join


def test_golden_zombie_is_a_drainer(reconciled):
    # Spend 340, real payout only 60 -> negative profit, the caught drainer.
    ans = STORY_OFFERS["ZOMBIE"]
    pf = _story_fact(ans["offer_id"])
    assert pf.reconciled_revenue == ans["real_payout"]        # 60.00
    assert pf.reconciled_revenue - pf.spend == ans["expected_true_profit"]  # -280.00
