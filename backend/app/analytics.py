from datetime import datetime
from typing import Any
import math

import pandas as pd


REQUIRED_ACTUAL_FIELDS = {"startTime", "generation", "fuelType"}
REQUIRED_FORECAST_FIELDS = {"startTime", "publishTime", "generation"}


def _to_frame(records: list[dict[str, Any]], required: set[str]) -> pd.DataFrame:
    valid = [row for row in records if required.issubset(row) and row.get("generation") is not None]
    if not valid:
        return pd.DataFrame()
    frame = pd.DataFrame(valid)
    frame["start_time"] = pd.to_datetime(frame["startTime"], utc=True, errors="coerce")
    frame["generation"] = pd.to_numeric(frame["generation"], errors="coerce")
    if "publishTime" in frame:
        frame["publish_time"] = pd.to_datetime(frame["publishTime"], utc=True, errors="coerce")
    return frame.dropna(subset=["start_time", "generation"])


def clean_actuals(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, int]:
    frame = _to_frame(records, REQUIRED_ACTUAL_FIELDS)
    if frame.empty:
        return frame, 0
    frame = frame.loc[frame["fuelType"].eq("WIND")].copy()
    duplicate_count = int(frame.duplicated(subset=["start_time"], keep=False).sum())
    # Deterministic policy: for identical wind delivery timestamps, retain the
    # most recently published record. No missing timestamp is fabricated.
    frame = frame.sort_values(["start_time", "publish_time"], kind="stable").drop_duplicates("start_time", keep="last")
    return frame[["start_time", "generation", "publish_time"]].sort_values("start_time"), duplicate_count


def clean_forecasts(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, int]:
    frame = _to_frame(records, REQUIRED_FORECAST_FIELDS)
    if frame.empty:
        return frame, 0
    frame = frame.dropna(subset=["publish_time"])
    duplicate_count = int(frame.duplicated(subset=["start_time", "publish_time"], keep=False).sum())
    # Duplicate rows for one delivery/publication pair are resolved by stable
    # source order, retaining the final record while retaining all vintages.
    frame = frame.sort_values(["start_time", "publish_time"], kind="stable").drop_duplicates(["start_time", "publish_time"], keep="last")
    return frame[["start_time", "publish_time", "generation"]].sort_values(["start_time", "publish_time"]), duplicate_count


def select_forecast(forecasts: pd.DataFrame, cutoff: datetime | None = None, vintage: datetime | None = None) -> pd.DataFrame:
    if forecasts.empty:
        return forecasts.copy()
    selected = forecasts
    if vintage is not None:
        selected = selected.loc[selected["publish_time"].eq(pd.Timestamp(vintage))]
    elif cutoff is not None:
        selected = selected.loc[selected["publish_time"].le(pd.Timestamp(cutoff))]
        selected = selected.sort_values(["start_time", "publish_time"]).groupby("start_time", as_index=False).tail(1)
    return selected.sort_values("start_time")


def matched_pairs(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    if actuals.empty or forecasts.empty:
        return pd.DataFrame(columns=["start_time", "actual", "forecast", "publish_time", "error", "absolute_error", "shortfall"])
    merged = actuals.rename(columns={"generation": "actual", "publish_time": "actual_publish_time"}).merge(
        forecasts.rename(columns={"generation": "forecast"}), on="start_time", how="inner"
    )
    merged["error"] = merged["forecast"] - merged["actual"]
    merged["absolute_error"] = merged["error"].abs()
    # Positive shortfall means actual wind was below forecast, not total procurement need.
    merged["shortfall"] = (merged["actual"] - merged["forecast"]).clip(lower=0)
    return merged.sort_values("start_time")


def metrics(pairs: pd.DataFrame) -> dict[str, float | int | None]:
    if pairs.empty:
        return {"matched_samples": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "wape_percent": None, "mean_wind_shortfall_mw": None}
    errors = pairs["error"]
    actual_sum = float(pairs["actual"].sum())
    return {
        "matched_samples": int(len(pairs)),
        "mae_mw": round(float(errors.abs().mean()), 2),
        "rmse_mw": round(float(math.sqrt((errors.pow(2)).mean())), 2),
        "bias_mw": round(float(errors.mean()), 2),
        "wape_percent": round(float(errors.abs().sum() / actual_sum * 100), 2) if actual_sum > 0 else None,
        "mean_wind_shortfall_mw": round(float(pairs["shortfall"].mean()), 2),
    }


def rows(frame: pd.DataFrame, actuals: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    actual_index = actuals.set_index("start_time")["generation"] if actuals is not None and not actuals.empty else pd.Series(dtype=float)
    output: list[dict[str, Any]] = []
    for record in frame.itertuples(index=False):
        item: dict[str, Any] = {"start_time": record.start_time.isoformat().replace("+00:00", "Z"), "generation_mw": float(record.generation)}
        if hasattr(record, "publish_time"):
            item["publish_time"] = record.publish_time.isoformat().replace("+00:00", "Z")
        if actuals is not None:
            actual = actual_index.get(record.start_time)
            item["actual_mw"] = None if pd.isna(actual) else float(actual)
        output.append(item)
    return output
