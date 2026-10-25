import asyncio
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class ElexonClient:
    """Small, defensive client for date-scoped BMRS raw dataset access.

    FUELHH accepts settlementDateFrom/settlementDateTo and is limited to one
    settlement day per request. WINDFOR accepts publishDateTimeFrom/To; this
    client deliberately requests one UTC publication day at a time and filters
    its returned delivery timestamps downstream.
    """

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        last_error: Exception | None = None
        async with httpx.AsyncClient(base_url=self.settings.bmrs_base_url, timeout=timeout, transport=self.transport) as client:
            for attempt in range(3):
                try:
                    response = await client.get(path, params=params, headers={"Accept": "application/json"})
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    data = payload.get("data", payload) if isinstance(payload, dict) else payload
                    if not isinstance(data, list):
                        raise ValueError("BMRS response did not contain a list of records")
                    return [record for record in data if isinstance(record, dict)]
                except (httpx.HTTPError, ValueError) as error:
                    last_error = error
                    if attempt < 2:
                        await asyncio.sleep(0.5 * (2**attempt))
            raise RuntimeError(f"BMRS request failed for {path}: {last_error}")

    async def actuals_for_day(self, day: date) -> list[dict[str, Any]]:
        value = day.isoformat()
        return await self._get("/datasets/FUELHH", {"settlementDateFrom": value, "settlementDateTo": value, "format": "json"})

    async def forecasts_published_on(self, day: date) -> list[dict[str, Any]]:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return await self._get(
            "/datasets/WINDFOR",
            {"publishDateTimeFrom": start.isoformat().replace("+00:00", "Z"), "publishDateTimeTo": end.isoformat().replace("+00:00", "Z"), "format": "json"},
        )

    async def dataset_metadata(self) -> list[dict[str, Any]]:
        return await self._get("/datasets/metadata/latest", {"format": "json"})
