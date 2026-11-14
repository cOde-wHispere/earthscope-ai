# Phase 1B Technical Lead review report

Team CO2 - EarthScope AI | 2026-11-14 | `feat/scientific-backend`

**Both findings corrected. Uncommitted; awaiting Technical Lead approval.**

## Geographic identity

The reviewed manifest at
`backend/src/earthscope_backend/manifests/gambia_merra2_1991_2025.json` defines the dataset
ID, provider, collection/version, variable, native units, trusted Giovanni URL origin/path,
`ArAvTs` service, `state_dept_countries_2017/shp_85` shape, selection bounds, period and
approved SHA-256:

```text
b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0
```

`identity.py` checks parsed data against this manifest before startup computes or exposes
scientific results. It validates the exact Giovanni `data` parameter and CSV value column,
rejects ambiguous/duplicate identity parameters, checks source origin/path, processing,
shape, URL/metadata bounds, coverage and digest. A failure produces `dataset_invalid` with
structured `validation.issues` codes, degraded health and HTTP 503 from data endpoints.
Missing/malformed packaged manifests also fail safely with `manifest_invalid`.

The generic parser contains no approved NASA checksum and reports geographic support as
unverified. The Gambia label is assigned only after identity verification. Changing
`EARTHSCOPE_DATA_PATH`, renaming a file or supplying a CSV sidecar does not approve new bytes.
Trusted backend code can explicitly supply a separately reviewed `DatasetIdentity` for a
future supported snapshot; that does not change the pinned production default. There is no
request parameter or environment variable that overrides the baseline manifest.

This verifies the approved export's identity; it does not independently reconstruct NASA's
spatial mask or weights. The existing scientific assumptions and limitations remain applicable.

## Frontend access

`CORSMiddleware` permits exactly `http://localhost:5173` and `http://127.0.0.1:5173` by
default. `EARTHSCOPE_CORS_ORIGINS` accepts comma-separated exact HTTP(S) origins and replaces
those defaults. Empty disables CORS; wildcard, path, credentials and malformed-port entries
fail explicitly. For example:

```powershell
$env:EARTHSCOPE_CORS_ORIGINS = 'https://app.example.org,https://www.example.org'
```

