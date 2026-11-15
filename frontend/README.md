# EarthScope AI six-variable frontend

React + TypeScript + Vite. The dashboard supports six verified local Giovanni
MERRA-2 exports for The Gambia, January 1991–December 2025. Sector applications
remain research context and planned capabilities. No operational recommendations
are implemented. See [Mission 18 review results](../docs/mission18-review.md).

## Local development

Use Node.js 22.12+ (or 20.19+) with the existing `package-lock.json`, Python 3.13,
and the backend's locked dependencies. Follow the [backend README](../backend/README.md)
and [v2 deployment instructions](../docs/multivariable-api.md). Supply all six
approved CSVs separately: Git and the backend wheel exclude raw sources.

From `frontend/` in PowerShell:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173 with FastAPI on port 8000. Unix shells use `npm`.
No NASA credentials, live NASA requests, database, or remote retrieval are needed.
Reload requests the backend's current startup snapshot; it does not refresh NASA data.

The default `/api` base uses Vite's local proxy to `http://127.0.0.1:8000`.
Alternatively set `VITE_API_BASE_URL` at build/dev startup to an explicit backend
URL with an approved CORS origin. Never put credentials in a `VITE_` variable.

## Contracts and scientific scope

All network responses are validated with Zod before rendering. `GET /v2/datasets`
drives the selector and availability explanations. Missing, invalid or unavailable
datasets are disabled; a failed T2M source does not prevent selecting another ready
variable. An unavailable catalog withholds data and provides a reload action.

For the selected variable, the frontend requests `/v2/datasets/{id}/metadata`,
`/timeseries/monthly` and `/timeseries/annual`. Metadata, its nested identity,
monthly and annual responses must match the selected catalog's full dataset ID,
variable and SHA-256. Units, conversions and annual methods must also agree.
Invalid metadata withholds scientific output; other endpoint errors stay local to
their panels. Empty arrays produce empty states without substituted observations.

| Variable | Monthly / annual units | Annual method |
| --- | --- | --- |
| T2M | °C / °C | Equal-weight mean of 12 monthly means |
| PRECTOTCORR | mm/month / mm/year | Sum of 12 monthly water-equivalent precipitation totals |
| QV2M | g/kg / g/kg | Calendar-day-weighted mean |
| U10M, V10M | signed m/s / signed m/s | Calendar-day-weighted signed mean |
| PS | hPa / hPa | Calendar-day-weighted mean; exported hPa unchanged |

Precipitation includes water equivalent, rather than measuring rain alone. Specific
humidity is distinct from relative humidity. Positive U is eastward; positive V is
northward. Components are not wind speed or gusts. Surface pressure is not sea-level
pressure. The UI displays backend methods and limitations alongside the sources.

Only T2M additionally loads the unchanged legacy endpoints `/health`, `/metadata`,
`/timeseries/monthly`, `/timeseries/annual`, `/climatology` and `/trend`. Their existing
Zod parsers and source checks remain; their hashes must also match the selected v2
identity. Approved temperature trend, uncertainty, interpretation, climatology and
anomalies are preserved. No such analysis is requested or displayed for other variables.
`/health` remains T2M-specific; the catalog establishes six-variable availability.

Each request has a 12-second timeout. Selection and reload abort the prior request
group, clear displayed results, and ignore late completions even when transport does
not honor abort. Selection also resets chart frequency, year filters and observation
position. No browser-side scientific conversion, aggregation or inference occurs.

Charts retain keyboard sliders, year filters, accessible descriptions, four-decimal
tables and internal horizontal scrolling on small screens. Wind readouts and tables
show signs; the chart includes a zero reference. Temperature retains its full-record
climatology overlay. Chart filters never alter the approved temperature analysis.

The decorative globe is not an analytical map. Original NASA product links, source
preambles, metadata, reviewed identity, validation warnings and checksums are exposed.
Retrieval dates and spatial weights remain unknown when absent from the exports.

## Verification

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run test:e2e -- --workers=1 --retries=0 --trace=off
npm.cmd run build
npm.cmd run test:production -- --workers=1 --retries=0 --trace=off
```

Unit/component tests use explicitly synthetic fixtures confined to `src/test/`.
Playwright uses installed Google Chrome (`channel: 'chrome'`), the workspace backend
venv and the actual six local CSVs. It starts local servers or reuses listeners and
fails if the required real sources are unavailable. Run build before production
tests. Those tests use `vite preview` on port 4173 and its inherited local API proxy.
Run expensive suites sequentially on constrained workstations. The commands above
disable diagnostic tracing to reduce memory overhead; console reports and failure
screenshots remain available. The default configuration retains traces on failure;
use `--trace=on` for a diagnostic run. Mission 18 records both the failed traced run
and final results, rather than retrying failures automatically. Test-only waits allow
slow browser startup; the application request timeout stays at 12 seconds.

Desktop (1440×1000), Pixel 7 emulation, 320-pixel error layouts, API/display agreement,
keyboard controls, failures, recovery, identity mismatch and WCAG A/AA axe checks are
covered. Screenshots, traces and logs are ignored under `test-results/`. Automated
checks supplement manual screen-reader and physical-device testing.

## Production dependencies; not deployed

`npm.cmd run build` generates `dist/`. Serve those static files and configure a
same-origin `/api` reverse proxy that strips `/api` and forwards both `/v2/*` and
legacy temperature paths to FastAPI. Alternatively build with an explicit
`VITE_API_BASE_URL` and configure exact `EARTHSCOPE_CORS_ORIGINS` before backend startup.
Vite's dev/preview proxies are local tooling and are absent from the production artifact.

Deploy the approved backend package with all six reviewed JSON manifests. Mount the
six original CSVs read-only, preserving bytes and filenames. Set absolute
`EARTHSCOPE_DATA_PATH` for T2M and `EARTHSCOPE_V2_DATA_DIR` for the five additional
sources; restart every worker after source/config changes. Verify all six catalog
entries, identities, hashes and series. A healthy legacy `/health` alone is insufficient.
No credentials, raw CSVs or test observations belong in the frontend artifact.

The working tree is local review work. Nothing is committed, pushed, merged or deployed.
