"""The report ORM reader - the ONE place ProfitFact.objects is queried for the digest.

Maps persisted ProfitFact rows to pure ProfitResult dataclasses so the view can call the pure
build_report with NO ORM in the view. This is the seam boundary: infrastructure (ORM) on this
side, pure application/domain logic on the other. The mirror of the reconcile command's mappers,
in the read direction.
"""
from __future__ import annotations

from domain.records import ProfitResult
from noon.models import ProfitFact


def read_profit_facts(account) -> list:
    """Read this account's ProfitFacts and map them to pure ProfitResult records. Returns a plain
    list (never a QuerySet). Null platform_reported_revenue is carried through as None (claim-side
    sparsity), attribution and source_keys are preserved (faithful, non-lossy projection)."""
    return [
        ProfitResult(
            date=f.date,
            platform=f.platform,
            campaign_id=f.campaign_id,
            ad_id=f.ad_id,
            offer_id=f.offer_id,
            geo=f.geo,
            spend=f.spend,
            reconciled_conversions=f.reconciled_conversions,
            reconciled_revenue=f.reconciled_revenue,
            platform_reported_revenue=f.platform_reported_revenue,
            revenue_status=f.revenue_status,
            source_keys=f.source_keys,
            attribution=f.attribution,
        )
        for f in ProfitFact.objects.filter(account=account)
    ]
