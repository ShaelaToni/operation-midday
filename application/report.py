"""The report-builder - the delivery seam. PURE (stdlib + domain.records only, no Django).

build_report takes the plain per-grain ProfitResult records (the ORM reader maps ProfitFacts into
these) and returns a ReportData payload the view/template render directly: the claim-vs-real gap
headline, per-offer profit-ranked money moves (fuel winners / free up drainers), and a
worth-acting-on total. The view never touches ProfitFact.objects - it delegates to a reader that
yields these records, then calls this pure function.

Thin delivery slice: winners/drainers are a simple profit sign-split. The full rules (min-volume
floor, thresholds, refresh/fix, change detection) are Stage 5, layered in through this same builder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from domain.records import Move, ProfitResult


@dataclass
class ReportData:
    """The Noon Report payload - everything the digest renders, at rest, zero clicks."""
    total_claim: Decimal            # sum of platform-claimed revenue (null claims excluded)
    total_real: Decimal             # sum of reconciled real payout
    gap_multiple: Decimal           # total_claim / total_real, guarded (0 when no real revenue)
    moves: list                     # list[Move], profit-ranked: fuel winners first, free_up drainers last
    worth_acting_on: Decimal        # recoverable drainer spend (sum of spend on offers running at a loss)


def build_report(facts: list) -> ReportData:
    """Aggregate per-grain ProfitResults into the Noon Report payload. Pure and total (safe on
    empty input). Winners (profit>0) become fuel moves, drainers (profit<0) become free_up moves,
    ranked by profit descending."""
    # The gap headline: sum claims (excluding nulls) and real revenue across every grain.
    total_claim = sum((f.platform_reported_revenue for f in facts
                       if f.platform_reported_revenue is not None), Decimal("0"))
    total_real = sum((f.reconciled_revenue for f in facts), Decimal("0"))
    gap_multiple = (total_claim / total_real) if total_real > 0 else Decimal("0")

    # Aggregate spend and real revenue per offer (across platform grains).
    by_offer: dict[str, dict[str, Decimal]] = {}
    for f in facts:
        agg = by_offer.setdefault(f.offer_id, {"spend": Decimal("0"), "real": Decimal("0")})
        agg["spend"] += f.spend
        agg["real"] += f.reconciled_revenue

    # Build one move per offer, ranked by profit (real - spend) descending.
    moves = []
    worth_acting_on = Decimal("0")
    ranked = sorted(by_offer.items(), key=lambda kv: kv[1]["real"] - kv[1]["spend"], reverse=True)
    for offer_id, agg in ranked:
        profit = agg["real"] - agg["spend"]
        if profit > 0:
            moves.append(Move(
                offer_id=offer_id, action="fuel", amount=profit,
                reason=f"Earning {profit} profit - your money works here.",
            ))
        elif profit < 0:
            # Drainer: recoverable = its spend (money to free up and redeploy).
            worth_acting_on += agg["spend"]
            moves.append(Move(
                offer_id=offer_id, action="free_up", amount=agg["spend"],
                reason=f"Spending {agg['spend']}, earning {agg['real']} - free up to redeploy.",
            ))
        # profit == 0: break-even - neither fueled nor freed up.

    return ReportData(
        total_claim=total_claim, total_real=total_real, gap_multiple=gap_multiple,
        moves=moves, worth_acting_on=worth_acting_on,
    )
