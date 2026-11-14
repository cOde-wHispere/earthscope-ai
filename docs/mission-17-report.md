# Mission 17: multi-variable backend review report

Team CO2 / EarthScope AI / 2026-11-14

**Implementation and verification complete; awaiting Technical Lead review.**
Local changes are uncommitted on `feat/multivariable-backend`, created from clean
`main` at `4cb8ea56077edbbc0a4af33fd23088980445e26c`. HEAD remains at that commit.
No commit, push, merge or deployment was performed. Temporary local verification
servers have been stopped.

## Delivered behavior

- Independent per-dataset registry with five additional packaged approved manifests.
  T2M reuses its original manifest, importer, identity validator and startup snapshot.
- Additive GET `/v2/datasets`, `/v2/datasets/{id}/metadata`,
  `/v2/datasets/{id}/timeseries/monthly`, and
  `/v2/datasets/{id}/timeseries/annual` routes, with explicit finite typed schemas.
- All six local originals verified: 420 ordered monthly observations and 35 complete
  years each, January 1991 through December 2025. No missing/duplicate/unexpected
  months, sentinel observations or invalid values were found in the originals.
- PRECTOTCORR monthly mean flux is multiplied by 86,400 seconds and Gregorian
  calendar-month length to obtain water-equivalent monthly totals; annual output
  sums 12 totals. Leap days are included.
- QV2M converts kg/kg to g/kg. U10M/V10M retain signed m/s components. PS exported
  hPa values remain unchanged; native product Pa is recorded separately.
- New state-variable annual means use calendar-day weights. T2M preserves its
  existing equal-month means, Celsius conversion, climatology, anomalies and inference.
- Separate missing/invalid/unavailable states and structured errors for each dataset.
  Invalid additional sources or manifests do not disable T2M or other valid sources.
  T2M failure also leaves valid additional datasets available.
- Original preambles, metadata, source identity, unit assumptions, sentinels,
  selection-bound limitations and SHA-256 provenance are exposed. No new statistical
  inference is provided; `/v2` has no trend routes.

The [API and deployment contract](multivariable-api.md) describes units, methods,
validation screens, response fields, errors, configuration and release requirements.

## Verification results

Commands ran from the repository root using Windows Python 3.13.17 and the existing
virtual environment. No runtime dependencies or lockfiles were replaced.

| Exact command | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests` | **224 passed**, 1 warning, 64.99 s; all original 112 regressions plus 112 new cases |
| `backend/.venv/Scripts/python.exe -m ruff check backend` | Exit 0, `All checks passed!` |
| `backend/.venv/Scripts/python.exe -m ruff format --check backend` | Exit 0, `27 files already formatted` |
| `backend/.venv/Scripts/python.exe -m pip check` | Exit 0, `No broken requirements found.` |
| `backend/.venv/Scripts/python.exe -m earthscope_backend.importer --verify-baseline` | Exit 0; original T2M identity and 420-observation validation passed |
| `backend/.venv/Scripts/python.exe backend/scripts/independent_trend.py data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv` | Exit 0; independent NumPy/manual HAC audit passed; original integration tests compare slope, standard error, CI and p-value |
| `backend/.venv/Scripts/python.exe backend/scripts/independent_multivariable.py data/raw` | Exit 0; six approved hashes, 420 months and 35 complete years each |
| `backend/.venv/Scripts/python.exe backend/scripts/verify_wheel.py` with isolated build-tool `PYTHONPATH` described below | Exit 0; wheel import, 6 ready datasets, 18 successful `/v2` resource responses and successful legacy `/trend`; 6 manifests, 0 CSVs packaged |
| `git diff --check` | Exit 0 |
| `git diff --cached --exit-code` | Exit 0; nothing staged |

The new tests cover each conversion and engineering screen, declared sentinels,
nonfinite/nonnumeric observations, signed/zero wind components, PS unit mistakes,
Gregorian leap/century years, precipitation annual sums, weighted means, complete
distinct-month years, ordering, gaps, duplicates, unexpected months, timestamp/row
errors, URL identity/duplicate parameters, provenance, checksum mismatches, malformed
individual manifests, missing/read-denied sources, independent failures, immutable
startup snapshots, restart validation and unsupported routes. Integration tests use
all six actual local exports and compare every monthly and annual value against
the independent Decimal audit. Originals are never modified by tests; failure
injection changes temporary copies or mocks reads.

The original six endpoint responses were hashed before and after implementation
using SHA-256 over `json.dumps(response.json(), sort_keys=True).encode()`.
Every hash matched, including all statistical outputs and original metadata:

| Endpoint | Unchanged canonical-response SHA-256 |
| --- | --- |
| `/health` | `69f45886ddbbe46df84965fefb462fab3d42cb89da3410cf3930dc54f5f6a88e` |
| `/metadata` | `c8031a89a83ad617bbc1fa01d289500d1a2b10e4e26e05ede6e3331a0525641d` |
| `/timeseries/monthly` | `6ea8013ec06683f048c57157e9782eb32f1d0218e8dccfba0b184cb6195b7c9d` |
| `/timeseries/annual` | `b81585e81484d991be3deacf38068754a83ca2f94a3ce699866cf1eec7410e1f` |
| `/climatology` | `d16abe2dbc4a1231fe10133c8099dcc2286ec137c45956cd2824f4eb7c671539` |
| `/trend` | `019b4c95a5fada283b36966175b2e4c8f6019ae8d92d707ef3171269a4e82226` |

### Real HTTP check

Started this temporary local service:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8017 --no-access-log
```

