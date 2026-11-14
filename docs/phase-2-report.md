# Phase 2 — Interactive frontend MVP

Team CO2 · EarthScope AI · 2026-11-14

Prepared for Technical Lead review. Work is local and uncommitted on
`feat/frontend-mvp`, created after `git fetch origin` and
`git merge --ff-only origin/main`. Both `main` and fetched `origin/main` were at
`d76e75e0201370c16a6b7ebfc913fc8a458b9920` (PR #1). No commit, push, merge of the
feature branch, publication or deployment is authorized or performed.

**Checkpoint A result: required frontend verification passed.** Technical Lead approval
of the staged six-dataset plan is acknowledged; this checkpoint verifies the existing
temperature frontend only. No multi-variable integration was implemented. The branch
and HEAD above remained unchanged throughout this checkpoint.

## Delivered scope

- React, TypeScript and Vite in `frontend/`, with the existing npm lockfile preserved.
- A professional responsive Earth intelligence dashboard with broad cross-sector
  positioning, one fixed study area (The Gambia) and one variable (MERRA-2 T2M).
- Monthly and annual temperature exploration, chart-only year filters, anomalies
  and climatology views, numeric readouts, keyboard observation sliders and data tables.
- Backend-supplied trend, 95% interval, p-value, observation count, record period,
  interpretation, assumptions and limitations. Full-record statistics remain clearly
  distinguished from chart filters. Tiny p-values retain scientific notation.
- NASA source/provenance panel with product link, geographic support, validation
  completeness, conversion/units basis, warnings, metadata/preamble and source checksum.
  Retrieval date is explicitly unknown, rather than inferred from file timestamps.
- Methodology and scientific limits, including equal-month annual weighting,
  descriptive full-record climatology, reanalysis limitations and noncausal inference.
- Planned application cards for fisheries/marine, aviation, agriculture, disaster
  management, government/communities and science/education. Each card is labeled
  planned and describes validation needs, without asserting sector results.
- Loading, per-endpoint errors, empty series, timeout/cancellation and reload recovery.
  Trend-only failure preserves matched descriptive data.
- Accessible landmarks, skip navigation, visible focus, labeled controls, text and
  table alternatives, reduced-motion support and locally scrolling mobile charts.
- Setup/configuration and production-integration documentation in the frontend
  README; automated unit/component and real-API browser checks.

## Scientific and engineering boundary

The approved backend and its statistical methods are unchanged. The frontend requests
all six existing GET endpoints. Runtime Zod parsers mirror the Pydantic response
contracts and infer TypeScript types. Every scientific response must match validated
metadata's source SHA-256. Failed metadata validation withholds scientific output;
mismatched snapshots never enter charts. Scientific numbers and conclusions come
only from the API. The frontend performs presentation formatting and chart coordinate
mapping, with no regression, annual averaging, anomaly or climatology calculations.

There are no live NASA API calls, new countries or variables, sea-temperature claims,
fishing recommendations, aviation operations/safety advice, forecasts, raw-data
publication, backend changes, cloud/database changes or deployment infrastructure.
The globe is decorative; it is not an analytical map or a country boundary.

## Validation record

Checkpoint A ran on Windows with Node.js `v26.12.0` and npm `11.20.0`.
The installed lockfile records React `19.3.1`, TypeScript `5.9.3`, Vite `7.3.8`,
Vitest `4.1.12`, ESLint `10.15.0`, Playwright `1.65.1` and axe-core `4.14.0`.
No install, dependency update, branch switch or lockfile regeneration was performed.

The actual scripts in `frontend/package.json` were inspected before execution:

| Command, working directory `frontend/` | Actual script | Final result after fixes |
| --- | --- | --- |
| `npm.cmd run lint` | `eslint . --max-warnings 0` | Exit 0; no lint errors or warnings |
| `npm.cmd run typecheck` | `tsc -b` | Exit 0; no TypeScript diagnostics |
| `npm.cmd test` | `vitest run` | Exit 0; 3 files passed, 17 tests passed; 29.88s |
| `npm.cmd run build` | `tsc -b && vite build` | Exit 0; 1,785 modules transformed; built in 8.78s; two upstream annotation warnings below |
| `npm.cmd run test:e2e` | `playwright test` | Exit 0; all 6 desktop/mobile cases passed in 1.9m |

The final build produced:

```text
dist/index.html                   0.73 kB | gzip:   0.42 kB
dist/assets/index-C4Zz30WK.css   23.26 kB | gzip:   5.80 kB
dist/assets/index-BIgHrYDj.js   351.46 kB | gzip: 107.53 kB
```

Initial Checkpoint A lint and typecheck also exited 0. Initial unit/component tests
passed all 17 tests in 33.56s. The initial production build passed in 28.75s.
These gates were repeated after the accessibility fix; the table above records the
final source. The initial browser run executed all six cases and reported **4 failed,
2 passed (2.0m)**. Failures were investigated and corrected rather than excluded.

### Investigated failures and minimal corrections

1. **Application accessibility defect:** axe reported
   `label-content-name-mismatch` on the brand link in both desktop and mobile cases.
   Its explicit `aria-label="EarthScope AI home"` omitted the visible
   `EARTH INTELLIGENCE` text. Removed that overriding attribute in `src/App.tsx`,
   allowing the visible content to supply the accessible name. This is the only
   application behavior change made in Checkpoint A.
2. **Browser-test routing defect:** the missing-source case used `**/api/**`, which
   also intercepted Vite's `http://127.0.0.1:5173/src/api/client.ts`. The preserved
   desktop/mobile traces show that JavaScript module receiving the injected HTTP 503,
   so the application could not start. Scoped the injection to
   `http://127.0.0.1:5173/api/**` in `e2e/dashboard.spec.ts`. The repaired test now
   verifies the application's actual missing-source state at 320px width.

The browser case was also strengthened to check the requested evidence explicitly:
loading while real API requests are held, backend confidence-interval endpoints and
level, monthly values, anomalies, climatology, and the backend model specification.
The held requests are released to the real backend; no scientific responses are
fabricated. No configured browser cases or axe rules were removed.

### Real-service browser and visual evidence

Playwright ran installed Google Chrome against Vite at `http://127.0.0.1:5173` and
the unchanged FastAPI service at `http://127.0.0.1:8000`. It started and stopped its
own backend process and reused the existing Vite listener. Existing development
processes were left running.

Profiles: desktop **1440 × 1000**, and Pixel 7 emulation **412 × 839**, touch enabled,
device scale factor 2.625. The missing-source case additionally uses **320 × 740**
in both profiles.

| Case, executed in both profiles | Verified outcome |
| --- | --- |
| Real API values, interactive views, accessible layout and keyboard controls | API-derived slope, interval, confidence level, p-value, interpretation and source hash agree with the UI. Monthly/annual controls, year filtering, annual table values, anomaly/climatology values, metadata and model specification work. Full-record observation count remains unchanged by chart filtering. Loading is visible and reload is disabled before real API requests are released. |
| Trend failure preserves descriptive output and retry restores analysis | Injected `/trend` HTTP 503 shows an error while the monthly chart remains available; removing the injected failure and reloading restores the real backend analysis. |
| Narrow layout and missing source show usable errors without scientific charts | API-only HTTP 503 responses show source errors and an enabled reload control, withhold scientific charts, and cause no page-wide horizontal overflow at 320px. |

The real-data cases passed full-page axe checks tagged `wcag2a`, `wcag2aa`,
`wcag21a` and `wcag21aa`, with **zero detected violations** on both profiles.
Keyboard ArrowLeft/Home exploration passed. No uncaught page JavaScript errors were
observed in these real-data cases. Desktop/mobile screenshots were visually inspected.

Local, ignored evidence:

- `frontend/test-results/dashboard-desktop.png` and `dashboard-mobile.png`:
  full-page screenshots after the tested interactions.
- `frontend/test-results/dashboard-desktop-overview.png` and
  `dashboard-mobile-overview.png`: viewport screenshots.
- `frontend/playwright-report/checkpoint-a-initial/`: initial failure screenshots,
  error contexts and traces, copied before the passing browser rerun.

### Scientific-output review

- Production components render trend numbers and interpretation from parsed backend
  responses; they do not select a warming/cooling conclusion or refit statistics.
- Chart coordinate scaling and number/date formatting are presentation operations.
  Annual means, climatology and anomalies continue to come from their API fields.
- Tests exercise nonsignificant and cooling interpretations using explicitly labeled
  synthetic test fixtures. The real-service cases compare values dynamically with the
  actual approved T2M API, without hardcoded expected scientific results.
- A scan of production JavaScript found no `synthetic-test.csv`,
  `SYNTHETIC TEST DATA` or `Synthetic fixture, not NASA observations` markers.
- Sector cards remain planned; this checkpoint adds no datasets to the interface,
  sector results, forecasts or operational recommendations.

### Warnings and environment distinctions

- Final production build emits two Rollup warnings about comment annotations in
  Zod: `node_modules/zod/v4/core/util.js (400:0)` and
  `node_modules/zod/v4/core/regexes.js (74:0)`. Rollup removes the unsupported
  annotations and completes the build. Dependency files were not edited or upgraded.
- Playwright workers warn that `NO_COLOR` is ignored because `FORCE_COLOR` is set.
  This is an inherited environment warning; all six browser cases pass.
- `git diff --check` exits 0 but Git warns that the pre-existing README's LF line
  endings will be replaced by CRLF the next time Git touches it. The README was
  not converted, edited or staged in this checkpoint.
- Tests, builds and browser execution used approved execution outside the restricted
  filesystem sandbox. Earlier work had demonstrated that sandboxed esbuild could not
  traverse parent directories to load Vite configuration. This was an environment
  restriction, separate from the two verified defects above.
- Earlier dependency installation/cache issues were not worked around by reinstalling
  or replacing the lockfile in Checkpoint A. The existing installed tree was used
  successfully. A fresh online/offline clean install was not re-tested here.

### Preservation and Git checks

Before and after verification, SHA-256 comparisons covered **all 23 tracked backend
files**, **all six original CSVs**, `frontend/package.json` and
`frontend/package-lock.json`: **no differences and no additions** in that protected set.
`git diff --exit-code -- backend` also exited 0.

```text
frontend/package.json
592cd27b18513082b22bc1347e1c462da99a2ad3a3941c496928ee9e13355c2e

frontend/package-lock.json
38a2e6e593361985da241ed2e69f45e2bed25d5011e1bf3815e0922a983137b1
```

Original CSV hashes, unchanged:

| Variable | SHA-256 |
| --- | --- |
| T2M | `b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0` |
| PRECTOTCORR | `1ac9ec55d13116f88606037303c9f8bb9d60806620d54a41999e11956781be23` |
| U10M | `a48bb11896167b7bc4174e4c8f13cfb9d67562587e73f8b1de546b79352fd1d2` |
| V10M | `380bbbb395be93c7ddc6adfad5b6074498806e40bd642ba4d94476343051f9f6` |
| QV2M | `13c1ea286bd89b5537b4ef0317bd1079c605d5f3314af1c0a1c7a0e5764ffb43` |
| PS | `e71b283c2a848ac1b201b512f612468d839c7cac9f2d40f8c91259ea78b862e0` |

Files edited by Checkpoint A:

- `frontend/src/App.tsx`: remove the mismatched accessible-name override.
- `frontend/e2e/dashboard.spec.ts`: correct failure injection and strengthen real-API
  verification for the requested behaviors.
- `docs/phase-2-report.md`: record commands, results, fixes, warnings and limits.

All other existing implementation/configuration files were preserved. The pre-existing
`.gitignore`, README encoding/BOM diff and deleted placeholder were not changed in
this checkpoint. Generated build, test and evidence files remain ignored.

`git diff --cached --name-only` returned no output: **nothing is staged**, including
credentials, raw CSVs, generated caches or build artifacts. `git check-ignore` confirms
that `frontend/node_modules`, `.npm-cache`, `dist`, `test-results`,
`playwright-report` and `tsconfig.tsbuildinfo` are ignored.

Branch and short status at completion (the frontend remains mostly untracked):

```text
## feat/frontend-mvp
 M .gitignore
 M README.md
 D frontend/.gitkeep
?? docs/phase-2-report.md
?? frontend/.env.example
?? frontend/README.md
?? frontend/e2e/
?? frontend/eslint.config.js
?? frontend/index.html
?? frontend/package-lock.json
?? frontend/package.json
?? frontend/playwright.config.ts
?? frontend/public/
?? frontend/src/
?? frontend/tsconfig.json
?? frontend/vite.config.ts
```

The expanded status contains 28 untracked files. Final port/process checks confirm
that the pre-existing Vite processes and listener on port 5173 remain available;
the browser suite's FastAPI listener on port 8000 has stopped.

No reset, clean, branch switch, commit, push, merge or deployment was performed in
Checkpoint A. Untracked source remains outside a Git commit and must be preserved
during the next review stage.

### Prior backend verification

These results were executed earlier in the session against the unchanged backend.
They were not re-run or counted as new test executions in Checkpoint A:

| Command from repository root | Exact result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests` | 112 passed, 1 warning in 19.64s |
| `backend/.venv/Scripts/python.exe -m ruff check backend` | All checks passed! |
| `backend/.venv/Scripts/python.exe -m ruff format --check backend` | 18 files already formatted |
| `backend/.venv/Scripts/python.exe -m pip check` | No broken requirements found. |
| `backend/.venv/Scripts/python.exe backend/scripts/independent_trend.py data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv` | Exit 0; independent NumPy/manual HAC audit completed on the approved 420-observation source |

The backend warning is an existing Starlette deprecation concerning `httpx` in
`TestClient`; it does not fail the suite and was not addressed by altering the approved
backend. The independently read source SHA-256 is
`b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0`.

## Limitations and handoff

The raw CSV remains ignored and must be supplied separately to the backend. A fresh
checkout cannot serve scientific data without it. Production needs a same-origin
`/api` reverse proxy or a build-time API URL and an approved backend CORS origin;
Vite's development proxy is not a production proxy. No hosting setup is included.

Response parsers are maintained alongside, rather than automatically generated from,
the backend schemas; future API changes require coordinated updates. There is no
runtime dataset switching, live refresh, authentication, forecast or operational
decision support. Chart filters do not trigger model refitting.

Automated browser/accessibility results do not replace manual screen-reader,
assistive-technology and device review. Google Chrome and the backend virtual
environment are required for the supplied local browser suite.

The browser suite tests the Vite development integration with FastAPI, not a deployed
production reverse proxy. Production output was built successfully but was not hosted
or deployed. Firefox, Safari, physical mobile devices and manual screen readers were
not tested. The two upstream build warnings and inherited browser color warning above
remain; there are no unresolved frontend failures in the executed required gates.

Stop point: Technical Lead review of the local implementation, scientific messaging,
validation evidence and integration requirements before any subsequent Git or hosting
action.
