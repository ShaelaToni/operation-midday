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


def _dedup_conversions(conversions: list[ConversionRecord]) -> list[ConversionRecord]:
    """De-dup by conversion_id, keeping the LAST occurrence (arrival order = latest status).
    A re-sent conversion_id is a status update, not a second event. ConversionRecord has no
    timestamp, so list order is the only 'latest' signal available (V2: real timestamp ordering)."""
    latest: dict[str, ConversionRecord] = {}
    for c in conversions:
        latest[c.conversion_id] = c  # later occurrence overwrites earlier
    return list(latest.values())


def _assign_conversions_to_grains(
    grains: dict[tuple, dict], conversions: list[ConversionRecord]
) -> dict[tuple, list[ConversionRecord]]:
    """Attribute each conversion to exactly ONE grain: the first grain (in sorted grain-key
    order) whose token set contains the conversion's token. Counted once total - a conversion
    whose token is shared by multiple grains does not double-count.
    V1 LIMIT: the non-winning sharing grain shows spend with zero revenue for this conversion
    (a documented false-zombie risk); safe here because seeded story data is single-platform per
    offer. V2: proportional / multi-touch split."""
    matched: dict[tuple, list[ConversionRecord]] = {key: [] for key in grains}
    sorted_keys = sorted(grains.keys())
    for c in conversions:
        if not c.tracking_token:
            continue  # unjoinable by token; fallback join handled later (3c)
        for key in sorted_keys:
            if c.tracking_token in grains[key]["tokens"]:
                matched[key].append(c)
                break  # first matching grain wins - counted once
    return matched


def _build_result(grain: dict, matched: list[ConversionRecord]) -> ProfitResult:
    """Aggregate matched conversions at the grain under the status contract.
    reconciled_revenue = SUM(approved) - SUM(reversed) (may be negative - honest clawback signal).
    reconciled_conversions = max(0, #approved - #reversed) (floored; a count can't be negative).
    rejected + pending contribute nothing. revenue_status: reversed > provisional(pending) > confirmed."""
    s = grain["sample"]
    approved = [c for c in matched if c.status == "approved"]
    reversed_ = [c for c in matched if c.status == "reversed"]
    has_pending = any(c.status == "pending" for c in matched)

    approved_rev = sum((c.revenue for c in approved), Decimal("0"))
    reversed_rev = sum((c.revenue for c in reversed_), Decimal("0"))
    reconciled_revenue = approved_rev - reversed_rev  # may be negative

    net_count = len(approved) - len(reversed_)
    reconciled_conversions = Decimal(max(0, net_count))  # floored at zero

    if reversed_:
        revenue_status = "reversed"
    elif has_pending:
        revenue_status = "provisional"
    else:
        revenue_status = "confirmed"

    # Lineage: approved + reversed ids (the rows that moved the number), deduped, order-stable.
    source_keys: list[str] = []
    for c in approved + reversed_:
        if c.conversion_id not in source_keys:
            source_keys.append(c.conversion_id)

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
    """Join spend to revenue on the tracking token, aggregate to the grain under the status
    contract, and return one ProfitResult per spend grain. reconciled_revenue is the real
    affiliate payout net of reversals (the truth); the platform claim is carried through for the
    downstream gap, never into the profit number. Each conversion counts once (deduped by id,
    attributed to one grain)."""
    grains = _aggregate_spend(spend_records)
    deduped = _dedup_conversions(conversions)
    matched_by_grain = _assign_conversions_to_grains(grains, deduped)

    results: list[ProfitResult] = []
    for key, grain in grains.items():
        results.append(_build_result(grain, matched_by_grain[key]))
    return results
