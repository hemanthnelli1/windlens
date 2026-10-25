# WindLens — UK Wind Forecast Intelligence

WindLens is a responsive energy-trading analytics portal for analysing national UK wind generation forecast accuracy for January 2026 delivery periods. It compares Elexon BMRS `FUELHH` wind actuals with `WINDFOR` forecast publications, retaining forecast vintages and applying a configurable decision cutoff.

**Anonymous repository suggestion:** `northbound-signal-ledger`

> No public deployment or GitHub repository has been created by this project. Add verified URLs after publishing:
>
> - Frontend URL: `TBD`
> - Backend URL: `TBD`
> - Public repository URL: `TBD`

## Product boundaries

- Scope is **national wind generation only**. No demand, price, fuel, or external generation data is used.
- `startTime` is treated as delivery-period time and `publishTime` as forecast issue time.
- All API timestamps are parsed and compared as UTC instants; the UI labels them in `Europe/London`. This prevents a UK daylight-saving display from changing joins or cutoff comparisons.
- Missing observations remain missing. They are never converted to zero.
- Forecast error is `forecast − actual`: a positive bias/error means the forecast was above actual wind generation; a negative value means it was below.
- The “wind shortfall estimate” is `max(actual − forecast, 0)` for wind. It is **not** a calculation of total electricity procurement needs, customer demand, cost, or savings.
- MAE, RMSE, bias, and WAPE are calculated only on matched pairs. WAPE is omitted when matched actual generation has a non-positive sum. MAPE is deliberately not used because it becomes unstable near zero actual generation.

## Screenshots

Run the application, select a delivery date with source coverage, and capture genuine screenshots of:

1. Overview with the actual-versus-forecast chart and KPIs.
2. Forecast Explorer with a timestamped delivery-period table.
3. Vintage Analysis with cutoff-qualified publication rows.
4. Methodology & Data Quality with retrieval and missing-record status.

Do not use fabricated screenshots or metrics.

## Architecture and data flow

```text
Elexon BMRS FUELHH / WINDFOR
        │  date-scoped HTTP requests, retries, timeouts
        ▼
FastAPI: parsing → UTC normalisation → deterministic deduplication
        │                   │
        │                   └→ preserve every (delivery, publishTime) vintage
        ▼
in-process TTL cache → cutoff/vintage selection → matched-pair metrics
        ▼
React + Vite → charts, tables, data-quality states
```

`backend/app/elexon_client.py` performs date-scoped Elexon requests. `service.py` coordinates cache and analysis; `analytics.py` contains the selection, join, and metrics logic. The React UI is in `frontend/src`.

## Elexon source access and historical retrieval

Primary documentation:

