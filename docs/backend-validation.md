# Backend implementation and validation report

Review date: **2026-11-14 UTC**. Branch: **feat/scientific-backend**.
Implementation is uncommitted and awaits Technical Lead review.

## Files and architecture

Changed: `.gitignore` (four additions: ignore Python package metadata and the workspace-local
Python runtime).

Created:

```text
backend/.env.example
backend/README.md
backend/pyproject.toml
backend/requirements-lock.txt
backend/scripts/independent_trend.py
backend/src/earthscope_backend/__init__.py
backend/src/earthscope_backend/config.py
backend/src/earthscope_backend/schemas.py
backend/src/earthscope_backend/importer.py
backend/src/earthscope_backend/analysis.py
backend/src/earthscope_backend/main.py
backend/tests/conftest.py
backend/tests/test_importer.py
backend/tests/test_analysis.py
backend/tests/test_api.py
backend/tests/test_cli.py
backend/tests/test_nasa_integration.py
docs/backend-methods.md
docs/backend-validation.md
```

`config` resolves an environment-configurable source. `importer` parses Giovanni metadata
and validates the complete monthly record into immutable observations and provenance.
`analysis` calculates summaries and a joint time/month fixed-effects regression. `schemas`
defines finite response contracts. FastAPI's lifespan loads one snapshot and caches results;
read-only endpoints serve health, metadata, monthly/annual data, climatology and trend.
Structured 503 errors handle missing, unreadable, invalid or unestimable input.
`independent_trend.py` reads the CSV separately and calculates a manual HAC sandwich without
application code or statsmodels. Tests cover both synthetic data and the actual local source.

## Source validation: observed results

Source: `data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv` (13,647 bytes).

```text
SHA-256: b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0
Expected and observed coverage: 1991-01 through 2025-12
Expected rows / observed rows / valid observations: 420 / 420 / 420
Missing months: 0
Duplicate months: 0
Unexpected months: 0
Invalid numeric values: 0
Fill values: 0
Input sorted: true
Validation issues / warnings: 0 / 0
Interpolated observations: 0
Annual means: 35 complete years
Month-of-year climatology: 12 means, 35 observations each
Source metadata entries preserved: 7
```

The same SHA-256 was observed before and after implementation/testing. The source remained
ignored and was not modified. Kelvin conversion uses `C = K - 273.15` without early rounding.
The independently recomputed observed Celsius minimum, maximum and monthly-record mean are
21.222253, 33.061639 and 27.644393633333355 respectively. These describe this source file;
they are not attribution claims or uncertainty estimates.

## Independently computed trend

Joint OLS time trend and month fixed effects, Bartlett HAC through lag 12, covariance
correction `420/407`, two-sided Student-t reference with 407 residual degrees of freedom:

| Quantity | Application (statsmodels) | Independent NumPy/manual HAC audit |
| --- | ---: | ---: |
| Slope, degC/decade | 0.009139123949585493 | 0.009139123951911188 |
| HAC standard error, degC/decade | 0.07045062410996095 | 0.07045062410991833 |
| 95% CI lower, degC/decade | -0.12935339895855583 | -0.12935339895614636 |
| 95% CI upper, degC/decade | 0.1476316468577268 | 0.14763164685996874 |
| Two-sided p-value | 0.8968490236859944 | 0.8968490236598302 |
| Observations / design rank | 420 / 13 | 420 / 13 |

Interpretation, separate from the estimates: **no statistically significant trend detected**
at alpha 0.05 under this model. This does not establish a zero true trend and does not identify
any causal mechanism. The small numerical differences reflect different parameterizations
and numerical linear algebra. Integration tests recompute and compare all five inferential
quantities; no trend slope or p-value is hardcoded into application logic or test expectations.

## Environment setup: exact commands used

