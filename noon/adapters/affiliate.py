"""Affiliate adapter: raw postback row -> ConversionRow kwargs (REVENUE side, NOT SpendRow).
transaction_id -> conversion_id (idempotency key). sub_id/click_id -> tracking_token (join key).
payout -> revenue (real money, always present - trust over platform claims). status is provisional
(pending|approved|rejected|reversed); reconciliation respects it. date sliced from the timestamp."""
from __future__ import annotations

from decimal import Decimal

from noon.adapters.base import SourceAdapter, register

_CENTS = Decimal("0.01")


class AffiliateAdapter(SourceAdapter):
    source = "affiliate"

    def parse_row(self, raw: dict) -> dict:
        # sub_id is the primary join token; click_id is the alternate name.
        tracking_token = raw.get("sub_id") or raw.get("click_id") or ""
        # transaction_id is the primary id; conversion_id is the alternate name.
        conversion_id = raw.get("transaction_id") or raw.get("conversion_id") or ""
        timestamp = str(raw.get("timestamp", ""))
        date = timestamp[:10]  # ISO-8601 always leads with YYYY-MM-DD; robust to Z/offset
        payout = raw.get("payout") or raw.get("amount")
        return {
            "source": "affiliate",
            "conversion_id": conversion_id,
            "date": date,
            "offer_id": raw.get("offer_id", ""),
            "geo": raw.get("geo", ""),
            "tracking_token": tracking_token,
            "revenue": Decimal(str(payout)).quantize(_CENTS) if payout is not None else Decimal("0"),
            "status": raw.get("status", "pending"),
            "raw": raw,
        }


register(AffiliateAdapter())