Only GET is allowed, with middleware handling OPTIONS preflight. Credentials are disabled;
there are no wildcard origins, methods or headers. Unapproved origins receive no
`Access-Control-Allow-Origin`; their preflights return 400. Existing public GET/status/JSON
contracts remain intact. Allowed browser origins can also read structured 503 responses.
This follows the [FastAPI CORS interface](https://fastapi.tiangolo.com/tutorial/cors/).

## Deployment readiness

The backend wheel includes the reviewed manifest using setuptools package data and loads it
with `importlib.resources`. It contains no raw CSV or environment files. Supply the exact
approved CSV separately through a private release artifact or read-only mount, and set an
absolute `EARTHSCOPE_DATA_PATH`; the installed package must not depend on repository layout.
Keep the manifest with the trusted backend release, not an untrusted replacement beside a CSV.
Preserve the original source bytes, including metadata/newlines, and verify before release:

```powershell
backend/.venv/Scripts/python.exe -m earthscope_backend.importer --verify-baseline
```

This command succeeded against the local NASA file (exit 0, valid identity and unchanged
checksum). Omitting the flag performs generic data-quality validation without geographic
approval. Startup independently repeats the identity check. No network/NASA credentials are
required. No raw data was published and no deployment infrastructure was changed.

## Quality gate: exact commands and observed outputs

All commands used the existing isolated Python 3.13 environment, from the repository root:

```powershell
backend/.venv/Scripts/python.exe --version
# Python 3.13.17

backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests
# collected 112 items
# ======================= 112 passed, 1 warning in 22.80s =======================

backend/.venv/Scripts/python.exe -m ruff check backend
# All checks passed!

backend/.venv/Scripts/python.exe -m ruff format --check backend
# 18 files already formatted

backend/.venv/Scripts/python.exe -m pip check
# No broken requirements found.

git diff --check
# No whitespace errors; exit 0.
```

All final checks exited 0. The suite retains the original 63 cases and adds 49 cases,
including nine total NASA integration cases. Synthetic API fixtures now declare explicit
test identities, URL and bounds rather than bypassing the production validator. Tests cover
altered shape, collection/version, variable, service, source host/path and bounds, duplicate
parameters, missing/malformed manifest, checksum mismatch, separate reviewed revisions,
renamed approved copies, CLI failure output, CORS defaults/production overrides/preflight,
blocked origins/methods/headers and unchanged response schemas/payloads.

One remaining warning, unchanged from Phase 1:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

It was also emitted by the wheel startup smoke check and was not suppressed. Dependencies
and their lock remain unchanged, including the previously documented transitive wrapt
prerelease. Pip's wheel command emitted an upgrade notice (26.2.2 -> 26.3); no upgrade was
performed. Git still emits its pre-existing `.gitignore` LF-to-CRLF advisory.

During development, the expanded CLI rejection test caught an error path: under
`python -m earthscope_backend.importer`, duplicate module exception classes let identity
errors escape the handler (111 passed, 1 failed, 1 warning in 23.36s). CLI handling moved
to `cli.py`, preserving the existing command/entry point and structured exit-2 diagnostics.
The final complete run above passes. No test failures remain.

## Independent NASA audit

Exact command:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/independent_trend.py data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv
```

Observed output (exit 0):

```json
{
  "source_sha256": "b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0",
  "n_observations": 420,
  "design_rank": 13,
  "residual_degrees_of_freedom": 407,
  "slope_celsius_per_decade": 0.009139123951911188,
  "standard_error_celsius_per_decade": 0.07045062410991833,
  "ci95_lower": -0.12935339895614636,
  "ci95_upper": 0.14763164685996874,
  "p_value": 0.8968490236598302,
  "hac_maxlags_months": 12,
  "method": "NumPy lstsq; manual Bartlett HAC with n/(n-k) correction; Student-t",
  "minimum_celsius": 21.222253000000023,
  "maximum_celsius": 33.061639000000014,
  "mean_celsius": 27.644393633333355
}
```

The result is unchanged: **no statistically significant trend detected** under the existing
method. No scientific calculation or interpretation rule changed. Hash comparisons confirmed
`analysis.py`, its tests, `independent_trend.py` and the NASA CSV are byte-for-byte unchanged.

## Local package verification

```powershell
backend/.venv/Scripts/python.exe -m pip wheel --no-deps --wheel-dir backend/.venv/review-wheels ./backend
```

Observed: `Successfully built earthscope-backend` (exit 0). Final wheel:
`earthscope_backend-0.1.0-py3-none-any.whl`, 16,207 bytes, SHA-256
`0573afd2824cc7baf004bc8660625730bd33cf5ce02b8b4cdba715fdabe883f4`.

A separate Python ZIP/import-resource smoke check inspected the archive, imported the
backend directly from that wheel, set an absolute source path and exercised startup/CORS:

```text
Wheel manifest and CLI present; raw CSV/data and .env files absent.
Wheel resource loading, approved baseline startup and CORS: passed.
```

It exited 0. The wheel stays in ignored `backend/.venv/review-wheels`; temporary
`backend/build` output was removed after verifying its absolute workspace path. Nothing was
published or installed into a deployment target.

## Review scope and handoff

New files (6): `identity.py`, `cli.py`, the approved JSON manifest, `test_identity.py`,
`test_cors.py` and this report. Modified existing files (12): backend `config.py`,
`importer.py`, `main.py`, `schemas.py`, `pyproject.toml`, `.env.example`, `README.md`, tests
`conftest.py`, `test_api.py`, `test_cli.py`, `test_importer.py` and `docs/backend-methods.md`.

Branch remains `feat/scientific-backend`. Earlier uncommitted work is retained; because the
backend was already untracked, ordinary Git diff does not show these edits relative to Phase 1.
The full working tree contains `.gitignore` modified and 26 untracked files, nothing staged.
The phase-specific inventory above comes from before/after file hashes.

Frontend, NASA CSV, trend calculation, independent audit, dependency lock, hybrid proposal
and original validation report were unchanged. No live NASA access, commit, merge, push,
publication or deployment was performed. Stop here for Technical Lead approval.
