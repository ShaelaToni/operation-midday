"""reconcile management command: composition root that maps SpendRow/ConversionRow -> pure dataclasses,
calls domain.reconcile(), and persists ProfitFacts (grain_key, ruleset_version, idempotent via
update_or_create). Wrapped in a PipelineRun. Seeds the story cases (filler=0) then reconciles and
asserts the ProfitFacts reproduce the answer key. Written test-first (red) before the command exists.
"""
from decimal import Decimal

import pytest
from django.core.management import call_command

from noon.models import Account, PipelineRun, ProfitFact, SpendRow, ConversionRow
from noon.fixtures.story import STORY_OFFERS

pytestmark = pytest.mark.django_db


def _seed_and_reconcile():
    call_command("seed_demo", filler=0)   # story cases only, deterministic
    call_command("reconcile")


def test_reconcile_populates_profit_facts():
    _seed_and_reconcile()
    assert ProfitFact.objects.count() > 0


def test_reconcile_creates_pipeline_run():
    _seed_and_reconcile()
    # A reconcile PipelineRun exists, terminal success, error="" (observability).
    assert PipelineRun.objects.filter(status="success").exists()
    for pr in PipelineRun.objects.all():
        assert pr.error == ""


def test_reconcile_hidden_winner_true_profit():
    _seed_and_reconcile()
    ans = STORY_OFFERS["HIDDEN_WINNER"]
    pf = ProfitFact.objects.get(offer_id=ans["offer_id"], platform="google")
    # reconciled_revenue is the affiliate payout, not the platform claim.
    assert pf.reconciled_revenue == ans["real_payout"]        # 3600.00
    assert pf.spend == ans["total_spend"]                     # 1200.00
    # true profit = reconciled_revenue - spend matches the answer key.
    assert pf.reconciled_revenue - pf.spend == ans["expected_true_profit"]  # 2400.00
    assert pf.attribution == "token"                          # clean token match


def test_reconcile_id_mismatch_recovered_via_fallback():
    _seed_and_reconcile()
    ans = STORY_OFFERS["ID_MISMATCH"]
    # The tiktok spend grain recovers the affiliate payout via offer+geo+date fallback.
    pf = ProfitFact.objects.get(offer_id=ans["offer_id"], platform="tiktok")
    assert pf.reconciled_revenue == ans["real_payout"]        # 1100.00 recovered
    assert pf.reconciled_revenue - pf.spend == ans["expected_true_profit"]  # 600.00
    assert pf.attribution == "fallback"                       # flagged as fallback join


def test_reconcile_is_idempotent():
    _seed_and_reconcile()
    count_first = ProfitFact.objects.count()
    call_command("reconcile")   # re-run
    assert ProfitFact.objects.count() == count_first   # update_or_create, no duplicates
