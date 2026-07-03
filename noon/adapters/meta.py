"""Meta adapter: raw Insights row -> SpendRow kwargs. Flattens the configured conversion
action_type (default 'lead') from the nested actions/action_values lists. spend is already
dollars (NOT divided). Revenue absent -> None (claim-side sparsity), never 0."""
from __future__ import annotations

from decimal import Decimal

from noon.adapters.base import SourceAdapter, register

_CENTS = Decimal("0.01")
# Priority list of acceptable conversion action_types; first match wins.
# Real Meta accounts use variant lead events; default handles the demo's 'lead'.
_DEFAULT_CONVERSION_ACTION_TYPES = ("lead",)


def _find_action_value(items: list[dict], action_types: tuple[str, ...]) -> str | None:
    """Return the 'value' for the first matching action_type in a nested actions list,
    or None if no listed action_type is present."""
    by_type = {a.get("action_type"): a.get("value") for a in items}
    for at in action_types:
        if at in by_type:
            return by_type[at]
    return None


class MetaAdapter(SourceAdapter):
    source = "meta"

    def __init__(self, conversion_action_types: tuple[str, ...] = _DEFAULT_CONVERSION_ACTION_TYPES):
        self.conversion_action_types = conversion_action_types

    def parse_row(self, raw: dict) -> dict:
        campaign_id = raw["campaign_id"]
        adset_id = raw.get("adset_id", "")
        ad_id = raw.get("ad_id", "")
        date = raw["date_start"]
        geo = raw.get("geo", "")
        tracking_token = raw.get("tracking_token", "")
        spend = Decimal(str(raw["spend"])).quantize(_CENTS)  # already dollars - do NOT divide

        conv_str = _find_action_value(raw.get("actions", []), self.conversion_action_types)
        conversions = Decimal(conv_str) if conv_str is not None else Decimal("0")

        rev_str = _find_action_value(raw.get("action_values", []), self.conversion_action_types)
        # Sparsity: no revenue value reported -> None (NOT zero, NOT crash).
        revenue = Decimal(rev_str).quantize(_CENTS) if rev_str is not None else None

        return {
            "source": "meta",
            "date": date,
            "campaign_id": campaign_id,
            "campaign_name": raw.get("campaign_name", ""),
            "ad_id": ad_id,
            "ad_name": raw.get("ad_name", ""),
            "offer_id": raw.get("offer_id", ""),
            "geo": geo,
            "tracking_token": tracking_token,
            "currency": raw.get("account_currency", "USD"),
            "spend": spend,
            "impressions": int(raw.get("impressions", 0)),
            "clicks": int(raw.get("clicks", 0)),
            "platform_reported_conversions": conversions,
            "platform_reported_revenue": revenue,
            "raw": raw,
            "ingest_key": f"meta:{campaign_id}:{adset_id}:{ad_id}:{date}:{geo}:{tracking_token}",
        }


register(MetaAdapter())
