"""Django admin - DEV/superuser plumbing ONLY. Never the product or operator surface (SPEC 3D).
Bare registration for build-time DB inspection; no crafted ModelAdmin.
"""
from django.contrib import admin

from noon.models import (
    Account,
    ConversionRow,
    IngestRun,
    PipelineRun,
    ProfitFact,
    SpendRow,
)

admin.site.register(Account)
admin.site.register(PipelineRun)
admin.site.register(IngestRun)
admin.site.register(SpendRow)
admin.site.register(ConversionRow)
admin.site.register(ProfitFact)
