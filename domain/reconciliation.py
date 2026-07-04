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
) -> tuple[dict[tuple, list[ConversionRecord]], list[ConversionRecord]]:
    """Primary token join: attribute each conversion to the first grain (sorted key order) whose
    token set contains its token. Returns (matched_by_grain, unmatched) where unmatched are the
    conversions whose token hit no grain - handed to the fallback join."""
    matched: dict[tuple, list[ConversionRecord]] = {key: [] for key in grains}
    unmatched: list[ConversionRecord] = []
    sorted_keys = sorted(grains.keys())
    for c in conversions:
        hit = None
        if c.tracking_token:
            for key in sorted_keys:
                if c.tracking_token in grains[key]["tokens"]:
                    hit = key
                    break
        if hit is not None:
            matched[hit].append(c)
        else:
            unmatched.append(c)
    return matched, unmatched


def _fallback_assign(
    grains: dict[tuple, dict], unmatched: list[ConversionRecord]
) -> tuple[dict[tuple, list[ConversionRecord]], set[tuple], list[ConversionRecord]]:
    """Fallback join on (offer_id, geo, date). Exactly-one grain -> attribute there (and mark the
    grain fallback-touched). Ambiguous (>1) or no match -> unattributed. Returns
    (fallback_by_grain, fallback_touched_keys, still_unattributed)."""
    # Index grains by their (offer_id, geo, date) coarse key.
    coarse: dict[tuple, list[tuple]] = {}
    for key, g in grains.items():
        s = g["sample"]
        coarse.setdefault((s.offer_id, s.geo, s.date), []).append(key)
    fallback_by_grain: dict[tuple, list[ConversionRecord]] = {key: [] for key in grains}
    fallback_touched: set[tuple] = set()
    unattributed: list[ConversionRecord] = []
    for c in unmatched:
        candidates = coarse.get((c.offer_id, c.geo, c.date), [])
        if len(candidates) == 1:                 # exactly one -> recover via fallback
            key = candidates[0]
            fallback_by_grain[key].append(c)
            fallback_touched.add(key)
        else:                                    # ambiguous (>1) or none -> never guess
            unattributed.append(c)
    return fallback_by_grain, fallback_touched, unattributed


def _build_result(grain: dict, matched: list[ConversionRecord], attribution: str) -> ProfitResult:
    """Status-aware aggregation at a grain. reconciled_revenue = SUM(approved) - SUM(reversed)
    (may be negative); reconciled_conversions = max(0, #approved - #reversed); rejected+pending
    excluded; revenue_status reversed>provisional>confirmed. attribution passed in (token/fallback)."""
    s = grain["sample"]
    approved = [c for c in matched if c.status == "approved"]
    reversed_ = [c for c in matched if c.status == "reversed"]
    has_pending = any(c.status == "pending" for c in matched)

    reconciled_revenue = (sum((c.revenue for c in approved), Decimal("0"))
                          - sum((c.revenue for c in reversed_), Decimal("0")))
    reconciled_conversions = Decimal(max(0, len(approved) - len(reversed_)))

    if reversed_:
        revenue_status = "reversed"
    elif has_pending:
        revenue_status = "provisional"
    else:
        revenue_status = "confirmed"

    source_keys: list[str] = []
    for c in approved + reversed_:
        if c.conversion_id not in source_keys:
            source_keys.append(c.conversion_id)

    return ProfitResult(
        date=s.date, platform=s.platform, campaign_id=s.campaign_id, ad_id=s.ad_id,
        offer_id=s.offer_id, geo=s.geo, spend=grain["spend"],
        reconciled_conversions=reconciled_conversions,
        reconciled_revenue=reconciled_revenue,
        platform_reported_revenue=grain["platform_reported_revenue"],
        revenue_status=revenue_status, source_keys=source_keys, attribution=attribution,
    )


def _build_unattributed(conversions: list[ConversionRecord]) -> list[ProfitResult]:
    """Group unattributed conversions by (offer_id, geo, date) into ProfitResults with no spend
    grain (spend 0, empty platform/campaign/ad), attribution='unattributed'. Same status-aware
    aggregation so a reversed orphan nets correctly and conservation holds."""
    groups: dict[tuple, list[ConversionRecord]] = {}
    for c in conversions:
        groups.setdefault((c.offer_id, c.geo, c.date), []).append(c)
    results: list[ProfitResult] = []
    for (offer_id, geo, d), convs in groups.items():
        approved = [c for c in convs if c.status == "approved"]
        reversed_ = [c for c in convs if c.status == "reversed"]
        has_pending = any(c.status == "pending" for c in convs)
        reconciled_revenue = (sum((c.revenue for c in approved), Decimal("0"))
                              - sum((c.revenue for c in reversed_), Decimal("0")))
        reconciled_conversions = Decimal(max(0, len(approved) - len(reversed_)))
        if reversed_:
            revenue_status = "reversed"
        elif has_pending:
            revenue_status = "provisional"
        else:
            revenue_status = "confirmed"
        source_keys: list[str] = []
        for c in approved + reversed_:
            if c.conversion_id not in source_keys:
                source_keys.append(c.conversion_id)
        results.append(ProfitResult(
            date=d, platform="", campaign_id="", ad_id="", offer_id=offer_id, geo=geo,
            spend=Decimal("0"), reconciled_conversions=reconciled_conversions,
            reconciled_revenue=reconciled_revenue, platform_reported_revenue=None,
            revenue_status=revenue_status, source_keys=source_keys, attribution="unattributed",
        ))
    return results


def reconcile(spend_records: list[SpendRecord],
              conversions: list[ConversionRecord]) -> list[ProfitResult]:
    """Join spend to revenue: token primary, then (offer,geo,date) fallback (flagged), with
    ambiguous/no-match revenue surfaced as unattributed. Aggregate to the grain under the status
    contract. reconciled_revenue is the real affiliate payout net of reversals; the platform claim
    is carried for the downstream gap, never into profit. Revenue is conserved: every conversion's
    net contribution lands in exactly one result (a spend grain or an unattributed group)."""
    grains = _aggregate_spend(spend_records)
    deduped = _dedup_conversions(conversions)
    token_matched, unmatched = _assign_conversions_to_grains(grains, deduped)
    fallback_matched, fallback_touched, unattributed = _fallback_assign(grains, unmatched)

    results: list[ProfitResult] = []
    for key, grain in grains.items():
        combined = token_matched[key] + fallback_matched[key]
        attribution = "fallback" if key in fallback_touched else "token"
        results.append(_build_result(grain, combined, attribution))
    results.extend(_build_unattributed(unattributed))
    return results
