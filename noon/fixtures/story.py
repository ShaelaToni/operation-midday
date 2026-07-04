"""The four demo story cases as the authored answer key (SPEC 3F: seed data and demo are one design).

This module is the SINGLE SOURCE OF TRUTH for the story cases. The seeder (seed_demo) plants rows that
realize these figures; Stage 3's golden eval imports STORY_OFFERS and asserts the reconciler reproduces
them EXACTLY. Every money value is Decimal. expected_true_profit == real_payout - total_spend, exactly.

The four cases (each tied to a demo beat, DATA_MAP / SPEC 3F):
  HIDDEN_WINNER      - platforms under-claim; real affiliate payout is far higher -> hidden profit (Beats 1-2).
  ZOMBIE             - steady spend, near-zero real payout -> a drainer (the Free-up line).
  OVERNIGHT_REVERSAL - looked profitable, then payouts reversed -> verdict flips (Beat 4).
  ID_MISMATCH        - revenue token differs from spend token -> forces the offer+geo+date fallback join,
                       proving the reconciler recovers the win instead of dropping the revenue.
"""
from __future__ import annotations

from decimal import Decimal

STORY_OFFERS: dict[str, dict] = {
    "HIDDEN_WINNER": {
        "offer_id": "OFFER_HW",
        "geo": "US",
        "tracking_token": "tok_story_hw",          # spend-side token (revenue matches it)
        "total_spend": Decimal("1200.00"),
        "platform_claimed_revenue": Decimal("1400.00"),  # platforms make it look marginal (+200)
        "real_payout": Decimal("3600.00"),               # affiliate truth: 3x spend
        "expected_true_profit": Decimal("2400.00"),      # 3600.00 - 1200.00
    },
    "ZOMBIE": {
        "offer_id": "OFFER_ZOM",
        "geo": "US",
        "tracking_token": "tok_story_zom",
        "total_spend": Decimal("340.00"),
        "platform_claimed_revenue": Decimal("400.00"),   # platform claims it is fine
        "real_payout": Decimal("60.00"),                 # reality: almost nothing pays out
        "expected_true_profit": Decimal("-280.00"),      # 60.00 - 340.00
    },
    "OVERNIGHT_REVERSAL": {
        "offer_id": "OFFER_REV",
        "geo": "CA",
        "tracking_token": "tok_story_rev",
        "total_spend": Decimal("800.00"),
        "platform_claimed_revenue": Decimal("1500.00"),  # platform still shows the pre-reversal figure
        "pre_reversal_payout": Decimal("1500.00"),       # what it looked like before the clawback
        "reversed_amount": Decimal("1200.00"),           # clawed back overnight (status -> reversed)
        "real_payout": Decimal("300.00"),                # 1500.00 - 1200.00
        "expected_true_profit": Decimal("-500.00"),      # 300.00 - 800.00
    },
    "ID_MISMATCH": {
        "offer_id": "OFFER_IDM",
        "geo": "GB",
        "tracking_token": "tok_story_idm_spend",         # top-level aliases the SPEND-side token
        "spend_tracking_token": "tok_story_idm_spend",
        "revenue_tracking_token": "tok_story_idm_revenue",  # deliberately different -> fallback join
        "total_spend": Decimal("500.00"),
        "platform_claimed_revenue": Decimal("550.00"),
        "real_payout": Decimal("1100.00"),               # a real win, recovered via the fallback join
        "expected_true_profit": Decimal("600.00"),       # 1100.00 - 500.00
    },
}
