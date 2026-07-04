"""Reconciliation core (the crown jewel) - PURE domain, standard library + domain.records only.

Joins spend to revenue on the tracking token, aggregates to the grain
(date | platform | campaign | ad | offer | geo), and produces ProfitResult facts. The
reconciled_revenue is the REAL affiliate payout - the reconciler trusts the revenue side; the
platform's claimed revenue is carried through only so downstream can surface the gap.

No Django, no ORM, no I/O - the composition root maps ORM rows to/from these dataclasses. This
purity is what makes the reconciliation logic unit-testable without a database (boundary-tested).

This module currently implements the token-join happy path + grain aggregation. Reversals/status
handling, the offer+geo+date fallback join, and orphan/zero-conversion handling are added by
subsequent steps that EXTEND this skeleton (they do not replace it).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from domain.records import SpendRecord, ConversionRecord, ProfitResult

# The reconciliation grain: one ProfitResult per unique tuple of these spend dimensions.
_GRAIN_FIELDS = ("date", "platform", "campaign_id", "ad_id", "offer_id", "geo")


def _grain_key(spend: SpendRecord) -> tuple:
    return tuple(getattr(spend, f) for f in _GRAIN_FIELDS)


def _aggregate_spend(spend_records: list[SpendRecord]) -> dict[tuple, dict]:
    """Group spend into grains. Each grain accumulates spend and carries the platform claim.
    Multiple spend rows on the same grain sum their spend; the claim sums where present."""
    grains: dict[tuple, dict] = {}
    for s in spend_records:
        key = _grain_key(s)
        g = grains.get(key)
        if g is None:
            grains[key] = {
                "spend": s.spend,
                "platform_reported_revenue": s.platform_reported_revenue,
                "tokens": {s.tracking_token} if s.tracking_token else set(),
                "sample": s,  # carries grain dimensions for the result
            }
        else:
            g["spend"] += s.spend
            if s.platform_reported_revenue is not None:
                base = g["platform_reported_revenue"] or Decimal("0")
                g["platform_reported_revenue"] = base + s.platform_reported_revenue
            if s.tracking_token:
                g["tokens"].add(s.tracking_token)
    return grains


def _index_conversions_by_token(conversions: list[ConversionRecord]) -> dict[str, list[ConversionRecord]]:
    """Index conversions by their tracking token for the primary join."""
    by_token: dict[str, list[ConversionRecord]] = defaultdict(list)
    for c in conversions:
        if c.tracking_token:
            by_token[c.tracking_token].append(c)
    return by_token


def _build_result(grain: dict, matched: list[ConversionRecord]) -> ProfitResult:
    """Aggregate matched conversions at the grain and build the ProfitResult.
    reconciled_revenue = summed affiliate payout; reconciled_conversions = count; lineage recorded."""
    s = grain["sample"]
    reconciled_revenue = sum((c.revenue for c in matched), Decimal("0"))
    reconciled_conversions = Decimal(len(matched))
    source_keys = [c.conversion_id for c in matched]
    revenue_status = "confirmed" if matched else "provisional"
    return ProfitResult(
        date=s.date,
        platform=s.platform,
        campaign_id=s.campaign_id,
        ad_id=s.ad_id,
        offer_id=s.offer_id,
        geo=s.geo,
        spend=grain["spend"],
        reconciled_conversions=reconciled_conversions,
        reconciled_revenue=reconciled_revenue,
        platform_reported_revenue=grain["platform_reported_revenue"],
        revenue_status=revenue_status,
        source_keys=source_keys,
    )


def reconcile(spend_records: list[SpendRecord],
              conversions: list[ConversionRecord]) -> list[ProfitResult]:
    """Join spend to revenue on the tracking token, aggregate to the grain, and return one
    ProfitResult per spend grain. reconciled_revenue is the real affiliate payout (the truth);
    the platform claim is carried through for the downstream gap, never into the profit number."""
    grains = _aggregate_spend(spend_records)
    convs_by_token = _index_conversions_by_token(conversions)

    results: list[ProfitResult] = []
    for key, grain in grains.items():
        matched: list[ConversionRecord] = []
        for token in grain["tokens"]:
            matched.extend(convs_by_token.get(token, []))
        results.append(_build_result(grain, matched))
    return results
