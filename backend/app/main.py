from contextlib import asynccontextmanager
from datetime import date, datetime
import logging

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .analytics import rows
from .config import get_settings
from .elexon_client import ElexonClient
from .service import WindService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
service = WindService(ElexonClient(settings), settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="WindLens API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, error: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(RuntimeError)
async def runtime_error_handler(_: Request, error: RuntimeError):
    return JSONResponse(status_code=502, content={"detail": str(error)})


def resolve_cutoff(cutoff: datetime | None) -> datetime | None:
    if cutoff is not None and cutoff.tzinfo is None:
        raise ValueError("cutoff must include a timezone offset or Z suffix")
    return cutoff


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "windlens-api"}


@app.get("/api/metadata")
async def metadata():
    return await service.metadata()


@app.get("/api/overview")
async def overview(delivery_date: date = Query(default=date(2026, 1, 1)), cutoff: datetime | None = None, vintage: datetime | None = None):
    return await service.overview(delivery_date, resolve_cutoff(cutoff), vintage)


@app.get("/api/actuals")
async def actuals(delivery_date: date = Query(default=date(2026, 1, 1))):
    service.validate_january(delivery_date)
    actual_frame, _, _ = await service.frames(delivery_date, delivery_date)
    return {"delivery_date": delivery_date.isoformat(), "records": [{"start_time": value["start_time"], "generation_mw": value["generation_mw"], "publish_time": value["publish_time"]} for value in rows(actual_frame)]}


@app.get("/api/forecasts")
async def forecasts(delivery_date: date = Query(default=date(2026, 1, 1)), cutoff: datetime | None = None, vintage: datetime | None = None):
    data = await service.analysis(delivery_date, resolve_cutoff(cutoff), vintage)
    return {"delivery_date": delivery_date.isoformat(), "publication_cutoff": data["cutoff"].isoformat(), "records": rows(data["selected"], data["actuals"])}


@app.get("/api/forecast-vintages")
async def forecast_vintages(delivery_date: date = Query(default=date(2026, 1, 1)), cutoff: datetime | None = None):
    return await service.vintages(delivery_date, resolve_cutoff(cutoff))


@app.get("/api/accuracy")
async def accuracy(delivery_date: date = Query(default=date(2026, 1, 1)), cutoff: datetime | None = None, vintage: datetime | None = None):
    data = await service.analysis(delivery_date, resolve_cutoff(cutoff), vintage)
    return {"delivery_date": delivery_date.isoformat(), "publication_cutoff": data["cutoff"].isoformat(), "metrics": data["metrics"]}


@app.get("/api/data-quality")
async def data_quality(delivery_date: date = Query(default=date(2026, 1, 1))):
    return await service.data_quality(delivery_date)