- [FUELHH — half-hourly generation outturn by fuel type](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH)
- [WINDFOR — wind generation forecast](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR)
- [Elexon Insights API documentation](https://developer.data.elexon.co.uk/)

The public Insights API base is `https://data.elexon.co.uk/bmrs/api/v1`; it did not require an API token during local endpoint verification. The app does not use a bare current stream to obtain old January data. It requests FUELHH using `settlementDateFrom`/`settlementDateTo` one settlement day at a time—the API rejects oversized month windows—and requests WINDFOR by `publishDateTimeFrom`/`publishDateTimeTo` in single UTC-day slices. Returned wind forecasts are then restricted by their `startTime` delivery timestamp. It includes two preceding publication days so early delivery periods have eligible forecasts.

Both source responses contain UTC `Z` timestamps. The API also returns a `settlementDate`/period field for actuals, but the analysis joins normalized `startTime` timestamps as required.

## Decision cutoff and vintage policy

When a specific forecast vintage is selected, WindLens shows that exact `publishTime`. Otherwise it chooses the latest forecast record with `publishTime <= cutoff` for each delivery period. The default cutoff is **12:00 Europe/London on the preceding calendar day**, configurable via `DEFAULT_CUTOFF_HOUR_LOCAL` or the UI. The native cutoff editor uses the browser’s local clock because HTML `datetime-local` controls carry no timezone; the selected instant is transmitted as UTC and the selected cutoff is displayed back in Europe/London. It is an explicit analytical assumption, not an Elexon or official market rule.

Deduplication is deterministic:

- Actuals: keep the latest `publishTime` for a duplicate wind `startTime`.
- Forecasts: deduplicate only an exact `(startTime, publishTime)` duplicate, keeping final stable source order. Different publication times remain separate vintages.

## Local setup

Prerequisites: Python 3.11+ and Node 20+.

```powershell
Copy-Item .env.example .env
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API documentation is at `http://localhost:8000/docs`; its health endpoint is `http://localhost:8000/api/health`.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The web UI is served at `http://localhost:8080`; the API is at `http://localhost:8000`. For a deployed frontend, build with `VITE_API_BASE_URL=https://your-api-host` and configure the API's `ALLOWED_ORIGINS` with the frontend origin.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `BMRS_BASE_URL` | Elexon Insights base URL | public BMRS v1 API |
| `REQUEST_TIMEOUT_SECONDS` | Per-upstream-request timeout | `20` |
| `CACHE_TTL_SECONDS` | Process-local raw daily-cache lifetime | `21600` |
| `DEFAULT_CUTOFF_HOUR_LOCAL` | Prior UK-calendar-day default cutoff hour | `12` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | local Vite `localhost` and `127.0.0.1` URLs |
| `VITE_API_BASE_URL` | Browser API base URL set at build time | `http://localhost:8000` |

No secret, token, virtual environment, build output, or raw data should be committed.

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness check |
| `GET /api/metadata` | Scope, sources, time strategy, cutoff assumption |
| `GET /api/overview` | Matched chart rows and KPIs |
| `GET /api/actuals` | Filtered wind actuals |
| `GET /api/forecasts` | Selected forecast rows |
| `GET /api/forecast-vintages` | Cutoff-qualified vintage comparison metrics |
| `GET /api/accuracy` | Metrics for a selection |
| `GET /api/data-quality` | Retrieval counts, missingness, duplicates, match count |

All date-aware endpoints accept `delivery_date=YYYY-MM-DD` within January 2026. Relevant selection endpoints accept ISO 8601 timezone-aware `cutoff` and `vintage` values.

## Tests and quality checks

```powershell
# Backend
backend\.venv\Scripts\python -m pytest backend/tests -q

# Frontend
cd frontend
npm run lint
npm test
npm run build
```

The backend tests use deterministic in-memory fixtures. They cover wind filtering, January limits, UK DST day duration, duplicate policy, forecast-vintage retention, cutoff selection, concurrent-cache sharing, MAE/RMSE/bias/WAPE calculations, zero-actual WAPE, and basic API validation. Frontend tests cover loading, core rendering, empty, and error states.

Final local verification on 25 October 2026:

- `python -m pytest backend/tests -q` — **8 passed**.
- `npm run lint` — **passed**.
- `npm test -- --reporter=verbose` — **4 passed**.
- `npm run build` — **passed**. Vite emitted a non-blocking 500 kB chunk-size warning for the charting bundle.
- `docker compose config --quiet` — **passed**.
- Real BMRS integration for `2026-01-01` — **passed**: 48 displayed delivery periods, 48 actuals, 24 selected forecast points, 24 explicit forecast gaps, and 24 valid matched pairs. Three concurrent overview calls completed while sharing four upstream date-slice downloads (one FUELHH day plus three WINDFOR publication days).
- Docker image build was **not completed** because Docker Desktop's Linux engine was not running (`dockerDesktopLinuxEngine` pipe unavailable). Start Docker Desktop and rerun `docker compose build` to verify container construction.

## Deployment readiness

The frontend is Vercel-ready via `vercel.json`; set `VITE_API_BASE_URL` in Vercel and deploy from the repository root. The FastAPI backend includes `render.yaml` for Render Docker deployment. Before deploying, set `ALLOWED_ORIGINS` to the exact Vercel origin and use the service `/api/health` path.

Vercel's standard static Vite hosting is suitable for the frontend, not for assuming a persistent FastAPI process. Render (or another container-friendly Python host) is appropriate for the backend. The current cache is per-process memory by design; use Redis or an equivalent managed cache if multi-instance persistence and predictable upstream request volume are required.

If a Vercel deployment returns 404 after navigating directly to a UI route, confirm the SPA rewrite in `vercel.json`. If requests fail from the browser, verify the production `VITE_API_BASE_URL`, HTTPS, and matching CORS origin. If Elexon rejects a data window, retain daily slicing and inspect the upstream error rather than falling back to current-stream data.

## Limitations and next steps

- Source availability, revisions, and historical retention determine whether every January 2026 period can be retrieved at runtime.
- The default cutoff is configurable but is not an official purchase deadline.
- The product intentionally cannot estimate complete electricity procurement without demand data.
- For production, add structured observability, an external cache, rate-limit dashboards, and an authenticated access layer where appropriate.
- Capture screenshots, create the repository under an anonymous name, deploy after credentials are supplied, and record the demonstration using `VIDEO_DEMO_SCRIPT.md`.

## AI assistance

AI tools, including OpenAI Codex, were used to assist development. Human review is required before operational or market decision use.