The existing system interpreter was Python 3.15.0, and the `py`/`pymanager` aliases could not
execute. The Python 3.13 runtime was downloaded into the ignored workspace directory using
the [Python-documented NuGet distribution](https://docs.python.org/3.13/using/windows.html#the-nuget-org-packages).
The commands below ran from the repository root, except the dependency install explicitly
ran from `backend`:

```powershell
New-Item -ItemType Directory -Force backend/.python-runtime | Out-Null
curl.exe --fail --location --max-time 90 https://www.nuget.org/api/v2/package/python/3.13.17 --output backend/.python-runtime/python.3.13.17.zip
Expand-Archive -LiteralPath backend/.python-runtime/python.3.13.17.zip -DestinationPath backend/.python-runtime/python313
backend/.python-runtime/python313/tools/python.exe --version
backend/.python-runtime/python313/tools/python.exe -m venv backend/.venv
backend/.venv/Scripts/python.exe --version
```

Both version commands reported **Python 3.13.17**; environment creation exited 0.
From the `backend` working directory:

```powershell
.venv/Scripts/python.exe -m pip install -e '.[dev]'
```

Result: exit 0; backend and runtime/development dependencies installed. Direct dependencies
are bounded in `pyproject.toml`; the exact tested environment is captured with:

```powershell
backend/.venv/Scripts/python.exe -m pip freeze --exclude earthscope-backend | Set-Content -Encoding ascii backend/requirements-lock.txt
```

Key resolved versions: FastAPI 0.162.7, Pydantic 2.14.3, NumPy 2.5.4, SciPy 1.18.1,
statsmodels 0.15.0, Uvicorn 0.54.0, pytest 9.2.0, Ruff 0.17.5.
The lock includes upstream transitive `wrapt==2.6.0.dev1`; it is retained transparently as
part of the tested environment. It is not a direct application dependency.

## Quality gate: exact commands and observed results

Commands from the repository root:

```powershell
backend/.venv/Scripts/python.exe --version
backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests
backend/.venv/Scripts/python.exe -m ruff check backend
backend/.venv/Scripts/python.exe -m ruff format --check backend
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe -m earthscope_backend.importer
backend/.venv/Scripts/python.exe backend/scripts/independent_trend.py data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv
git diff --check
```

| Check | Final observed result |
| --- | --- |
| Python | Python 3.13.17 |
| pytest | **63 passed, 1 warning in 14.29s**, exit 0; includes 3 NASA integration tests |
| Ruff check | `All checks passed!`, exit 0 |
| Ruff format | `14 files already formatted`, exit 0 |
| pip check | `No broken requirements found.`, exit 0 |
| Importer CLI | Complete valid metadata/validation JSON, exit 0 |
| Independent audit | Numeric results above, exit 0 |
| git diff --check | No whitespace errors, exit 0; Git emitted its configured LF-to-CRLF notice |

The remaining pytest warning is Starlette's deprecation of its HTTPX-based TestClient in
favor of `httpx2`. API tests and the real Uvicorn smoke test pass. The warning is not suppressed.

Failure history: an early command ran before dependency installation finished and could not
import pytest. Initial Ruff found 14 formatting/unused-variable issues, all corrected. The
first completed pytest run had **61 passed, 1 failed, 1 warning in 26.66s**: a metadata test
assumed LF while Windows wrote CRLF inside a quoted field. The importer correctly preserved
the original CRLF. The fixture now writes exact bytes and tests both LF and CRLF, producing
the final 63-test passing run. No failures remain.

## Live localhost smoke test

Started from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8765
```

Uvicorn reported application startup complete. `Invoke-RestMethod` requests to `/health`,
`/trend`, `/timeseries/monthly` and `/timeseries/annual` returned HTTP 200. Health was
`ok`/`ready`; trend output matched the application column above; counts were 420 monthly
and 35 annual observations, bounded by 1991-01-01 and 2025-12-01. The temporary smoke-test
server was stopped after verification.

## Scientific limitations

The source is a reanalysis. The country's shape is narrow relative to the native grid;
spatial aggregation/weights and Kelvin units cannot be independently established from the
CSV alone. Annual means weight months equally. The 1991–2025 climatology is a full-record
baseline, not a standard 30-year normal. A linear trend with fixed seasonality can miss breaks
or nonlinear/evolving seasonal changes. Lag-12 HAC assumes weak residual dependence;
longer-memory and lag-sensitivity checks remain future work. Its interval excludes reanalysis
structural, measurement and spatial aggregation uncertainty. See [methods](backend-methods.md).

## Run locally and Git handoff

With the prepared environment, from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs. For setup, locked installation and optional
`EARTHSCOPE_DATA_PATH`, see [backend instructions](../backend/README.md).

Git diff summary: **1 tracked file modified (`.gitignore`, +4/-0), 19 new untracked files**
listed above. New files are not included in ordinary `git diff --stat` until staged.
Nothing is staged. Working-tree status for review:

```text
## feat/scientific-backend
 M .gitignore
?? backend/.env.example
?? backend/README.md
?? backend/pyproject.toml
?? backend/requirements-lock.txt
?? backend/scripts/independent_trend.py
?? backend/src/earthscope_backend/__init__.py
?? backend/src/earthscope_backend/analysis.py
?? backend/src/earthscope_backend/config.py
?? backend/src/earthscope_backend/importer.py
?? backend/src/earthscope_backend/main.py
?? backend/src/earthscope_backend/schemas.py
?? backend/tests/conftest.py
?? backend/tests/test_analysis.py
?? backend/tests/test_api.py
?? backend/tests/test_cli.py
?? backend/tests/test_importer.py
?? backend/tests/test_nasa_integration.py
?? docs/backend-methods.md
?? docs/backend-validation.md
```

The frontend and raw NASA CSV were unchanged. Raw data, runtime, virtual environment and
Python build artifacts remain ignored. No database, authentication, Docker, chatbot or cloud
service was added. No commit, push, merge, deployment, remote or visibility change was made.
