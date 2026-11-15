# Mission 18 — Technical Lead review

Base: `main` at `21e4464`. Branch: `feat/multivariable-frontend`.
Local implementation only; no commit, push, merge or deployment has been performed.
Implementation: November 14–15, 2026 UTC. Continuation verification: November 15, 2026 UTC.
Status: final local gates passed; stopped for Technical Lead review. Earlier failed
diagnostic runs remain recorded below. No release or deployment approval is implied.

## Working application

The React dashboard discovers availability through `GET /v2/datasets` and supports
T2M, PRECTOTCORR, QV2M, U10M, V10M and PS. Unavailable entries are disabled and
explained. A failed temperature source leaves other ready variables selectable.
All six original local files are present in this checkout.

The selected record uses v2 metadata, monthly and annual endpoints with Zod runtime
validation. Catalog ID, full dataset ID and SHA-256 bind every response; metadata's
nested identity must agree. Units, conversions and annual methods are checked across
responses. Invalid provenance withholds scientific output. Selection/reload aborts
requests, clears old results, resets chart controls and discards late completions.

Charts, keyboard sliders, year filters and four-decimal tables are shared across
variables. Units are °C, mm/month and mm/year, g/kg, signed m/s, and hPa. Wind signs
and zero references are retained. Original NASA product links, preambles, metadata,
identity, validation details, warnings, limitations and source hashes are inspectable.

Annual methods are explicit: equal-month temperature means, precipitation totals,
and calendar-day-weighted means for humidity, wind components and pressure. All
conversions and annual values come from the backend. The frontend computes no new
scientific statistics or observations.

Only T2M loads the legacy analysis, with both its existing provenance check and the
v2 catalog hash check. Its approved trend, interval, p-value, interpretation,
climatology and anomalies remain available. Other variables show descriptive
records only. Backend implementation, identity checks, manifests, tests, dependency
lockfiles and all six source CSVs are unchanged.

## Verification results

| Gate | Result |
| --- | --- |
| Frontend unit/component/client tests, `npm.cmd test` | **43 passed, 0 failed**, 4 files; final run after chart fix: 37.13 s |
| Frontend lint, `npm.cmd run lint` | Passed, zero warnings |
| Standalone TypeScript, `npm.cmd run typecheck` | Passed, exit code 0 |
| Production build, `npm.cmd run build` | Passed, exit code 0; 1,787 modules transformed; final Vite build 12.40 s |
| Development Playwright, desktop and Pixel 7 | **16 passed, 0 failed**, 0 skipped, 0 flaky; 163.411 s; 16 attempts |
| Built production Playwright, desktop and Pixel 7 | **2 passed, 0 failed**, 0 skipped, 0 flaky; 20.600 s; 2 attempts |
| Full unchanged backend suite, `python -m pytest -c backend/pyproject.toml backend/tests` | **224 passed, 0 failed**, 0 skipped; 39.39 s; one existing dependency deprecation warning; includes real-source integration and original temperature regressions |
| Independent temperature audit | Passed; 420 observations, full-rank 13-parameter model |
| Independent multivariable source audit | **6 passed, 0 failed**; each dataset has 420 months and 35 complete years |
| Independent audit against running backend | **6 passed, 0 failed**; all 2,520 monthly and 210 annual values match the independent Decimal audit (`rel_tol=1e-12`, `abs_tol=1e-10`), with matching identities, hashes, units, conversions and methods |
| Source integrity and `git diff --check` | Passed after all suites; **44/44 protected files unchanged**, including all six CSVs, all backend source/tests/manifests and both dependency lockfiles; backend/data/frontend lockfile diff and whitespace check exit codes 0 |

Final browser commands use `--workers=1 --retries=0 --trace=off`. The development
and production suites run sequentially. Runtime response validation, provenance
binding and the application's 12-second individual request timeout are unchanged.
The six-dataset rendering check fails on a first-attempt timeout; it never reloads
conditionally to turn a failed source request into a pass.
The final source verification completed between 01:59:28 and 02:02:36 UTC on
November 15. Development passed 8/8 desktop and 8/8 mobile checks; the built preview
passed 1/1 desktop and 1/1 mobile checks, including both frequencies for each source.

