from datetime import datetime
import asyncio

import pandas as pd
import pytest

from app.analytics import clean_actuals, clean_forecasts, matched_pairs, metrics, select_forecast
from app.cache import MemoryCache
from app.service import WindService
from app.timeutils import UK_TZ, default_day_ahead_cutoff, uk_day_bounds


def test_filters_wind_and_deduplicates_actuals():
    records = [
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:30:00Z", "fuelType": "WIND", "generation": 100},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T01:00:00Z", "fuelType": "WIND", "generation": 110},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:30:00Z", "fuelType": "CCGT", "generation": 999},
    ]
    frame, duplicates = clean_actuals(records)
    assert len(frame) == 1 and frame.iloc[0].generation == 110 and duplicates == 2


def test_forecast_vintages_are_preserved_and_cutoff_selects_latest():
    records = [
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-30T12:00:00Z", "generation": 100},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T12:00:00Z", "generation": 120},
    ]
    forecasts, _ = clean_forecasts(records)
    selected = select_forecast(forecasts, cutoff=datetime.fromisoformat("2025-12-31T12:00:00+00:00"))
    assert len(forecasts) == 2 and selected.iloc[0].generation == 120


def test_metrics_and_zero_actual_wape():
    actuals = pd.DataFrame({"start_time": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"]), "generation": [0, 100], "publish_time": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"])})
    forecasts = pd.DataFrame({"start_time": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"]), "generation": [10, 80], "publish_time": pd.to_datetime(["2025-12-31T12:00:00Z", "2025-12-31T12:00:00Z"])})
    result = metrics(matched_pairs(actuals, forecasts))
    assert result["mae_mw"] == 15 and result["rmse_mw"] == pytest.approx(15.81, abs=0.01) and result["bias_mw"] == -5 and result["wape_percent"] == 30
    zero = actuals.assign(generation=0)
    assert metrics(matched_pairs(zero, forecasts))["wape_percent"] is None


def test_january_boundary_and_uk_daylight_saving():
    WindService.validate_january(__import__("datetime").date(2026, 1, 31))
    with pytest.raises(ValueError):
        WindService.validate_january(__import__("datetime").date(2026, 2, 1))
    start, end = uk_day_bounds(__import__("datetime").date(2026, 3, 29))
    assert (end - start).total_seconds() == 23 * 3600


def test_default_cutoff_is_explicit_uk_time():
    cutoff = default_day_ahead_cutoff(__import__("datetime").date(2026, 1, 2), 12)
    assert cutoff.isoformat() == "2026-01-01T12:00:00+00:00"


def test_cache_shares_one_inflight_request():
    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return {"source": "BMRS"}

    async def exercise():
        cache = MemoryCache(60)
        return await asyncio.gather(cache.get_or_set("FUELHH:2026-01-01", factory), cache.get_or_set("FUELHH:2026-01-01", factory))

    result = asyncio.run(exercise())
    assert result == [{"source": "BMRS"}, {"source": "BMRS"}] and calls == 1
