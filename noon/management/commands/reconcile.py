"""reconcile - the composition root for reconciliation.

Reads all SpendRow / ConversionRow for the account, maps them to the pure domain dataclasses
(the ONLY rename: SpendRecord.platform <- SpendRow.source), calls the pure reconcile() core, and
persists the resulting ProfitResults as ProfitFact rows - idempotently, via update_or_create on a
deterministic grain_key. Wrapped in a PipelineRun for observability.

The domain stays pure: this command does all ORM I/O and constructs the persistence-only fields
(grain_key, ruleset_version, computed_at); the reconciler never touches Django.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from domain.records import SpendRecord, ConversionRecord
from domain.reconciliation import reconcile
from noon.models import Account, PipelineRun, ProfitFact, SpendRow, ConversionRow

RULESET_VERSION = "v1"


def _grain_key(r) -> str:
    """Deterministic natural key from the ProfitResult's grain dimensions. Real grains carry a
    non-empty platform; unattributed rows (empty platform) get an explicit, collision-safe prefix
    so they never clash with a real grain."""
    if r.attribution == "unattributed":
        return f"unattributed|{r.date.isoformat()}|{r.offer_id}|{r.geo}"
    return "|".join([
        r.date.isoformat(), r.platform, r.campaign_id, r.ad_id, r.offer_id, r.geo,
    ])


def _to_spend_record(row: SpendRow) -> SpendRecord:
    return SpendRecord(
        date=row.date, platform=row.source, campaign_id=row.campaign_id,
        campaign_name=row.campaign_name, ad_id=row.ad_id, ad_name=row.ad_name,
        offer_id=row.offer_id, geo=row.geo, tracking_token=row.tracking_token,
        spend=row.spend, impressions=row.impressions, clicks=row.clicks,
        platform_reported_conversions=row.platform_reported_conversions,
        platform_reported_revenue=row.platform_reported_revenue,
    )


def _to_conversion_record(row: ConversionRow) -> ConversionRecord:
    return ConversionRecord(
        conversion_id=row.conversion_id, date=row.date, offer_id=row.offer_id,
        geo=row.geo, tracking_token=row.tracking_token, revenue=row.revenue, status=row.status,
    )


class Command(BaseCommand):
    help = "Reconcile all spend + conversion rows for the account into ProfitFacts (idempotent)."

    def handle(self, *args, **options):
        account, _ = Account.objects.get_or_create(
            name="Demo Account",
            defaults={"timezone": "US/Eastern", "currency": "USD"},
        )
        pipeline = PipelineRun.objects.create(
            account=account, started_at=timezone.now(), status="running", error="",
        )
        try:
            spend_records = [_to_spend_record(r)
                             for r in SpendRow.objects.filter(account=account)]
            conversions = [_to_conversion_record(r)
                           for r in ConversionRow.objects.filter(account=account)]

            results = reconcile(spend_records, conversions)

            written = 0
            for r in results:
                ProfitFact.objects.update_or_create(
                    grain_key=_grain_key(r),
                    defaults={
                        "account": account,
                        "date": r.date,
                        "platform": r.platform,
                        "campaign_id": r.campaign_id,
                        "ad_id": r.ad_id,
                        "offer_id": r.offer_id,
                        "geo": r.geo,
                        "spend": r.spend,
                        "reconciled_conversions": r.reconciled_conversions,
                        "reconciled_revenue": r.reconciled_revenue,
                        "platform_reported_revenue": r.platform_reported_revenue,
                        "revenue_status": r.revenue_status,
                        "attribution": r.attribution,
                        "ruleset_version": RULESET_VERSION,
                        "source_keys": r.source_keys,
                    },
                )
                written += 1

            pipeline.status = "success"
            pipeline.finished_at = timezone.now()
            pipeline.save()
            self.stdout.write(self.style.SUCCESS(
                f"reconcile done: {written} profit facts from {len(spend_records)} spend + "
                f"{len(conversions)} conversion rows."
            ))
        except Exception as exc:
            pipeline.status = "failed"
            pipeline.error = repr(exc)
            pipeline.finished_at = timezone.now()
            pipeline.save()
            raise
