"""Google Ads adapter: raw GAQL row -> SpendRow kwargs. Divides cost_micros to Decimal dollars."""
from __future__ import annotations

from decimal import Decimal

from noon.adapters.base import SourceAdapter, register

_MICROS = Decimal("1000000")
_CENTS = Decimal("0.01")


class GoogleAdapter(SourceAdapter):
    source = "google"

    def parse_row(self, raw: dict) -> dict:
        cost_micros = raw["metrics.cost_micros"]
        spend = (Decimal(cost_micros) / _MICROS).quantize(_CENTS)
        campaign_id = raw["campaign.id"]
        ad_id = raw.get("ad_group_ad.ad.id", "")
        date = raw["segments.date"]
        geo = raw["geographic_view.country"]
        tracking_token = raw.get("tracking_token", "")
        conv_value = raw.get("metrics.conversions_value")
        return {
            "source": "google",
            "date": date,
            "campaign_id": campaign_id,
            "campaign_name": raw.get("campaign.name", ""),
            "ad_id": ad_id,
            "ad_name": raw.get("ad_group_ad.ad.name", ""),
            "offer_id": raw.get("offer_id", ""),
            "geo": geo,
            "tracking_token": tracking_token,
            "currency": "USD",
            "spend": spend,
            "impressions": int(raw.get("metrics.impressions", 0)),
            "clicks": int(raw.get("metrics.clicks", 0)),
            "platform_reported_conversions": Decimal(str(raw.get("metrics.conversions", 0))),
            "platform_reported_revenue": (Decimal(str(conv_value)) if conv_value is not None else None),
            "raw": raw,
            "ingest_key": f"google:{campaign_id}:{ad_id}:{date}:{geo}:{tracking_token}",
        }


register(GoogleAdapter())
