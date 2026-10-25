from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

UK_TZ = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")


def parse_utc(value: str | datetime) -> datetime:
    parsed = pd.Timestamp(value)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone offset or Z suffix")
    return parsed.tz_convert("UTC").to_pydatetime()


def january_2026_bounds() -> tuple[datetime, datetime]:
    return datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)


def uk_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=UK_TZ)
    end = start + timedelta(days=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def default_day_ahead_cutoff(day: date, cutoff_hour: int) -> datetime:
    """Assumption, not an Elexon or market rule: previous local day at cutoff_hour."""
    previous_day = day - timedelta(days=1)
    return datetime.combine(previous_day, time(hour=cutoff_hour), tzinfo=UK_TZ).astimezone(UTC)


def iso_utc(value: datetime | pd.Timestamp) -> str:
    timestamp = pd.Timestamp(value).tz_convert("UTC")
    return timestamp.isoformat().replace("+00:00", "Z")


def local_label(value: datetime | pd.Timestamp) -> str:
    return pd.Timestamp(value).tz_convert("Europe/London").strftime("%d %b %Y, %H:%M %Z")
