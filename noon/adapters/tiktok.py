"""TikTok adapter: raw {dimensions, metrics} row -> SpendRow kwargs. Reads by NAME from both
nested sub-dicts (field order is unstable). spend is dollars (NOT divided). conversion_value
often absent -> revenue None (claim-side sparsity). adgroup_id -> raw + ingest_key (no column)."""
from __future__ import annotations

from decimal import Decimal

from noon.adapters.base import SourceAdapter, register

_CENTS = Decimal("0.01")


class TikTokAdapter(SourceAdapter):
    source = "tiktok"

    def parse_row(self, raw: dict) -> dict:
        dims = raw.get("dimensions", {})
        metrics = raw.get("metrics", {})
        campaign_id = dims.get("campaign_id", "")
        adgroup_id = dims.get("adgroup_id", "")
        ad_id = dims.get("ad_id", "")
        date = dims.get("stat_time_day", "")
        geo = dims.get("country_code", "")
        tracking_token = raw.get("tracking_token", "")
        spend = Decimal(str(metrics.get("spend", "0"))).quantize(_CENTS)  # dollars - NOT divided
        conv_value = metrics.get("conversion_value")  # missing key -> None (sparsity)
        return {
            "source": "tiktok",
            "date": date,
            "campaign_id": campaign_id,
            "campaign_name": metrics.get("campaign_name", ""),
            "ad_id": ad_id,
            "ad_name": metrics.get("ad_name", ""),
            "offer_id": raw.get("offer_id", ""),
            "geo": geo,
            "tracking_token": tracking_token,
            "currency": "USD",
            "spend": spend,
            "impressions": int(metrics.get("impressions", 0)),
            "clicks": int(metrics.get("clicks", 0)),
            "platform_reported_conversions": Decimal(str(metrics.get("conversion", 0))),
            "platform_reported_revenue": (Decimal(str(conv_value)).quantize(_CENTS) if conv_value is not None else None),
            "raw": raw,
            "ingest_key": f"tiktok:{campaign_id}:{adgroup_id}:{ad_id}:{date}:{geo}:{tracking_token}",
        }


register(TikTokAdapter())
