"""Noon data-spine models (Stage 1). Infrastructure layer - maps to/from the pure
domain dataclasses in domain/records.py via the run_pipeline composition root.
Money and conversion counts are DecimalField, never Float. Every FK sets on_delete
and related_name; every model sets an explicit db_table.
"""
from django.db import models


class Account(models.Model):
    """Tenant boundary (single-tenant in V1; the id is reserved for V3 isolation)."""
    name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=64, default="US/Eastern")
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts"

    def __str__(self):
        return self.name


class PipelineRun(models.Model):
    """Observability: spans a whole pipeline run (ingest -> reconcile -> metrics -> rules -> snapshots)."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="pipeline_runs")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, default="running")  # running|success|partial|failed
    stages = models.JSONField(default=dict)  # per-stage status/counts/durations
    exceptions_count = models.IntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "pipeline_runs"

    def __str__(self):
        return f"PipelineRun {self.pk} ({self.status})"


class IngestRun(models.Model):
    """Per-source ingest, nested under a PipelineRun. Observability + source health."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="ingest_runs")
    pipeline_run = models.ForeignKey(
        PipelineRun, on_delete=models.CASCADE, related_name="ingest_runs", null=True, blank=True
    )
    source = models.CharField(max_length=16)  # google|meta|taboola|tiktok|affiliate
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    rows_in = models.IntegerField(default=0)
    status = models.CharField(max_length=16, default="running")  # running|success|partial|failed
    error = models.TextField(blank=True)

    class Meta:
        db_table = "ingest_runs"

    def __str__(self):
        return f"IngestRun {self.source} ({self.status})"


class SpendRow(models.Model):
    """Raw spend fact from an ad platform. Enters via an adapter; never hand-written in logic."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="spend_rows")
    ingest_run = models.ForeignKey(IngestRun, on_delete=models.CASCADE, related_name="spend_rows")
    source = models.CharField(max_length=16)
    date = models.DateField()
    campaign_id = models.CharField(max_length=255)
    campaign_name = models.CharField(max_length=255)
    ad_id = models.CharField(max_length=255, blank=True)
    ad_name = models.CharField(max_length=255, blank=True)
    offer_id = models.CharField(max_length=255, blank=True)
    geo = models.CharField(max_length=2)
    tracking_token = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    spend = models.DecimalField(max_digits=14, decimal_places=2)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    platform_reported_conversions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    platform_reported_revenue = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    raw = models.JSONField(default=dict)
    ingest_key = models.CharField(max_length=255, unique=True)  # natural key -> idempotency

    class Meta:
        db_table = "spend_rows"

    def __str__(self):
        return f"SpendRow {self.source} {self.date} {self.campaign_id}"


class ConversionRow(models.Model):
    """Raw conversion/postback fact from the revenue side. Revenue is PROVISIONAL via status."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="conversion_rows")
    ingest_run = models.ForeignKey(IngestRun, on_delete=models.CASCADE, related_name="conversion_rows")
    source = models.CharField(max_length=16)
    conversion_id = models.CharField(max_length=255, unique=True)  # idempotency key
    date = models.DateField()
    offer_id = models.CharField(max_length=255)
    geo = models.CharField(max_length=2)
    tracking_token = models.CharField(max_length=255, blank=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=16)  # pending|approved|rejected|reversed
    raw = models.JSONField(default=dict)

    class Meta:
        db_table = "conversion_rows"

    def __str__(self):
        return f"ConversionRow {self.conversion_id} ({self.status})"


class ProfitFact(models.Model):
    """DERIVED reconciled fact - never hand-written. Stamped with ruleset_version + source_keys (lineage)."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="profit_facts")
    date = models.DateField()
    platform = models.CharField(max_length=16)
    campaign_id = models.CharField(max_length=255)
    ad_id = models.CharField(max_length=255, blank=True)
    offer_id = models.CharField(max_length=255, blank=True)
    geo = models.CharField(max_length=2)
    spend = models.DecimalField(max_digits=14, decimal_places=2)
    reconciled_conversions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reconciled_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    platform_reported_revenue = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    revenue_status = models.CharField(max_length=16)  # provisional|confirmed|reversed
    ruleset_version = models.CharField(max_length=32)
    source_keys = models.JSONField(default=list)  # lineage: contributing raw-row keys
    computed_at = models.DateTimeField(auto_now=True)
    grain_key = models.CharField(max_length=255, unique=True)  # date|platform|campaign|ad|offer|geo

    class Meta:
        db_table = "profit_facts"

    def __str__(self):
        return f"ProfitFact {self.grain_key}"