## Browser findings and retained run history

The first continuation run with full diagnostic traces finished **6 passed,
10 failed**, 0 skipped and 0 flaky, in 673.958 s. Every test had exactly one
attempt. The failures remain preserved; they are not reclassified as passes.
Eight tests failed on real request timeouts, across T2M, precipitation and catalog
loading. Two instances of the new timeout-recovery test failed because its handler
continued an already handled route after `unroute`. That was a test-harness defect.
The handler now finishes its intentional stalled request before removing interception.
The mismatch test installs its interception after the initial temperature record
loads, and the unavailable-catalog test removes interception before selecting a
healthy variable. Both still exercise the intended failure and recovery paths.

Workstation evidence during the traced run: **100% CPU**, 398,308 KiB of free
physical memory out of 8,205,052 KiB total (about 389 MiB free / 7.8 GiB total).
Direct catalog and V10M metadata requests took 0.1534 s and 0.0243 s while their
Vite-proxied checks took 6.7697 s and 0.2036 s. Initial direct metadata checks for
all six sources took 0.0063–0.0123 s. The traces show selected-record requests
aborting around the existing 12-second limit while the UI withholds output.
These measurements support local serving/browser/test-runner scheduling pressure;
they do not isolate a single root cause or establish a backend data defect.

After the harness fixes, the run with tracing disabled passed **16/16** in
162.268 s; the production preview passed **2/2** in 20.685 s. Both used one worker
and zero retries, with no skipped or flaky tests. These runs preceded the visual
fix below and are retained separately from the final source verification.
Disabling diagnostic recording reduces overhead; it does not relax assertions,
extend application request timeouts or automatically repeat failed requests.
No existing user browser sessions were terminated or workstation settings changed.

Screenshot inspection then found an application display defect: the fixed chart
margin clipped the leading digit of grouped precipitation/pressure axis labels
(for example `1,454.4`). The plot now reserves space for the formatted tick text.
Backend values, conversions and aggregation are untouched. A shared browser
assertion checks actual SVG text bounds for monthly and annual charts of all six
variables in both development and the built production application. This checks
rendered geometry independently of the margin implementation. Updated screenshots
confirm the complete labels are visible.

A separate, deliberately stalled V10M metadata test verifies the real 12-second
timeout, withheld chart/product link, one metadata request before the user's reload,
and recovery only after an explicit click. Test screenshots now use each test's
output directory, preserving earlier artifacts and distinguishing attempts.

Evidence is retained locally under the ignored directory
`frontend/playwright-report/mission18-continuation-20261115T010707Z/`:
`prior-test-results/`, `integrity-before.json`, timing and source-audit JSON,
logs, screenshots, the original full traces and each Playwright JSON report.
`development-results.json` is the failed traced run;
`development-final-results.json` and `production-results.json` are the passes before
the chart fix. `development-reviewed-results.json` and
`production-reviewed-results.json` identify the final source runs.
`verification-summary.json` consolidates all attempts without filtering failures.
`backend-results.xml` and `backend-tests.log` record the 224-test regression gate;
`integrity-after.json`, `integrity-summary.json` and `git-final-checks.json` record
the final byte and Git comparisons. The final frontend, backend and browser suites total **285
passed, 0 failed**; historical diagnostic attempts are separate, not added to that
final-source total.

The live browser checks exposed an active-selection bug: reselecting the current
option aborted its requests without triggering a new effect. The selector now
ignores an unchanged selection; a regression test verifies that data stays visible
without extra requests. Screenshot inspection also led to moving the axis unit
above the plot to prevent tick-label overlap. Source product links are shown only
when verified metadata is available, avoiding a guessed product during errors.
Number and UTC date formatters are reused across the full record; regression
tests preserve grouping, precision, signs, calendar labels and p-value formatting.
Earlier browser runs hit the 15-second test assertion while successful data requests
were still completing (the captured last temperature response took 11.4 seconds).
Test assertions now allow 30 seconds for discovery followed by selected-record
loading; application requests retain their existing 12-second individual timeout.
The loading test holds only catalog discovery, keeping other API requests direct.

