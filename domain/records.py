"""Pure domain records. No Django, no framework imports - standard library only.
These plain dataclasses are what the reconciliation, metrics, and rules logic operate on.
The composition root (a Django management command) maps ORM rows to and from these."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class SpendRecord:
    date: date
    platform: str
    campaign_id: str
    campaign_name: str
    ad_id: str
    ad_name: str
    offer_id: str
    geo: str
    tracking_token: str
    spend: Decimal
    impressions: int
    clicks: int
    platform_reported_conversions: Decimal
    platform_reported_revenue: Decimal | None


@dataclass
class ConversionRecord:
    conversion_id: str
    date: date
    offer_id: str
    geo: str
    tracking_token: str
    revenue: Decimal
    status: str


@dataclass
class ProfitResult:
    date: date
    platform: str
    campaign_id: str
    ad_id: str
    offer_id: str
    geo: str
    spend: Decimal
    reconciled_conversions: Decimal
    reconciled_revenue: Decimal
    platform_reported_revenue: Decimal | None
    revenue_status: str
    source_keys: list[str] = field(default_factory=list)
    attribution: str = "token"  # join quality: token | fallback | unattributed (distinct from revenue_status)


@dataclass
class Verdict:
    offer_id: str
    metric_key: str
    status: str
    reason: str
    window: str
    value: Decimal | None
    delta: Decimal | None


@dataclass
class Move:
    offer_id: str
    action: str
    amount: Decimal
    reason: str
