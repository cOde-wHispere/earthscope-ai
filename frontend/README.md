# EarthScope AI frontend MVP

React + TypeScript + Vite. A responsive scientific dashboard for one approved Gambia
MERRA-2 T2M snapshot. Sector applications are informative future possibilities only.

## Prerequisites and local development

Use Node.js 22.12+ (or 20.19+); use an actively supported release. `package-lock.json`
pins the installed dependency graph. Start the unchanged FastAPI backend and supply
its approved local CSV as described in [the backend README](../backend/README.md).

From this directory in PowerShell:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. On Unix-like systems use `npm` instead of `npm.cmd`.
`npm.cmd` avoids the workstation's restriction on PowerShell `.ps1` shims. Both
backend and frontend must be running. No NASA credentials or live NASA API are used.

The default relative `/api` base uses the Vite development proxy to
`http://127.0.0.1:8000`. Optionally copy `.env.example` to `.env.local` and set
`VITE_API_BASE_URL=http://127.0.0.1:8000` (restart Vite afterward). That direct browser
connection requires an allowed backend origin; its existing defaults allow Vite on
localhost and 127.0.0.1 port 5173. Never put credentials in a `VITE_` variable.

## Checks

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e
```

Unit/component tests use clearly labeled synthetic fixtures in `src/test/`; production
imports no fixture and supplies no fallback scientific values. Tests cover schema
validation, source matching, partial failures, timeout, cancellation, loading/empty
states, error recovery, chart controls and backend-provided interpretations.

Playwright starts a local backend and Vite server (or reuses existing listeners) and
uses installed Google Chrome via `channel: 'chrome'`. It requires the approved CSV,
the workspace backend virtual environment, and Chrome. It fails rather than fabricating
data when real backend output is unavailable. It checks live API/display agreement,
keyboard exploration, filtering, responsive layouts, injected failure recovery and
axe WCAG A/AA checks. Desktop/mobile screenshots, traces and reports are ignored in
`test-results/` and `playwright-report/`. These automated checks supplement manual
screen-reader and device testing; they do not establish complete accessibility conformance.

## API contract and scientific boundaries

`src/api/schemas.ts` mirrors the existing backend Pydantic response schemas using Zod;
types are inferred from runtime parsers. `src/api/client.ts` requests only:

| GET endpoint          | Use                                                          |
| --------------------- | ------------------------------------------------------------ |
| `/health`             | Service readiness, including HTTP 200 degraded states        |
| `/metadata`           | Validation, source identity, units, preamble and warnings    |
| `/timeseries/monthly` | Supplied temperatures, anomalies and climatology             |
| `/timeseries/annual`  | Supplied annual means and aggregation method                 |
| `/climatology`        | Supplied month-of-year means and baseline                    |
| `/trend`              | Supplied slope, interval, p-value, interpretation and limits |

Each request has a 12-second timeout and supports cancellation. Reload cancels the
previous request group. Endpoint failures remain separate; an unavailable trend does
not remove descriptive charts. Scientific responses must share the validated metadata
SHA-256; mismatched responses are withheld. Missing/invalid metadata withholds all
scientific output. Empty observation arrays produce explicit empty states.

Reusable charts map backend values to SVG coordinates and provide keyboard sliders,
numeric readouts and data tables (four decimal places). Narrow-screen plots scroll within their own
region to keep labels readable. Color is supplemented by zero position, signs,
legends and tables. Chart year filters affect the temperature view only. The full-record
trend and climatology baseline remain unchanged. No client-side scientific aggregation,
regression, climatology or anomaly calculation occurs.

The study-area globe is decorative, not a geographic boundary or analytical map.
The source metadata retains the approved country-shape and selection details. Retrieval
date remains explicitly unknown because the API does not supply one. The NASA product
link is a reference; loading the dashboard makes no NASA API requests.

## Production artifact (not deployed)

`npm.cmd run build` writes static output to `dist/`. Production must provide a
same-origin `/api` reverse proxy to FastAPI, or set `VITE_API_BASE_URL` at build time
to a backend with an explicitly approved `EARTHSCOPE_CORS_ORIGINS` configuration.
Vite's development proxy is not part of the production output. `npm.cmd run preview`
serves only static output; use an explicit API URL to test data there. The raw NASA CSV
stays with the backend and is never included in the frontend bundle.

No hosting, credentials, backend behavior or approved statistical methods are changed.
