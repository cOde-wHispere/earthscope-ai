# EarthScope AI scientific backend

Python **3.13** and FastAPI. Serves one local Giovanni MERRA-2 T2M export for The Gambia,
January 1991–December 2025. The application reads the source without changing it and makes
no network requests. The additive `/v2` API also serves five independently validated
environmental exports. See [multi-variable API, methods and deployment](../docs/multivariable-api.md)
for all six datasets, unit conversions, failure isolation and verification commands.

From the repository root, in PowerShell, with Python 3.13 installed:

```powershell
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt -e './backend[dev]'
backend/.venv/Scripts/python.exe -m earthscope_backend.importer --verify-baseline
backend/.venv/Scripts/python.exe -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for the API contract. Stop with Ctrl+C. Activation is optional.
`requirements-lock.txt` records every resolved runtime/test dependency from the validated
Windows Python 3.13 environment, including an upstream transitive `wrapt` prerelease.
`pyproject.toml` supplies bounded direct dependencies. For a fresh resolution within those
bounds, omit `-r backend/requirements-lock.txt`.
This workstation also has a workspace-local runtime in the ignored directory
`backend/.python-runtime/python313/tools/python.exe`. To recreate its environment:

```powershell
backend/.python-runtime/python313/tools/python.exe -m venv backend/.venv
```

On Unix-like systems use `python3.13 -m venv backend/.venv` and substitute
`backend/.venv/bin/python` for the Windows interpreter path.

The default source is `data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv`.
To use another local copy of the same export, set the environment before launch:

```powershell
$env:EARTHSCOPE_DATA_PATH = 'C:\path\to\giovanni_merra2_gambia_t2m_1991_2025.csv'
```

Default and relative configured paths resolve from the repository root, independently of the
launch directory. `backend/.env.example` documents the variable; `.env` files are not
automatically loaded. The supported product, variable and 1991–2025 coverage remain fixed.
Restart after changing the source or environment. Endpoints share one startup snapshot and
its SHA-256, avoiding mixtures of data revisions. Startup also checks the packaged approved
dataset identity and exact source checksum; changing the data path never approves new bytes.

| GET endpoint | Response |
| --- | --- |
| `/health` | Liveness and dataset readiness; HTTP 200 with `ok` or `degraded` |
| `/metadata` | Source preamble, metadata entries, SHA-256, units and validation summary |
| `/timeseries/monthly` | 420 observations in Kelvin and Celsius, climatology and anomalies |
| `/timeseries/annual` | 35 annual means, each with 12 equally weighted monthly means |
| `/climatology` | 12 month-of-year means and sample counts, baseline 1991–2025 |
| `/trend` | Slope, HAC interval and p-value; separate interpretation and limitations |

Missing, unreadable or invalid sources leave `/health` available with details. Data endpoints
return HTTP 503 with `code`, `message` and optional structured `validation`. Invalid rows,
gaps and duplicates block scientific output. A numerically unestimable trend returns 503 for
`/trend`, while valid descriptive data remains available. Fix the source and restart.
Unexpected programming errors are not disguised as missing-data responses.

Validate a specific export without producing processed data:

```powershell
backend/.venv/Scripts/python.exe -m earthscope_backend.importer --verify-baseline data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv
```

Success writes metadata/validation JSON to stdout (exit 0). Failure writes diagnostics to
stderr (exit 2). Raw and processed data directories remain ignored by Git.
Omitting `--verify-baseline` performs generic CSV/data-quality validation only and reports
geographic support as unverified; it does not approve the file for the MVP application.

The reviewed manifest is
`src/earthscope_backend/manifests/gambia_merra2_1991_2025.json`. It identifies the collection,
version, variable, source URL origin/path, area-average service, country shape, selection
bounds, period and approved SHA-256. `identity.py` validates these separately from parsing
and assigns the Gambia label only after all checks pass. Missing/malformed manifests or
identity/checksum mismatches produce structured `dataset_invalid` errors; `/health` remains
available and scientific endpoints return HTTP 503. Independently approved future snapshots
can use separate `DatasetIdentity` objects through trusted backend configuration. Neither a
CSV sidecar, request parameter nor environment data path can override the production identity.

For Vite development, CORS permits exactly `http://localhost:5173` and
`http://127.0.0.1:5173` by default, with GET and OPTIONS preflight support. Credentialed CORS
is disabled. To set production origins, replace the defaults before starting the backend:

```powershell
$env:EARTHSCOPE_CORS_ORIGINS = 'https://app.example.org,https://www.example.org'
```

Use exact HTTP(S) origins without paths, trailing slashes, user credentials or wildcards.
An empty value disables CORS. Invalid configuration fails explicitly. Unapproved origins
receive no `Access-Control-Allow-Origin`; their preflights return 400. Public non-browser
GET behavior and JSON contracts remain unchanged. See the
[FastAPI CORS documentation](https://fastapi.tiangolo.com/tutorial/cors/).

Deployment data must be supplied explicitly: Git ignores `data/raw/` and the wheel contains
no raw CSV. The wheel includes the reviewed JSON manifest as package data, loaded through
`importlib.resources`, independently of the working directory. Ship the approved backend
package/manifest together and provide the exact CSV through a private release artifact or
read-only file mount. Use an absolute `EARTHSCOPE_DATA_PATH` for an installed package, e.g.:

```powershell
$env:EARTHSCOPE_DATA_PATH = 'C:\EarthScopeData\giovanni_merra2_gambia_t2m_1991_2025.csv'
backend/.venv/Scripts/python.exe -m earthscope_backend.importer --verify-baseline
```

Verify the CSV/manifest before release and again at startup. Preserve original CSV bytes,
including metadata/newlines, or the checksum will fail. The JSON manifest is trusted reviewed
package configuration, not a substitute downloaded beside an arbitrary CSV. New data revisions
require separate reviewed identities. No NASA credentials/network are required for startup.
No raw files are published and no deployment infrastructure is changed by these instructions.

Run the quality gate and independent scientific audit from the repository root:

```powershell
backend/.venv/Scripts/python.exe --version
backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests
backend/.venv/Scripts/python.exe -m ruff check backend
backend/.venv/Scripts/python.exe -m ruff format --check backend
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe backend/scripts/independent_trend.py data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv
```

The full suite requires the actual local NASA CSV. Integration tests fail explicitly if it is
absent; they do not skip or substitute fabricated data. Use `-m 'not integration'` only for
isolated synthetic unit/API work. Integration tests independently recompute scientific values
from observations instead of asserting a hardcoded slope or p-value.

Architecture: `config.py` resolves the source; `importer.py` validates it into immutable
observations and provenance; `identity.py` verifies approved source identity; `analysis.py`
computes summaries and inference; `schemas.py`
defines finite JSON contracts; `main.py` loads a snapshot and serves cached results.
`scripts/independent_trend.py` supplies an independent numerical audit. See
[methods](../docs/backend-methods.md) and [validation report](../docs/backend-validation.md).
