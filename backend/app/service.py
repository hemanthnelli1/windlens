from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from .analytics import clean_actuals, clean_forecasts, matched_pairs, metrics, rows, select_forecast
from .cache import MemoryCache
from .config import Settings
from .elexon_client import ElexonClient
from .timeutils import default_day_ahead_cutoff, iso_utc, january_2026_bounds, uk_day_bounds


class WindService:
    def __init__(self, client: ElexonClient, settings: Settings):
        self.client = client
        self.settings = settings
        self.cache = MemoryCache(settings.cache_ttl_seconds)
        self.last_retrieval: datetime | None = None

    @staticmethod
    def validate_january(day: date) -> None:
        if day.year != 2026 or day.month != 1:
            raise ValueError("Only January 2026 delivery dates are in scope")

    async def _actual_records(self, start: date, end: date) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        cursor = start
        while cursor <= end:
            key = f"actuals:{cursor.isoformat()}"
            result.extend(await self.cache.get_or_set(key, lambda day=cursor: self.client.actuals_for_day(day)))
            cursor += timedelta(days=1)
        self.last_retrieval = datetime.now().astimezone()
        return result

    async def _forecast_records(self, start: date, end: date) -> list[dict[str, Any]]:
        # The source publishes forecasts up to about two days ahead. Include two
        # prior publication days so early delivery periods are eligible.
        result: list[dict[str, Any]] = []
        cursor = start - timedelta(days=2)
        final = end
        while cursor <= final:
            key = f"forecasts-published:{cursor.isoformat()}"
            result.extend(await self.cache.get_or_set(key, lambda day=cursor: self.client.forecasts_published_on(day)))
            cursor += timedelta(days=1)
        self.last_retrieval = datetime.now().astimezone()
        return result

    async def frames(self, start: date, end: date) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
        actual_records, forecast_records = await self._actual_records(start, end), await self._forecast_records(start, end)
        actuals, actual_duplicates = clean_actuals(actual_records)
        forecasts, forecast_duplicates = clean_forecasts(forecast_records)
        lower, upper = uk_day_bounds(start)[0], uk_day_bounds(end + timedelta(days=1))[0]
        if not actuals.empty:
            actuals = actuals.loc[actuals.start_time.between(pd.Timestamp(lower), pd.Timestamp(upper), inclusive="left")]
        if not forecasts.empty:
            forecasts = forecasts.loc[forecasts.start_time.between(pd.Timestamp(lower), pd.Timestamp(upper), inclusive="left")]
        return actuals, forecasts, {"actual_raw_records": len(actual_records), "forecast_raw_records": len(forecast_records), "actual_duplicates": actual_duplicates, "forecast_duplicates": forecast_duplicates}

    async def analysis(self, day: date, cutoff: datetime | None = None, vintage: datetime | None = None) -> dict[str, Any]:
        self.validate_january(day)
        actuals, forecasts, quality = await self.frames(day, day)
        effective_cutoff = cutoff or default_day_ahead_cutoff(day, self.settings.default_cutoff_hour_local)
        selected = select_forecast(forecasts, cutoff=None if vintage else effective_cutoff, vintage=vintage)
        pairs = matched_pairs(actuals, selected)
        return {"actuals": actuals, "forecasts": forecasts, "selected": selected, "pairs": pairs, "quality": quality, "cutoff": effective_cutoff, "metrics": metrics(pairs)}

    async def overview(self, day: date, cutoff: datetime | None = None, vintage: datetime | None = None) -> dict[str, Any]:
        data = await self.analysis(day, cutoff, vintage)
        pairs = data["pairs"]
        display = data["actuals"][["start_time", "generation"]].rename(columns={"generation": "actual_mw"}).merge(
            data["selected"].rename(columns={"generation": "forecast_mw"})[["start_time", "publish_time", "forecast_mw"]],
            on="start_time",
            how="outer",
        ).sort_values("start_time")
        period_rows = []
        for record in display.itertuples(index=False):
            matched = pd.notna(record.actual_mw) and pd.notna(record.forecast_mw)
            error = float(record.forecast_mw - record.actual_mw) if matched else None
            period_rows.append({
                "start_time": iso_utc(record.start_time),
                "actual_mw": float(record.actual_mw) if pd.notna(record.actual_mw) else None,
                "forecast_mw": float(record.forecast_mw) if pd.notna(record.forecast_mw) else None,
                "publish_time": iso_utc(record.publish_time) if pd.notna(record.publish_time) else None,
                "error_mw": error,
                "absolute_error_mw": abs(error) if error is not None else None,
                "wind_shortfall_mw": max(-error, 0) if error is not None else None,
            })
        return {"delivery_date": day.isoformat(), "selection_mode": "exact_vintage" if vintage else "latest_available_at_cutoff", "publication_cutoff": iso_utc(data["cutoff"]), "selected_vintage": iso_utc(vintage) if vintage else None, "metrics": data["metrics"], "periods": period_rows, "quality": data["quality"]}

    async def vintages(self, day: date, cutoff: datetime | None = None) -> dict[str, Any]:
        data = await self.analysis(day, cutoff)
        limit = pd.Timestamp(data["cutoff"])
        forecasts = data["forecasts"].loc[data["forecasts"].publish_time.le(limit)] if not data["forecasts"].empty else data["forecasts"]
        summaries = []
        if not forecasts.empty:
            for publish_time, vintage_frame in forecasts.groupby("publish_time", sort=False):
                pairs = matched_pairs(data["actuals"], vintage_frame)
                summary = metrics(pairs)
                summary["publish_time"] = iso_utc(publish_time)
                summary["available_at_cutoff"] = True
                summaries.append(summary)
        return {"delivery_date": day.isoformat(), "decision_cutoff": iso_utc(data["cutoff"]), "vintages": summaries}

    async def data_quality(self, day: date) -> dict[str, Any]:
        data = await self.analysis(day)
        expected = 48
        actual_count = len(data["actuals"])
        selected_count = len(data["selected"])
        return {"delivery_date": day.isoformat(), "requested_range": f"{day.isoformat()} Europe/London delivery day", "retrieved_at": self.last_retrieval.isoformat() if self.last_retrieval else None, "actual_records": actual_count, "selected_forecast_records": selected_count, "missing_actual_observations": max(0, expected - actual_count), "missing_selected_forecast_observations": max(0, expected - selected_count), "matched_sample_count": data["metrics"]["matched_samples"], **data["quality"], "deduplication_policy": "Actuals: latest publishTime per delivery startTime. Forecasts: final stable row per (startTime, publishTime); distinct vintages are retained."}

    async def metadata(self) -> dict[str, Any]:
        start, end = january_2026_bounds()
        return {"product": "WindLens — UK Wind Forecast Intelligence", "delivery_scope": {"start": iso_utc(start), "end_exclusive": iso_utc(end)}, "timezone_strategy": "All API timestamps are parsed and compared as UTC instants; the interface formats delivery timestamps in Europe/London.", "default_cutoff_assumption": f"Previous UK calendar day at {self.settings.default_cutoff_hour_local:02d}:00 Europe/London; configurable and not presented as an official market rule.", "sources": [{"name": "Elexon FUELHH", "url": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH"}, {"name": "Elexon WINDFOR", "url": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR"}]}
