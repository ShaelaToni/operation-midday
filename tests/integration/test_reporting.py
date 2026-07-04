"""ORM reader integration test. noon.reporting.read_profit_facts(account) is the ONE place that
touches ProfitFact.objects - it maps persisted ProfitFacts to pure ProfitResult dataclasses, so the
view calls build_report (pure) without any ORM in the view. Written test-first (red)."""
from datetime import date
from decimal import Decimal

import pytest

from domain.records import ProfitResult
from noon.models import Account, ProfitFact

pytestmark = pytest.mark.django_db


def _fact(account, offer_id, spend, real, claim, grain):
    return ProfitFact.objects.create(
        account=account, date=date(2026, 1, 15), platform="google", campaign_id="C1",
        ad_id="A1", offer_id=offer_id, geo="US", spend=Decimal(spend),
        reconciled_conversions=Decimal("1"), reconciled_revenue=Decimal(real),
        platform_reported_revenue=(None if claim is None else Decimal(claim)),
        revenue_status="confirmed", attribution="token", ruleset_version="v1",
        grain_key=grain,
    )


def test_reader_maps_profitfacts_to_profitresults():
    from noon.reporting import read_profit_facts
    acct = Account.objects.create(name="Demo", timezone="US/Eastern", currency="USD")
    _fact(acct, "OFFER_W", "100", "400", "500", "g1")
    _fact(acct, "OFFER_D", "340", "60", None, "g2")

    results = read_profit_facts(acct)

    assert len(results) == 2
    assert all(isinstance(r, ProfitResult) for r in results)
    by_offer = {r.offer_id: r for r in results}
    assert by_offer["OFFER_W"].reconciled_revenue == Decimal("400")
    assert by_offer["OFFER_W"].platform_reported_revenue == Decimal("500")
    assert by_offer["OFFER_W"].spend == Decimal("100")
    # Null claim maps through as None (not zero) - claim-side sparsity preserved.
    assert by_offer["OFFER_D"].platform_reported_revenue is None


def test_reader_empty_account_returns_empty_list():
    from noon.reporting import read_profit_facts
    acct = Account.objects.create(name="Empty", timezone="US/Eastern", currency="USD")
    assert read_profit_facts(acct) == []
