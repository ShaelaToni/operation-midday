"""TikTok ingestion: generator emits real /report/integrated/get/ shape - each row is a nested
{dimensions, metrics} split. Adapter reads by NAME (order is unstable) and flattens to SpendRow
kwargs. spend is dollars (not micros). conversion value often absent -> revenue None (sparsity).
Written test-first (red) before the generator/adapter exist.
"""
from decimal import Decimal

import pytest


def test_generator_emits_nested_dimensions_metrics_shape():
    from noon.fixtures.tiktok import generate_tiktok_rows

    rows = generate_tiktok_rows(n=5, seed=42)
    assert len(rows) == 5
    r = rows[0]
    # Each row is the nested split.
    assert "dimensions" in r and "metrics" in r
    assert isinstance(r["dimensions"], dict) and isinstance(r["metrics"], dict)
    for dkey in ("stat_time_day", "campaign_id", "adgroup_id", "ad_id", "country_code"):
        assert dkey in r["dimensions"], f"missing dimension: {dkey}"
    for mkey in ("spend", "impressions", "clicks", "conversion",
                 "campaign_name", "adgroup_name", "ad_name"):
        assert mkey in r["metrics"], f"missing metric: {mkey}"


def test_generator_is_deterministic_with_seed():
    from noon.fixtures.tiktok import generate_tiktok_rows
    assert generate_tiktok_rows(n=3, seed=7) == generate_tiktok_rows(n=3, seed=7)


def test_adapter_reads_nested_split_by_name():
    from noon.adapters.tiktok import TikTokAdapter

    raw = {
        "dimensions": {
            "stat_time_day": "2026-01-15",
            "campaign_id": "TT_C1",
            "adgroup_id": "AG1",
            "ad_id": "TT_AD1",
            "country_code": "US",
        },
        "metrics": {
            "spend": "175.25",
            "impressions": "40000",
            "clicks": "220",
            "conversion": "14",
            "conversion_value": "420.00",
            "campaign_name": "TikTok Campaign",
            "adgroup_name": "Adgroup One",
            "ad_name": "TikTok Ad One",
        },
        "tracking_token": "tok_tt_1",
        "offer_id": "OFFER1",
    }
    kwargs = TikTokAdapter().parse_row(raw)
    # spend is dollars, NOT micros.
    assert kwargs["spend"] == Decimal("175.25")
    assert isinstance(kwargs["spend"], Decimal)
    # Read by name from the nested split.
    assert kwargs["source"] == "tiktok"
    assert kwargs["campaign_id"] == "TT_C1"
    assert kwargs["ad_id"] == "TT_AD1"
    assert kwargs["campaign_name"] == "TikTok Campaign"
    assert kwargs["ad_name"] == "TikTok Ad One"
    assert kwargs["date"] == "2026-01-15"        # from stat_time_day
    assert kwargs["geo"] == "US"                 # from country_code
    assert kwargs["clicks"] == 220
    assert kwargs["platform_reported_conversions"] == Decimal("14")
    assert kwargs["platform_reported_revenue"] == Decimal("420.00")
    assert kwargs["tracking_token"] == "tok_tt_1"
    # adgroup lives in raw + ingest_key (no dedicated column).
    assert kwargs["raw"] == raw
    assert kwargs["ingest_key"] == "tiktok:TT_C1:AG1:TT_AD1:2026-01-15:US:tok_tt_1"


def test_adapter_revenue_absent_is_none():
    """TikTok conversion value is often absent for lead-gen -> revenue None (not zero)."""
    from noon.adapters.tiktok import TikTokAdapter

    raw = {
        "dimensions": {
            "stat_time_day": "2026-01-16", "campaign_id": "TT_C2", "adgroup_id": "AG2",
            "ad_id": "TT_AD2", "country_code": "CA",
        },
        "metrics": {
            "spend": "88.00", "impressions": "12000", "clicks": "90", "conversion": "6",
            "campaign_name": "No-Rev TT", "adgroup_name": "AG Two", "ad_name": "Ad Two",
            # no conversion_value key - the sparsity case
        },
        "tracking_token": "tok_tt_2", "offer_id": "OFFER2",
    }
    kwargs = TikTokAdapter().parse_row(raw)
    assert kwargs["platform_reported_conversions"] == Decimal("6")
    assert kwargs["platform_reported_revenue"] is None


def test_adapter_registered_in_registry():
    import noon.adapters  # noqa: F401
    from noon.adapters.base import get_adapter
    assert get_adapter("tiktok").source == "tiktok"
