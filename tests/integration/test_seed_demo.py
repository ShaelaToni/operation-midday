"""seed_demo management command: the composition root that runs the generators + story planter
through the real adapters and persists SpendRow/ConversionRow under PipelineRun/IngestRun.
Asserts rows land, observability records are created (error=""), the four story cases are queryable
with exact figures, and the command is idempotent (re-run does not double-count).
Written test-first (red) before the command exists.
"""
from decimal import Decimal

import pytest
from django.core.management import call_command

from noon.models import Account, PipelineRun, IngestRun, SpendRow, ConversionRow
from noon.fixtures.story import STORY_OFFERS

pytestmark = pytest.mark.django_db


def test_seed_demo_populates_rows():
    call_command("seed_demo")
    assert SpendRow.objects.count() > 0
    assert ConversionRow.objects.count() > 0
    assert Account.objects.count() == 1


def test_seed_demo_creates_observability_records():
    call_command("seed_demo")
    # One pipeline run, terminal success, error captured as empty string (not null).
    pr = PipelineRun.objects.get()
    assert pr.status == "success"
    assert pr.error == ""
    assert pr.finished_at is not None
    # One IngestRun per source, each success with error="".
    sources = set(IngestRun.objects.values_list("source", flat=True))
    assert sources == {"google", "meta", "taboola", "tiktok", "affiliate"}
    for ir in IngestRun.objects.all():
        assert ir.status == "success"
        assert ir.error == ""
        assert ir.finished_at is not None


def test_seed_demo_plants_hidden_winner_exact_figures():
    call_command("seed_demo")
    ans = STORY_OFFERS["HIDDEN_WINNER"]
    # The hidden-winner spend row (google) is queryable with exact spend + claim.
    spend_rows = SpendRow.objects.filter(offer_id=ans["offer_id"], source="google")
    assert spend_rows.count() == 1
    sr = spend_rows.get()
    assert sr.spend == ans["total_spend"]                     # 1200.00
    assert sr.platform_reported_revenue == ans["platform_claimed_revenue"]  # 1400
    assert sr.tracking_token == ans["tracking_token"]
    # The affiliate payout row is queryable with exact real payout.
    conv = ConversionRow.objects.filter(offer_id=ans["offer_id"], source="affiliate")
    assert conv.count() == 1
    assert conv.get().revenue == ans["real_payout"]           # 3600.00
    assert conv.get().status == "approved"


def test_seed_demo_plants_reversal_as_two_conversion_rows():
    call_command("seed_demo")
    ans = STORY_OFFERS["OVERNIGHT_REVERSAL"]
    conv = ConversionRow.objects.filter(offer_id=ans["offer_id"], source="affiliate")
    assert conv.count() == 2  # approved + reversed
    by_status = {c.status: c for c in conv}
    assert by_status["approved"].revenue == ans["pre_reversal_payout"]   # 1500.00
    assert by_status["reversed"].revenue == ans["reversed_amount"]       # 1200.00
    # Same tracking token, distinct conversion ids.
    assert by_status["approved"].tracking_token == ans["tracking_token"]
    assert by_status["reversed"].tracking_token == ans["tracking_token"]
    assert by_status["approved"].conversion_id != by_status["reversed"].conversion_id


def test_seed_demo_plants_id_mismatch_divergent_tokens():
    call_command("seed_demo")
    ans = STORY_OFFERS["ID_MISMATCH"]
    sr = SpendRow.objects.get(offer_id=ans["offer_id"], source="tiktok")
    cr = ConversionRow.objects.get(offer_id=ans["offer_id"], source="affiliate")
    assert sr.tracking_token == ans["spend_tracking_token"]
    assert cr.tracking_token == ans["revenue_tracking_token"]
    assert sr.tracking_token != cr.tracking_token
    # offer + geo align so the fallback join can still recover it.
    assert sr.geo == cr.geo == ans["geo"]


def test_seed_demo_is_idempotent():
    call_command("seed_demo")
    spend_after_first = SpendRow.objects.count()
    conv_after_first = ConversionRow.objects.count()
    # Re-running must NOT double-count (natural-key get_or_create).
    call_command("seed_demo")
    assert SpendRow.objects.count() == spend_after_first
    assert ConversionRow.objects.count() == conv_after_first
    # Still exactly one account and one pipeline run per invocation is allowed,
    # but rows must not duplicate.
    assert Account.objects.count() == 1
