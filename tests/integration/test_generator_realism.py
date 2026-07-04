"""Generator economic-realism guard. Real platform over-claim is ~15-50% (Meta ~26%, Google ~15-20%;
~15% normal variance, 40-50% high end - Varos/Google benchmarks 2024-25). The filler generators must
produce an aggregate gap in that believable band, not the incoherent ~32x that decoupled random
claim/payout produced. Asserts on the RECONCILED aggregate (what the report shows), through the real
pipeline. Written test-first (red) - fails against the current incoherent generators.
"""
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db.models import Sum

from noon.models import ProfitFact

pytestmark = pytest.mark.django_db


def test_filler_aggregate_gap_is_believable():
    # Seed a meaningful volume of filler (plus story cases) and run the real pipeline.
    call_command("seed_demo", filler=200)
    call_command("reconcile")

    total_claim = ProfitFact.objects.aggregate(s=Sum("platform_reported_revenue"))["s"] or Decimal("0")
    total_real = ProfitFact.objects.aggregate(s=Sum("reconciled_revenue"))["s"] or Decimal("0")

    assert total_real > 0, "no reconciled revenue - filler is not joining spend to payout"
    ratio = total_claim / total_real
    # Believable gap = platform over-claim (1.15-1.5) times status attrition: reconciled real is
    # net of reversed/rejected/pending (~half of raw), so claim-vs-reconciled runs ~1.1-3.5x.
    # This is the honest Noon gap (platforms claim on conversions that don't all survive to payout).
    assert Decimal("1.1") <= ratio <= Decimal("3.5"), (
        f"aggregate gap unbelievable: claim {total_claim} / reconciled real {total_real} = {ratio:.2f}x "
        f"(expected 1.1-3.5x: over-claim x status attrition)")


def test_filler_produces_joinable_revenue():
    # Coherent filler must produce substantial ATTRIBUTED (token or fallback) revenue,
    # not mostly unattributed orphans - proving spend and payout actually share offers/tokens.
    call_command("seed_demo", filler=200)
    call_command("reconcile")
    attributed = ProfitFact.objects.exclude(attribution="unattributed").aggregate(
        s=Sum("reconciled_revenue"))["s"] or Decimal("0")
    total = ProfitFact.objects.aggregate(s=Sum("reconciled_revenue"))["s"] or Decimal("0")
    assert total > 0
    # The majority of real revenue should attribute to spend (shared offer/token), not orphan.
    assert attributed / total >= Decimal("0.5"), (
        f"most revenue is unattributed ({attributed}/{total}) - spend and payout are not sharing "
        f"offers/tokens; the filler is still decoupled")
