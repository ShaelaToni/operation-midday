"""seed_demo - the composition root that populates the demo dataset.

Runs the story planter (the four authored cases) plus bulk random filler through the REAL source
adapters, and persists SpendRow / ConversionRow under a PipelineRun + per-source IngestRun. This is
the ONLY place that does ORM writes for ingestion; the domain/adapters stay pure. Idempotent: rows
dedup on their natural keys (SpendRow.ingest_key, ConversionRow.conversion_id), so re-running is safe.

It loads RAW inputs only - it never writes a profit number or verdict. Reconciliation (Stage 3) is a
separate command. Simulate inputs, not outputs.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from noon.adapters.base import get_adapter, SPEND_SOURCES, REVENUE_SOURCES
from noon.fixtures.google import generate_google_rows
from noon.fixtures.meta import generate_meta_rows
from noon.fixtures.taboola import generate_taboola_rows
from noon.fixtures.tiktok import generate_tiktok_rows
from noon.fixtures.affiliate import generate_affiliate_rows
from noon.fixtures.story_planter import build_story_rows
from noon.models import Account, PipelineRun, IngestRun, SpendRow, ConversionRow

# Composition root knows the concrete generators (that is its job).
_GENERATORS = {
    "google": generate_google_rows,
    "meta": generate_meta_rows,
    "taboola": generate_taboola_rows,
    "tiktok": generate_tiktok_rows,
    "affiliate": generate_affiliate_rows,
}


class Command(BaseCommand):
    help = "Seed the demo dataset: four story cases + 12 months of filler, through the real adapters."

    def add_arguments(self, parser):
        parser.add_argument("--filler", type=int, default=200,
                            help="Rows of random filler per source (default 200).")
        parser.add_argument("--seed", type=int, default=0,
                            help="Base RNG seed for deterministic filler (default 0).")

    def handle(self, *args, **options):
        filler_n = options["filler"]
        base_seed = options["seed"]
        now = timezone.now()

        account, _ = Account.objects.get_or_create(
            name="Demo Account",
            defaults={"timezone": "US/Eastern", "currency": "USD"},
        )
        pipeline = PipelineRun.objects.create(
            account=account, started_at=now, status="running", error="",
        )

        story = build_story_rows()
        totals = {"spend_rows": 0, "conversion_rows": 0}

        # Collect story rows per source so they seed under that source's IngestRun.
        story_spend_by_source: dict[str, list[dict]] = {s: [] for s in SPEND_SOURCES}
        story_affiliate_raws: list[dict] = []
        for case in story.values():
            for src, raw in case["spend"]:
                story_spend_by_source[src].append(raw)
            story_affiliate_raws.extend(case["affiliate"])

        exceptions = 0

        # --- Spend sources ---
        for src in SPEND_SOURCES:
            ingest = IngestRun.objects.create(
                account=account, pipeline_run=pipeline, source=src,
                started_at=timezone.now(), status="running", error="",
            )
            count = 0
            try:
                raws = list(story_spend_by_source[src])
                raws += _GENERATORS[src](n=filler_n, seed=base_seed)
                for raw in raws:
                    kwargs = get_adapter(src).parse_row(raw)
                    kwargs["account"] = account
                    kwargs["ingest_run"] = ingest
                    _, created = SpendRow.objects.get_or_create(
                        ingest_key=kwargs["ingest_key"], defaults=kwargs,
                    )
                    if created:
                        count += 1
                ingest.rows_in = count
                ingest.status = "success"
            except Exception as exc:  # per-source isolation: one failure does not kill the run
                exceptions += 1
                ingest.status = "failed"
                ingest.error = repr(exc)
            ingest.finished_at = timezone.now()
            ingest.save()
            totals["spend_rows"] += count

        # --- Revenue source (affiliate -> ConversionRow) ---
        for src in REVENUE_SOURCES:
            ingest = IngestRun.objects.create(
                account=account, pipeline_run=pipeline, source=src,
                started_at=timezone.now(), status="running", error="",
            )
            count = 0
            try:
                raws = list(story_affiliate_raws)
                raws += _GENERATORS[src](n=filler_n, seed=base_seed)
                for raw in raws:
                    kwargs = get_adapter(src).parse_row(raw)
                    kwargs["account"] = account
                    kwargs["ingest_run"] = ingest
                    _, created = ConversionRow.objects.get_or_create(
                        conversion_id=kwargs["conversion_id"], defaults=kwargs,
                    )
                    if created:
                        count += 1
                ingest.rows_in = count
                ingest.status = "success"
            except Exception as exc:
                exceptions += 1
                ingest.status = "failed"
                ingest.error = repr(exc)
            ingest.finished_at = timezone.now()
            ingest.save()
            totals["conversion_rows"] += count

        pipeline.status = "success" if exceptions == 0 else "partial"
        pipeline.exceptions_count = exceptions
        pipeline.finished_at = timezone.now()
        pipeline.save()

        self.stdout.write(self.style.SUCCESS(
            f"seed_demo done: {totals['spend_rows']} spend rows, "
            f"{totals['conversion_rows']} conversion rows, {exceptions} source failures."
        ))