Verified runtime: Node.js 26.12.0, npm 11.20.0, Python 3.13.17,
Google Chrome 157.0.8103.40, Playwright 1.65.1, Vitest 4.1.12, Vite 7.3.8. The final build emits
`dist/index.html` (748 bytes), CSS (23,794 bytes), JavaScript (365,276 bytes),
and the existing SVG icon (285 bytes). No raw CSVs or synthetic fixtures are
bundled. Rollup removed two upstream Zod purity annotations and completed normally.
The JavaScript is `assets/index-BjH8pzVo.js`, SHA-256
`35c84065f23646ea4474d2a65eb3146de0c0e059e58adebff66c6d1aaf7000d5`.
The initial Vitest startup was blocked by sandbox access to ancestor directories;
the authorized run outside that sandbox passed. A PowerShell wrapper also reported
failure while relaying build warnings; an isolated npm run confirmed exit code 0,
and the final runner captures native exit codes explicitly. These were tooling
incidents, not frontend assertion failures.

The unchanged backend test environment reports one Starlette deprecation warning
about its existing httpx TestClient integration. No dependency changes were made.
The independent temperature audit reported a slope of 0.009139123951911188 °C/decade
and p = 0.8968490236598302. This remains a nonsignificant temperature result; no
analogous inference was added for the other variables.

## Source integrity

SHA-256 was recomputed after implementation; every value equals its initial and
approved snapshot checksum:

| Variable | SHA-256 |
| --- | --- |
| T2M | `b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0` |
| PRECTOTCORR | `1ac9ec55d13116f88606037303c9f8bb9d60806620d54a41999e11956781be23` |
| QV2M | `13c1ea286bd89b5537b4ef0317bd1079c605d5f3314af1c0a1c7a0e5764ffb43` |
| U10M | `a48bb11896167b7bc4174e4c8f13cfb9d67562587e73f8b1de546b79352fd1d2` |
| V10M | `380bbbb395be93c7ddc6adfad5b6074498806e40bd642ba4d94476343051f9f6` |
| PS | `e71b283c2a848ac1b201b512f612468d839c7cac9f2d40f8c91259ea78b862e0` |

## Deployment dependencies and limits

See the [frontend guide](../frontend/README.md) for reproducible commands and the
[v2 backend guide](multivariable-api.md) for source packaging.

Production requires static `frontend/dist/`, a running Python 3.13 FastAPI backend,
all six reviewed packaged manifests, and the exact six original CSVs supplied
separately as private artifacts/read-only mounts. Raw sources remain Git-ignored
and are excluded from the frontend bundle and backend wheel.

Use absolute `EARTHSCOPE_DATA_PATH` for temperature and `EARTHSCOPE_V2_DATA_DIR` for
the five additional sources. Supply a same-origin `/api` reverse proxy stripping
that prefix for both v2 and legacy routes, or build with `VITE_API_BASE_URL` and
configure exact `EARTHSCOPE_CORS_ORIGINS`. Vite development/preview proxies do not
ship in the static artifact. Restart all workers after source/configuration changes;
verify the entire catalog and all response identities. `/health` is T2M-specific.

No live NASA retrieval, forecasts, database, authentication, point-data substitution,
sector decision tools or operational aviation/marine advice is implemented. Retrieval
time, spatial weights and absent export bounds remain unknown. New statistical
analysis for the five additional variables requires separate scientific approval.
Automated accessibility and mobile emulation do not replace screen-reader and
physical-device review. Production hosting and a production reverse proxy remain
unverified because deployment is explicitly deferred for Technical Lead review.
