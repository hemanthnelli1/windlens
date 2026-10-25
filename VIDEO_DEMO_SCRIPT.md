# WindLens video demo script (maximum 10 minutes)

## Recording checklist

- [ ] Start the API and web application; wait for `/api/health` to return `ok`.
- [ ] Use a January 2026 date with verified source coverage.
- [ ] Refresh the dashboard before recording and confirm data freshness and gaps are truthful.
- [ ] Keep browser zoom at 100%; hide credentials, terminals, and personal information.
- [ ] Do not claim deployment, a GitHub repository, or an uploaded video unless each has actually been completed.

## Part 1 — Customer presentation (up to 5 minutes)

**0:00–0:45 — Problem and value.** Explain that the utility needs a reliable view of national wind output uncertainty before a day-ahead decision. WindLens compares Elexon national wind actuals with forecasts, without claiming to calculate demand or total procurement.

**0:45–2:15 — Overview.** Select a January 2026 delivery date. Point out the selected publication cutoff, MAE, RMSE, signed bias, and the actual-versus-forecast chart. Define a positive bias as forecast above actual.

**2:15–3:20 — Decision boundary.** Explain that the wind shortfall card is only `max(actual − forecast, 0)` for wind. It is not electricity demand, market cost, or required total buying volume.

**3:20–4:25 — Forecast Explorer.** Show a delivery period in the table, including its forecast publication timestamp, actual, signed error, and absolute error. Point out that absent records are not silently converted to zero.

**4:25–5:00 — Vintage analysis and limitations.** Open Vintage Analysis, explain that only forecast publications at or before the displayed cutoff qualify, then state the configurable cutoff is an assumption rather than an official market rule.

## Part 2 — Technical review (up to 5 minutes)

**5:00–5:45 — Architecture.** Show the React/Vite frontend calling FastAPI. Explain that the backend provides parsing, caching, timestamp normalization, deterministic deduplication, forecast selection, and metric modules.

**5:45–6:55 — Elexon ingestion.** Point to `backend/app/elexon_client.py`. FUELHH is requested one settlement day at a time using date-scoped parameters; WINDFOR is requested in one publication-day slices, then delivery timestamps are filtered. This avoids assuming a stream endpoint provides all history.

**6:55–7:50 — Time and metrics.** Point to `timeutils.py` and `analytics.py`. All source timestamps are parsed to UTC instants, with interface labels converted to Europe/London. Explain the cutoff selection and MAE/RMSE/bias/WAPE definitions.

**7:50–8:50 — Quality and tests.** Open Methodology & Data Quality. Show raw counts, missing observation counts, duplicate policy, and matched sample count. Mention automated coverage for wind filtering, January bounds, DST day length, duplicate handling, vintages, cutoff selection, zero actual WAPE, and API error handling.

**8:50–10:00 — Operations.** Show Docker Compose, environment settings, `/api/health`, Vercel frontend configuration, and Render backend manifest. Explain that serverless filesystems/process memory are not persistent; production scale should use an external cache if needed.
