# Mission 17: verified descriptive dataset API

The six approved local Giovanni exports cover The Gambia, January 1991 through
December 2025. Each contains 420 monthly area averages and 35 complete years.
The existing temperature API, identity manifest, importer, calculations, inference
and JSON schemas are preserved. Mission 18 adds the six-variable frontend described
in the [frontend guide](../frontend/README.md) and [review report](mission18-review.md).

`/v2` is additive. It exposes discovery, provenance and descriptive monthly/annual
series. It does not expose trends, significance tests, confidence intervals,
climatologies or anomalies for the additional variables. The approved T2M
inference remains available only through the existing `/trend` contract.

## Endpoints and contracts

All routes are read-only GET requests, with finite JSON numbers. OpenAPI at
`/openapi.json` and Swagger at `/docs` describe the full Pydantic contracts.

| Endpoint | HTTP 200 response |
| --- | --- |
| `/v2/datasets` | `datasets`: six catalog entries with readiness, expected checksum, units and resource URLs |
| `/v2/datasets/{id}/metadata` | Verified identity, source/export units, conversions, aggregation, original metadata/preamble, checksum and validation |
| `/v2/datasets/{id}/timeseries/monthly` | Converted values alongside original exported values and month lengths |
| `/v2/datasets/{id}/timeseries/annual` | Complete-year descriptive aggregates with units and explicit method |

IDs are case-sensitive: `T2M`, `PRECTOTCORR`, `QV2M`, `U10M`, `V10M`, `PS`.
Requests cannot select other countries, products, periods, source files or units.
Catalog IDs are short variable identifiers; `dataset_id` is the full reviewed
snapshot identifier. The catalog always includes all six approved slots, including
unavailable ones. `dataset_id` and `expected_source_sha256` are null if the relevant
packaged manifest cannot be validated. These fields never approve unverified bytes.

The catalog includes `id`, `dataset_id`, `label`, `status`,
`expected_source_sha256`, `monthly_units`, `annual_units`, `metadata_url`,
`monthly_url`, `annual_url`, `statistical_inference`, `approved_legacy_trend_url`
and `error`. Status is `ready`, `missing`, `invalid` or `unavailable`. Only T2M
links to `/trend`; `statistical_inference` is `Not provided by /v2` throughout.

Monthly responses contain `dataset_id`, `variable`, `source_sha256`, `units`,
`source_units`, `conversion` and `observations`. Each observation contains:

```typescript
{ time: string; source_value: number; value: number; days_in_month: number }
```

`time` is an ISO month-start date. `source_value` is the original parsed CSV
number in exported units; `value` is the converted display value. Source bytes
are preserved separately and are never rewritten by the service.

Annual responses contain `dataset_id`, `variable`, `source_sha256`, `units`,
`aggregation`, `method` and `observations`. Each observation contains:

```typescript
{ year: number; value: number; months: 12 }
```

Metadata includes a reviewed `identity` manifest, source filename/checksum,
`product_native_units`, `exported_units`, monthly/annual units, `units_basis`,
conversion, aggregation/method, value column, fill value, engineering screen,
original `source_metadata` entries, `raw_preamble`, `validation`, and limitations.
Retrieval time and spatial weights are explicitly unknown in those limitations.
The original bytes' SHA-256 binds metadata and both descriptive series.

## Units and aggregation

