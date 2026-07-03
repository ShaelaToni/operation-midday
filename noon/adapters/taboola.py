"""Taboola adapter: raw Backstage row -> SpendRow kwargs. Maps Taboola's renamed fields
(spent->spend NOT divided, cpa_actions_num->conversions, conversions_value->revenue,
item->ad_id, country->geo). url (landing page) + timezone preserved in raw (no columns).
Date maps through: Taboola EST/EDT == our US/Eastern, no shift needed in V1."""
from __future__ import annotations

from decimal import Decimal

from noon.adapters.base import SourceAdapter, register

_CENTS = Decimal("0.01")


class TaboolaAdapter(SourceAdapter):
    source = "taboola"

    def parse_row(self, raw: dict) -> dict:
        campaign_id = raw["campaign_id"]
        item = raw.get("item", "")
        date = raw["date"]
        geo = raw.get("country", "")
        tracking_token = raw.get("tracking_token", "")
        spend = Decimal(str(raw["spent"])).quantize(_CENTS)  # 'spent', already dollars - NOT divided
        conv_value = raw.get("conversions_value")
        return {
            "source": "taboola",
            "date": date,
            "campaign_id": campaign_id,
            "campaign_name": raw.get("campaign_name", ""),
            "ad_id": item,
            "ad_name": raw.get("item_name", ""),
            "offer_id": raw.get("offer_id", ""),
            "geo": geo,
            "tracking_token": tracking_token,
            "currency": raw.get("currency", "USD"),
            "spend": spend,
            "impressions": int(raw.get("impressions", 0)),
            "clicks": int(raw.get("clicks", 0)),
            "platform_reported_conversions": Decimal(str(raw.get("cpa_actions_num", 0))),
            "platform_reported_revenue": (Decimal(str(conv_value)).quantize(_CENTS) if conv_value is not None else None),
            "raw": raw,
            "ingest_key": f"taboola:{campaign_id}:{item}:{date}:{geo}:{tracking_token}",
        }


register(TaboolaAdapter())
