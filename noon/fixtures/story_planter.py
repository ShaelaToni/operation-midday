"""Build the four demo story cases as RAW source rows in each assigned platform's real schema.

Run through the real adapters, these rows reproduce the EXACT STORY_OFFERS answer-key figures -
the "simulate inputs, not outputs" contract: even the hand-crafted demo story flows through the
genuine ingest pipeline, never written as pre-computed results. Each case is assigned to one spend
platform so the four cases exercise all four spend adapters:
  HIDDEN_WINNER -> google, ZOMBIE -> meta, OVERNIGHT_REVERSAL -> taboola, ID_MISMATCH -> tiktok.
The platform claim lives in a different raw field per adapter (that is the point - real schemas differ).
"""
from __future__ import annotations

from decimal import Decimal

from noon.fixtures.story import STORY_OFFERS

# A fixed date inside the seeded window for the story rows (deterministic, not clock-relative).
_STORY_DATE = "2026-01-15"


def _dollars_to_micros(amount: Decimal) -> int:
    """Google reports cost in millionths; the adapter divides back. 1200.00 -> 1200000000."""
    return int((amount * Decimal("1000000")).to_integral_value())


def _google_spend_row(ans: dict) -> dict:
    return {
        "campaign.id": f"C_{ans['offer_id']}",
        "campaign.name": f"{ans['offer_id']} Campaign",
        "segments.date": _STORY_DATE,
        "metrics.cost_micros": _dollars_to_micros(ans["total_spend"]),
        "metrics.impressions": 100000,
        "metrics.clicks": 1000,
        "metrics.conversions": 40,
        "metrics.conversions_value": float(ans["platform_claimed_revenue"]),
        "geographic_view.country": ans["geo"],
        "ad_group_ad.ad.id": f"AD_{ans['offer_id']}",
        "ad_group_ad.ad.name": f"Ad {ans['offer_id']}",
        "tracking_token": ans["tracking_token"],
        "offer_id": ans["offer_id"],
    }


def _meta_spend_row(ans: dict) -> dict:
    return {
        "campaign_id": f"C_{ans['offer_id']}",
        "campaign_name": f"{ans['offer_id']} Campaign",
        "adset_id": f"AS_{ans['offer_id']}",
        "adset_name": f"Adset {ans['offer_id']}",
        "ad_id": f"AD_{ans['offer_id']}",
        "ad_name": f"Ad {ans['offer_id']}",
        "date_start": _STORY_DATE,
        "date_stop": _STORY_DATE,
        "spend": f"{ans['total_spend']:.2f}",  # dollars, NOT micros
        "impressions": "50000",
        "clicks": "500",
        "actions": [{"action_type": "lead", "value": "40"}],
        # Platform claim rides in nested action_values keyed by lead.
        "action_values": [{"action_type": "lead", "value": f"{ans['platform_claimed_revenue']:.2f}"}],
        "account_currency": "USD",
        "geo": ans["geo"],
        "tracking_token": ans["tracking_token"],
        "offer_id": ans["offer_id"],
    }


def _taboola_spend_row(ans: dict) -> dict:
    return {
        "campaign_id": f"C_{ans['offer_id']}",
        "campaign_name": f"{ans['offer_id']} Native",
        "date": _STORY_DATE,
        "spent": f"{ans['total_spend']:.2f}",
        "impressions": "80000",
        "visible_impressions": "60000",
        "clicks": "300",
        "cpa_actions_num": "40",
        "conversions_value": f"{ans['platform_claimed_revenue']:.2f}",
        "currency": "USD",
        "timezone": "EST",
        "item": f"IT_{ans['offer_id']}",
        "item_name": f"Native {ans['offer_id']}",
        "url": f"https://example.com/lp/{ans['offer_id'].lower()}",
        "country": ans["geo"],
        "tracking_token": ans["tracking_token"],
        "offer_id": ans["offer_id"],
    }


def _tiktok_spend_row(ans: dict, tracking_token: str) -> dict:
    return {
        "dimensions": {
            "stat_time_day": _STORY_DATE,
            "campaign_id": f"C_{ans['offer_id']}",
            "adgroup_id": f"AG_{ans['offer_id']}",
            "ad_id": f"AD_{ans['offer_id']}",
            "country_code": ans["geo"],
        },
        "metrics": {
            "spend": f"{ans['total_spend']:.2f}",
            "impressions": "40000",
            "clicks": "220",
            "conversion": "40",
            "conversion_value": f"{ans['platform_claimed_revenue']:.2f}",
            "campaign_name": f"{ans['offer_id']} TikTok",
            "adgroup_name": f"Adgroup {ans['offer_id']}",
            "ad_name": f"Ad {ans['offer_id']}",
        },
        "tracking_token": tracking_token,
        "offer_id": ans["offer_id"],
    }


def _affiliate_row(ans: dict, conversion_id: str, payout: Decimal, status: str,
                   tracking_token: str) -> dict:
    return {
        "transaction_id": conversion_id,
        "sub_id": tracking_token,
        "offer_id": ans["offer_id"],
        "payout": f"{payout:.2f}",
        "status": status,
        "timestamp": f"{_STORY_DATE}T12:00:00Z",
        "geo": ans["geo"],
    }


def build_story_rows() -> dict[str, dict]:
    """Return {case_name: {"spend": [(source, raw), ...], "affiliate": [raw, ...]}} for the four cases."""
    hw = STORY_OFFERS["HIDDEN_WINNER"]
    zom = STORY_OFFERS["ZOMBIE"]
    rev = STORY_OFFERS["OVERNIGHT_REVERSAL"]
    idm = STORY_OFFERS["ID_MISMATCH"]

    return {
        "HIDDEN_WINNER": {
            "spend": [("google", _google_spend_row(hw))],
            "affiliate": [
                _affiliate_row(hw, "TXN_HW_1", hw["real_payout"], "approved", hw["tracking_token"]),
            ],
        },
        "ZOMBIE": {
            "spend": [("meta", _meta_spend_row(zom))],
            "affiliate": [
                _affiliate_row(zom, "TXN_ZOM_1", zom["real_payout"], "approved", zom["tracking_token"]),
            ],
        },
        "OVERNIGHT_REVERSAL": {
            "spend": [("taboola", _taboola_spend_row(rev))],
            "affiliate": [
                _affiliate_row(rev, "TXN_REV_1", rev["pre_reversal_payout"], "approved", rev["tracking_token"]),
                _affiliate_row(rev, "TXN_REV_2", rev["reversed_amount"], "reversed", rev["tracking_token"]),
            ],
        },
        "ID_MISMATCH": {
            "spend": [("tiktok", _tiktok_spend_row(idm, idm["spend_tracking_token"]))],
            "affiliate": [
                _affiliate_row(idm, "TXN_IDM_1", idm["real_payout"], "approved", idm["revenue_tracking_token"]),
            ],
        },
    }