After Uvicorn reported application startup complete, executed:

```powershell
@'
import json,urllib.request
base='http://127.0.0.1:8017'
paths=['/health','/metadata','/timeseries/monthly','/timeseries/annual','/climatology','/trend','/v2/datasets']
for variable in ['T2M','PRECTOTCORR','QV2M','U10M','V10M','PS']:
    paths.extend(f'/v2/datasets/{variable}/{suffix}' for suffix in ['metadata','timeseries/monthly','timeseries/annual'])
for path in paths:
    with urllib.request.urlopen(base+path,timeout=5) as response:
        assert response.status==200
        json.load(response)
print(json.dumps({'real_uvicorn_http_200':len(paths),'port':8017}))
'@ | backend/.venv/Scripts/python.exe -
```

Exit 0: `{"real_uvicorn_http_200": 25, "port": 8017}`.
The temporary server's process IDs were verified before stopping. Subsequent process
inspection found no checkpoint Uvicorn process, and a TCP probe could not connect
to port 8017.

### Investigated failures and environmental details

- First new-test run: **109 passed, 2 failed**, 1 warning, 40.38 s, from:
  `backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests/test_multivariable.py backend/tests/test_multivariable_integration.py`.
  One synthetic test doubled PS beyond the intended validation screen; its fixture
  was corrected to an in-range variation. Another expected ENOTDIR/unavailable for
  a file used as a directory, while Windows reported a missing child. Its assertion
  now accepts the platform-specific classification, and a deterministic injected
  PermissionError separately verifies read-denial behavior. No application rule was
  weakened to satisfy either test. The subsequent full 224-test run passed.
- Early lint runs found formatting/import issues only in new files; these were
  corrected before the passing quality gate.
- First offline wheel attempt failed because `setuptools.build_meta` was absent
  from the existing runtime environment. The local pip HTTP cache contained a
  setuptools **82.0.1** wheel, within the existing `>=80,<83` build requirement.
  Its SHA-256 was `a59e362652f08dcd477c78bb6e7bd9d80a7995bc73ce773050228a348ce2e5bb`.
  It was extracted with archive-path validation into the ignored isolated directory
  `backend/.venv/mission17-build-tools`. No package was installed into site-packages
  and no network download or lockfile change was required. The passing invocation was:

  ```powershell
  $env:PYTHONPATH = (Resolve-Path -LiteralPath backend/.venv/mission17-build-tools).Path
  backend/.venv/Scripts/python.exe backend/scripts/verify_wheel.py
  ```

  The wheel built in a temporary source copy with no dependency installation. The
  child import check used `-I`, the actual wheel first on `sys.path`, an unrelated
  working directory, and absolute original-data paths. The temporary wheel was not
  installed, retained as a release artifact or deployed.
- An initial 45-second subprocess readiness probe timed out before startup logs.
  A separately started Uvicorn instance reached readiness and passed all 25 HTTP
  checks without application changes. Startup performance under production load
  was not benchmarked.