Native product units follow the
[NASA MERRA-2 File Specification, version 1.1](https://gmao.gsfc.nasa.gov/media/publications/zbly36ziNFDFbmYmvhQeVqPhUo/Bosilovich785.pdf).
The CSVs have no explicit units field. Product assumptions are recorded in the
reviewed manifests; PS additionally records the Technical Lead's approved export
unit instruction. Plausible values alone do not establish a scientific identity.

| Variable / collection v5.12.4 | Exported units | Monthly output | Annual aggregate |
| --- | --- | --- | --- |
| T2M / M2IMNXASM | K | `degC = K - 273.15` | Equal-weight arithmetic mean of 12 monthly Celsius values, `degC` |
| PRECTOTCORR / M2TMNXFLX | kg m-2 s-1 | Flux × 86,400 × calendar days, `mm/month` | Sum of the 12 monthly totals, `mm/year` |
| QV2M / M2IMNXASM | kg/kg | Source × 1,000, `g/kg` | Calendar-day-weighted mean, `g/kg` |
| U10M / M2TMNXSLV | m/s | Signed eastward component unchanged, `m/s` | Calendar-day-weighted signed mean, `m/s` |
| V10M / M2TMNXSLV | m/s | Signed northward component unchanged, `m/s` | Calendar-day-weighted signed mean, `m/s` |
| PS / M2TMNXSLV | hPa | Exported values unchanged, `hPa` | Calendar-day-weighted mean, `hPa` |

For water-equivalent precipitation, 1 kg/m² corresponds to 1 mm. The monthly mean
flux is integrated using the Gregorian month length, including leap days; it is
not already a monthly depth. Annual totals require all 12 distinct months. This
is total precipitation water equivalent, not a rain-only measurement.

For each new state variable, the annual mean is
`sum(monthly_value * days_in_month) / sum(days_in_month)` over a complete year.
This is an explicit descriptive aggregation choice. T2M retains its approved
equal-month weighting, including identical values under `/v2` and the legacy API.
The PS product is natively specified in Pa, but these approved exported values
are already hPa. Applying another division by 100 would be incorrect.

Specific humidity is not relative humidity. Wind signs are retained, including
zero and cancellation; positive U is eastward and positive V is northward.
No wind speed, gusts, sea temperatures, fishing advice, aviation guidance or
operational safety products are inferred from these monthly area averages.

## Validation and identity

The registry loads five additional independently reviewed JSON manifests from
the backend package. Its T2M entry adapts the original approved manifest and
reuses the original startup dataset and identity validator. It does not pass T2M
through the new importer. Original regression tests and schemas are untouched.

Each identity pins SHA-256, collection/version, variable, filename, units, sentinel,
Giovanni origin/path, service, country shape, period and available selection bounds.
New manifests are not inferred from a CSV, request, environment variable or sidecar.
Changing bytes or approving a later export requires Technical Lead review of a new
trusted identity; changing a data path does not grant approval.

The new importer validates UTF-8 CSV syntax, exact columns, unique metadata,
source URL parameter uniqueness, exact timestamps and coverage, finite values,
dataset-specific sentinels and broad engineering screens. Screens use exported
units and are inclusive: PRECTOTCORR 0..0.01 kg m-2 s-1; QV2M 0..0.1 kg/kg;
U10M and V10M -150..150 m/s; PS 300..1100 hPa. These catch errors and unit mistakes,
not climatological extremes. The original T2M screen remains 150..350 K.
Declared fill values are 1e15 except PS, whose export declares 999999986991104.
Sentinels are rejected before conversion and are never treated as observations.

Missing/duplicate/out-of-period months, invalid rows and checksum mismatches block
the affected dataset. No interpolation, gap filling, clipping or duplicate averaging
is performed. Valid out-of-order input is sorted in memory with a warning; raw
bytes remain intact. Annual output requires 12 distinct calendar months per year.

All six exports identify `state_dept_countries_2017/shp_85`. Five declare selection
bounds `[-16.8296, 13.0839, -13.8084, 13.82]`. The precipitation export omits URL
bounds and has an empty User Bounding Box; its `selection_bbox` remains null.
Its manifest explicitly permits its one empty URL separator (`&&`). The new
parser handles that exact reviewed case without relaxing the original T2M parser.
All six Data Bounding Box fields are empty and remain unknown (`data_bbox: null`).
Selection bounds are not substituted for data grid bounds.

## Failures and compatibility

Catalog discovery returns HTTP 200 even when individual datasets fail. Known but
invalid/unavailable dataset resources return HTTP 503 with the existing top-level
`{code, message, validation}` error shape. Validation issues include codes and,
when available, source line/period. Unknown IDs return HTTP 404 with
`code: dataset_not_found`; unsupported methods return 405. No new trend endpoint
is registered. A request such as `/v2/datasets/QV2M/trend` returns 404.

Each dataset is loaded and cached independently at startup. A malformed manifest,
missing file, read denial, invalid observation or identity mismatch in an additional
dataset does not disable T2M or other valid datasets. T2M failure likewise leaves
valid additional datasets available. `/health` retains its existing T2M-specific
meaning and JSON schema. Operators must inspect `/v2/datasets` for six-dataset
readiness; `/health: ok` does not imply all additional datasets are ready.

The existing `/metadata`, `/timeseries/monthly`, `/timeseries/annual`, `/climatology`
and `/trend` contracts remain unchanged. Mission 17 preserved frontend source,
configuration, dependencies and lockfile. Mission 18 uses v2 for the selected
descriptive record and retains approved legacy analysis only for T2M. Backend
contracts and scientific methods remain unchanged.

## Deployment requirements

Use Python 3.13 and the existing locked backend runtime/test dependencies. No new
runtime dependencies are required. No NASA API calls, credentials or network access
are needed to serve these local snapshots. `.env` files are not automatically loaded.

The wheel must include all six JSON manifests. Raw CSVs remain Git-ignored and are
not bundled. Supply their exact original bytes through private release artifacts
or read-only mounts, including preambles and line endings. Use absolute paths for
installed packages; repository-relative paths resolve from the repository root.

```powershell
$env:EARTHSCOPE_DATA_PATH = 'C:\EarthScopeData\giovanni_merra2_gambia_t2m_1991_2025.csv'
$env:EARTHSCOPE_V2_DATA_DIR = 'C:\EarthScopeData'
$env:EARTHSCOPE_CORS_ORIGINS = 'https://app.example.org'
backend/.venv/Scripts/python.exe -m uvicorn earthscope_backend.main:app --host 127.0.0.1 --port 8000
```

`EARTHSCOPE_DATA_PATH` retains its original meaning for both T2M APIs.
`EARTHSCOPE_V2_DATA_DIR` selects the directory containing the five additional fixed
filenames; its default is `data/raw`. A T2M file in that directory does not override
`EARTHSCOPE_DATA_PATH`. Both T2M APIs use the same validated in-memory snapshot.
Exact filenames are listed in the manifests. Existing exact-origin CORS rules apply
to `/v2`. A production frontend may use a same-origin reverse proxy or configure
the approved backend origin as previously documented.

Restart all workers after replacing sources or configuration. Each worker freezes
its startup snapshots; it does not watch files. Deploy matching approved package
and data revisions together, check the complete catalog, then exercise metadata
and both series for each dataset. A checksum error requires restoring approved
bytes or separate review, not bypassing verification.

From the repository root, verification commands are:

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pyproject.toml backend/tests
backend/.venv/Scripts/python.exe -m ruff check backend
backend/.venv/Scripts/python.exe -m ruff format --check backend
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe -m earthscope_backend.importer --verify-baseline
backend/.venv/Scripts/python.exe backend/scripts/independent_trend.py data/raw/giovanni_merra2_gambia_t2m_1991_2025.csv
backend/.venv/Scripts/python.exe backend/scripts/independent_multivariable.py data/raw
backend/.venv/Scripts/python.exe backend/scripts/verify_wheel.py
```

The full suite and both audits require original local data and fail if it is absent.
The additional audit uses Decimal arithmetic without importing application conversion
code. Integration tests compare all monthly and annual values against it.
For the optional offline wheel check, provide `setuptools>=80,<83` in the build
environment first. `verify_wheel.py` uses `--no-index --no-build-isolation --no-deps`,
builds a temporary source copy, verifies manifest inclusion/CSV exclusion, and imports
the wheel in an isolated interpreter from an unrelated directory. It does not install
or deploy the wheel or alter runtime lockfiles.
