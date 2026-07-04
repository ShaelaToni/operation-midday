"""The story planter builds the four story cases as RAW source rows. Run through the real
adapters, they must produce the EXACT STORY_OFFERS answer-key figures - proving the seeded
demo story realizes the authored truth through the real pipeline (simulate inputs, not outputs).
Written test-first (red) before noon/fixtures/story_planter.py exists.
"""
from decimal import Decimal

import pytest

from noon.adapters.base import get_adapter
from noon.fixtures.story import STORY_OFFERS
import noon.adapters  # noqa: F401  (registers all adapters)


def _parse(source, raw):
    return get_adapter(source).parse_row(raw)


def test_planter_returns_all_four_cases():
    from noon.fixtures.story_planter import build_story_rows
    rows = build_story_rows()
    assert set(rows.keys()) == {"HIDDEN_WINNER", "ZOMBIE", "OVERNIGHT_REVERSAL", "ID_MISMATCH"}
    for case in rows.values():
        assert "spend" in case and "affiliate" in case
        assert isinstance(case["spend"], list) and isinstance(case["affiliate"], list)


def test_hidden_winner_realizes_exact_figures():
    from noon.fixtures.story_planter import build_story_rows
    hw = build_story_rows()["HIDDEN_WINNER"]
    ans = STORY_OFFERS["HIDDEN_WINNER"]
    assert len(hw["spend"]) == 1
    src, raw = hw["spend"][0]
    assert src == "google"
    k = _parse(src, raw)
    assert k["spend"] == ans["total_spend"]                       # 1200.00 (from micros)
    assert k["platform_reported_revenue"] == ans["platform_claimed_revenue"]  # 1400.00
    assert k["tracking_token"] == ans["tracking_token"]
    assert k["offer_id"] == ans["offer_id"]
    assert k["geo"] == ans["geo"]
    assert len(hw["affiliate"]) == 1
    a = _parse("affiliate", hw["affiliate"][0])
    assert a["revenue"] == ans["real_payout"]                     # 3600.00
    assert a["status"] == "approved"
    assert a["tracking_token"] == ans["tracking_token"]


def test_zombie_realizes_exact_figures():
    from noon.fixtures.story_planter import build_story_rows
    z = build_story_rows()["ZOMBIE"]
    ans = STORY_OFFERS["ZOMBIE"]
    src, raw = z["spend"][0]
    assert src == "meta"
    k = _parse(src, raw)
    assert k["spend"] == ans["total_spend"]                       # 340.00
    assert k["platform_reported_revenue"] == ans["platform_claimed_revenue"]  # 400.00
    assert k["tracking_token"] == ans["tracking_token"]
    a = _parse("affiliate", z["affiliate"][0])
    assert a["revenue"] == ans["real_payout"]                     # 60.00
    assert a["status"] == "approved"


def test_overnight_reversal_is_two_affiliate_rows_netting_correctly():
    from noon.fixtures.story_planter import build_story_rows
    r = build_story_rows()["OVERNIGHT_REVERSAL"]
    ans = STORY_OFFERS["OVERNIGHT_REVERSAL"]
    src, raw = r["spend"][0]
    assert src == "taboola"
    k = _parse(src, raw)
    assert k["spend"] == ans["total_spend"]                       # 800.00
    assert k["platform_reported_revenue"] == ans["platform_claimed_revenue"]  # 1500.00 (stale claim)
    # TWO affiliate rows: one approved (pre_reversal), one reversed (reversed_amount).
    assert len(r["affiliate"]) == 2
    parsed = [_parse("affiliate", ar) for ar in r["affiliate"]]
    by_status = {p["status"]: p for p in parsed}
    assert by_status["approved"]["revenue"] == ans["pre_reversal_payout"]   # 1500.00
    assert by_status["reversed"]["revenue"] == ans["reversed_amount"]       # 1200.00
    net = by_status["approved"]["revenue"] - by_status["reversed"]["revenue"]
    assert net == ans["real_payout"]                              # 300.00
    assert by_status["approved"]["tracking_token"] == ans["tracking_token"]
    assert by_status["reversed"]["tracking_token"] == ans["tracking_token"]
    assert by_status["approved"]["conversion_id"] != by_status["reversed"]["conversion_id"]


def test_id_mismatch_tokens_differ_across_sides():
    from noon.fixtures.story_planter import build_story_rows
    m = build_story_rows()["ID_MISMATCH"]
    ans = STORY_OFFERS["ID_MISMATCH"]
    src, raw = m["spend"][0]
    assert src == "tiktok"
    k = _parse(src, raw)
    assert k["spend"] == ans["total_spend"]                       # 500.00
    assert k["platform_reported_revenue"] == ans["platform_claimed_revenue"]  # 550.00
    assert k["tracking_token"] == ans["spend_tracking_token"]
    a = _parse("affiliate", m["affiliate"][0])
    assert a["revenue"] == ans["real_payout"]                     # 1100.00
    assert a["tracking_token"] == ans["revenue_tracking_token"]
    assert a["tracking_token"] != k["tracking_token"]
    assert a["offer_id"] == k["offer_id"] == ans["offer_id"]
    assert a["geo"] == k["geo"] == ans["geo"]
