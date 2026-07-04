"""Report-builder unit test (PURE - no Django). build_report takes plain ProfitResult records
(what the ORM reader will map ProfitFacts into) and returns a ReportData payload: the claim-vs-real
gap, per-offer profit-ranked money moves (fuel winners / free up drainers), and a worth-acting-on
total. Written test-first (red). The full rules/thresholds/min-volume-floor are Stage 5 - this is
the thin delivery slice."""
from decimal import Decimal

from domain.records import ProfitResult


def _grain(offer_id, spend, real, claim, platform="google"):
    # One per-grain profit fact (the shape the ORM reader yields to build_report).
    from datetime import date
    return ProfitResult(
        date=date(2026, 1, 15), platform=platform, campaign_id="C1", ad_id="A1",
        offer_id=offer_id, geo="US", spend=Decimal(spend),
        reconciled_conversions=Decimal("1"), reconciled_revenue=Decimal(real),
        platform_reported_revenue=(None if claim is None else Decimal(claim)),
        revenue_status="confirmed",
    )


def test_gap_headline_sums_claim_and_real():
    from application.report import build_report
    facts = [
        _grain("OFFER_W", spend="100", real="400", claim="500"),
        _grain("OFFER_D", spend="340", real="60", claim="90"),
    ]
    r = build_report(facts)
    assert r.total_claim == Decimal("590")   # 500 + 90
    assert r.total_real == Decimal("460")     # 400 + 60
    # gap multiple = claim / real (guarded)
    assert round(r.gap_multiple, 2) == round(Decimal("590") / Decimal("460"), 2)


def test_null_claim_excluded_from_gap():
    from application.report import build_report
    facts = [
        _grain("OFFER_W", spend="100", real="400", claim="500"),
        _grain("OFFER_S", spend="50", real="30", claim=None),  # claim-sparse: no platform claim
    ]
    r = build_report(facts)
    assert r.total_claim == Decimal("500")   # null excluded
    assert r.total_real == Decimal("430")     # real still counts


def test_moves_rank_winner_above_drainer():
    from application.report import build_report
    facts = [
        _grain("OFFER_D", spend="340", real="60", claim="90"),    # profit -280 (drainer)
        _grain("OFFER_W", spend="100", real="400", claim="500"),  # profit +300 (winner)
    ]
    r = build_report(facts)
    # Winner ranks first (highest profit), drainer last.
    assert r.moves[0].offer_id == "OFFER_W"
    assert r.moves[0].action == "fuel"
    assert r.moves[-1].offer_id == "OFFER_D"
    assert r.moves[-1].action == "free_up"


def test_per_offer_aggregation_across_grains():
    from application.report import build_report
    # Same offer, two platform grains -> aggregate to one move.
    facts = [
        _grain("OFFER_W", spend="100", real="400", claim="500", platform="google"),
        _grain("OFFER_W", spend="50", real="200", claim="250", platform="meta"),
    ]
    r = build_report(facts)
    w = [m for m in r.moves if m.offer_id == "OFFER_W"]
    assert len(w) == 1                        # one move per offer, not per grain
    # profit = (400+200) - (100+50) = 450
    assert w[0].action == "fuel"


def test_worth_acting_on_sums_recoverable_drainer_spend():
    from application.report import build_report
    facts = [
        _grain("OFFER_W", spend="100", real="400", claim="500"),   # winner, not recoverable
        _grain("OFFER_D", spend="340", real="60", claim="90"),     # drainer, recoverable ~340
        _grain("OFFER_D2", spend="200", real="20", claim="30"),    # drainer, recoverable ~200
    ]
    r = build_report(facts)
    # worth acting on = recoverable drainer spend (the drainers' spend), winners excluded.
    assert r.worth_acting_on == Decimal("540")  # 340 + 200


def test_empty_state_is_graceful():
    from application.report import build_report
    r = build_report([])
    assert r.total_claim == Decimal("0")
    assert r.total_real == Decimal("0")
    assert r.moves == []
    assert r.worth_acting_on == Decimal("0")
    # gap_multiple must not divide by zero - safe default.
    assert r.gap_multiple == Decimal("0")