- Sandbox process inspection initially denied CIM access. Scoped inspection with
  execution approval identified only checkpoint server processes. Windows
  `Stop-Process` raised a NullReferenceException; stopping the verified launcher
  through .NET ended the service. A subsequent child-stop attempt raced with its
  exit and reported access denied; reinspection found no checkpoint processes.
- Remaining warning: existing `StarletteDeprecationWarning` about TestClient using
  `httpx` and suggesting `httpx2`. The approved dependency set is preserved;
  this warning does not indicate a failing assertion or production API error.

## Original-file integrity

All six original raw-file byte counts and SHA-256 values matched the initial
inspection and reviewed manifests after verification:

| Variable | Bytes | SHA-256 |
| --- | ---: | --- |
| T2M | 13647 | `b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0` |
| PRECTOTCORR | 15277 | `1ac9ec55d13116f88606037303c9f8bb9d60806620d54a41999e11956781be23` |
| QV2M | 14663 | `13c1ea286bd89b5537b4ef0317bd1079c605d5f3314af1c0a1c7a0e5764ffb43` |
| U10M | 13922 | `a48bb11896167b7bc4174e4c8f13cfb9d67562587e73f8b1de546b79352fd1d2` |
| V10M | 14140 | `380bbbb395be93c7ddc6adfad5b6074498806e40bd642ba4d94476343051f9f6` |
| PS | 13618 | `e71b283c2a848ac1b201b512f612468d839c7cac9f2d40f8c91259ea78b862e0` |

No original observations were rewritten, interpolated, replaced or fabricated.
Raw data remains ignored. All 27 tracked frontend files remain unchanged, including
the npm lockfile. The backend lockfile and pyproject are unchanged. The original
T2M analysis, importer, identity, config, schemas, manifest, CLI, independent trend
audit and all original test files are unchanged. Only additive app wiring and its
module description changed in the original backend Python source.

`git diff --exit-code -- frontend backend/requirements-lock.txt backend/pyproject.toml`
and checks covering all protected T2M modules, original manifest and original tests
returned exit 0. No credentials, raw observations, dependency caches, wheels or
generated files are staged; the index is empty.

## Git status and changed files

Final branch: `feat/multivariable-backend`. HEAD: `4cb8ea5`.
The three existing modified files and all new files are unstaged:

```text
 M backend/.env.example
 M backend/README.md
 M backend/src/earthscope_backend/main.py
?? backend/scripts/independent_multivariable.py
?? backend/scripts/verify_wheel.py
?? backend/src/earthscope_backend/dataset_registry.py
?? backend/src/earthscope_backend/manifests/gambia_merra2_prectotcorr_1991_2025.json
?? backend/src/earthscope_backend/manifests/gambia_merra2_ps_1991_2025.json
?? backend/src/earthscope_backend/manifests/gambia_merra2_qv2m_1991_2025.json
?? backend/src/earthscope_backend/manifests/gambia_merra2_u10m_1991_2025.json
?? backend/src/earthscope_backend/manifests/gambia_merra2_v10m_1991_2025.json
?? backend/src/earthscope_backend/multivariable_importer.py
?? backend/src/earthscope_backend/multivariable_schemas.py
?? backend/src/earthscope_backend/v2.py
?? backend/src/earthscope_backend/variables.py
?? backend/tests/test_multivariable.py
?? backend/tests/test_multivariable_integration.py
?? docs/mission-17-report.md
?? docs/multivariable-api.md
```

## Limits and review points

The CSVs do not themselves declare units, retrieval times or spatial weights. PS
export units rely on the Technical Lead's explicit approval. Precipitation's absent
bounds remain unknown; none were copied from other exports. Monthly area averages
cannot resolve local extremes, daily events or operational conditions. New annual
state-variable weighting is explicitly documented for review. No additional trend
model, uncertainty interval, p-value, forecast or sector recommendation is exposed.

The frontend remains the merged temperature dashboard. No multi-variable frontend
work or browser suite was run in Mission 17; compatibility was checked through
unchanged frontend files, identical legacy responses, the original backend tests
and the real HTTP service. Production deployment, external hosting and a clean
machine installation were not performed. The offline wheel/package resource and
API check passed against the existing validated runtime dependencies.

Review the additive API and manifest assumptions before any further integration or
release action. Work stops here for Technical Lead review.
