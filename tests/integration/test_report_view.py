"""Report-view integration test. The Noon Report page ties read_profit_facts -> build_report ->
template, with NO ORM in the view. Asserts the page renders (200) with the gap numbers, and that
the empty-state (no data) renders gracefully rather than crashing. Written test-first (red)."""
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from noon.models import Account, ProfitFact

pytestmark = pytest.mark.django_db


def _fact(account, offer_id, spend, real, claim, grain):
    return ProfitFact.objects.create(
        account=account, date=date(2026, 1, 15), platform="google", campaign_id="C1",
        ad_id="A1", offer_id=offer_id, geo="US", spend=Decimal(spend),
        reconciled_conversions=Decimal("1"), reconciled_revenue=Decimal(real),
        platform_reported_revenue=(None if claim is None else Decimal(claim)),
        revenue_status="confirmed", attribution="token", ruleset_version="v1", grain_key=grain,
    )


def test_report_page_renders_with_gap(client):
    acct = Account.objects.create(name="Demo Account", timezone="US/Eastern", currency="USD")
    _fact(acct, "OFFER_W", "100", "400", "500", "g1")
    _fact(acct, "OFFER_D", "340", "60", "90", "g2")
    resp = client.get(reverse("noon:report"))
    assert resp.status_code == 200
    body = resp.content.decode()
    # The gap numbers (claim 590, real 460) appear on the page (formatting may add $ / commas).
    assert "590" in body
    assert "460" in body
    # A money move for the winner and the drainer are present.
    assert "OFFER_W" in body
    assert "OFFER_D" in body


def test_report_page_empty_state_does_not_crash(client):
    # No account, no data - the page must still render (200), not 500.
    resp = client.get(reverse("noon:report"))
    assert resp.status_code == 200
