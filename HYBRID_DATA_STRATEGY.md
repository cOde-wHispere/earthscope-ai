# EarthScope AI - Hybrid NASA Data Strategy

Team CO2 | 2026-11-14 | **Proposal: awaiting Technical Lead approval**

**Decision:** retain the validated Giovanni MERRA-2 country-average export as the
MVP baseline with offline access. Add optional server-side NASA retrieval and validated,
matching snapshots. NASA POWER point exploration is a separate dataset mode. A point,
bounding-box average and country-shape average must never substitute for one another.

## 1. Already implemented

- `backend/src/earthscope_backend/importer.py`: Giovanni metadata, SHA-256, Kelvin conversion,
  exact coverage and rejection of invalid/fill values, duplicates and gaps; no interpolation.
- `analysis.py`: monthly/annual series, climatology/anomalies and month-fixed-effects OLS
  with lag-12 HAC uncertainty; observations and interpretation are separate.
- `main.py`, `schemas.py`, `config.py`: read-only FastAPI endpoints, immutable startup
  results, provenance hashes, `EARTHSCOPE_DATA_PATH` and structured failure responses.
- Synthetic/API tests and independent NASA integration audit; the existing
  [validation report](docs/backend-validation.md) records 63 passing tests.

The baseline is 420 months, January 1991-December 2025, product M2IMNXASM v5.12.4,
variable T2M, shape `state_dept_countries_2017/shp_85`. Its raw-file SHA-256 is
`b12cd5e3321e160269cc951448a094905529aaff1355c493ffaedde1278539e0`.
Missing: remote adapters, persistent snapshots, refresh, structured provider/geographic
support, retrieval date and live/cache status.

## 2. Reuse unchanged

Keep the baseline CSV, Giovanni importer, conversion/coverage helpers, existing MERRA-2
analysis, API behavior and regression tests. Wrap the baseline with additional provenance.
Keep the source hash and independent audit as reproducibility checks.

`Dataset` uses Kelvin observations; metadata, responses and limitations contain
MERRA-2/1991-2025 defaults. These are **not provider-neutral**. POWER needs its own decoder,
neutral representations and parameterized explanatory metadata before reusing the statistical
formulas. Do not manufacture Giovanni CSV or inherit misleading MERRA-2 labels.

## 3. Required contract, adapter and cache interfaces

Introduce a versioned provenance envelope; preserve the existing baseline contract during
migration. Each scientific response identifies one immutable snapshot and its metadata.

| Contract field | Required meaning |
| --- | --- |
| `dataset_id`, `mode`, `provider`, `product`, `version`, `variable` | Distinguish NASA GES DISC/Giovanni country data from NASA POWER point data. |
| `native_units`, `output_units`, `conversion`, `units_basis` | Preserve provider units; normalize once to degC. Reject unsupported units. |
| `geographic_support` | Typed `country_shape_average`, `bounding_box_average` or `point`; CRS, geometry/shape ID and version/hash, selection bounds, aggregation/masking/weighting method, native grid and actual selected cell where applicable. Unknown details remain explicit. |
| `requested_period`, `observed_period`, `frequency`, `expected_count` | Monthly coverage and completeness; also record the climatology reference period. |
| `retrieved_at`, `validated_at` | Separate UTC timestamps. The legacy export's retrieval date is unknown: use null plus an explicit unknown status, never file mtime or today's date. |
| `delivery`, `cache_origin`, `freshness`, `refresh_error` | `live` or `cache`; bundled baseline/runtime snapshot; fresh/stale/unknown/not-applicable; sanitized fallback reason. |
| `snapshot_id`, raw/payload hashes, validation/method versions | Bind every summary and trend to the same validated observations, provenance and processing rules. |

Proposed interfaces, not implemented APIs:

| Interface | Responsibility |
| --- | --- |
| `DatasetSpec` | Canonical scientific identity: provider/product/version, variable/statistic, units, frequency/period, geographic support and relevant grid/community/elevation/time settings. |
| `SourceAdapter.fetch(spec) -> Candidate` | `GiovanniFileAdapter` wraps the importer; optional `Merra2RemoteAdapter` and `PowerPointAdapter` preserve raw responses, request provenance and actual retrieval time. No cache writes. |
| `validate(candidate, spec) -> ValidatedSnapshot` | Provider-specific decoding plus common completeness/unit/value checks; reject identity mismatches. POWER decoding separates monthly records from annual summaries and uses its declared fill value. |
| `SnapshotStore.get_exact(spec)` / `publish(validated)` | Read matching snapshots; publish immutable raw payload + manifest + normalized observations + validation report. |
| `DatasetResolver.resolve(spec, policy)` | Baseline by default; explicit opt-in live retrieval; fall back only to a valid snapshot with the identical scientific identity. |

Key caches by a canonical `DatasetSpec` hash; version snapshots separately. Stage and validate
the entire result and derived outputs, then atomically publish the bundle/pointer with writer
serialization/version checks. Readers retain complete snapshots. Keep the pinned baseline
immutable and retain the previous good revision. Invalid, partial or mismatched responses never
replace either. Changed values create reviewed revisions. Refresh outside request handling;
initially activate snapshots on restart.

## 4. API feasibility and authentication risks

**MERRA-2:** investigate CMR and current GES DISC/Harmony services. The Giovanni reproduction
URL does not establish a stable API; NASA documents a 2026 migration away from legacy endpoints. [NASA migration guidance](https://github.com/nasa/gesdisc-tutorials/blob/main/user-guidance/GES_DISC_Migration_to_Earthdata_Website_and_Earthdata_Cloud.md).

Harmony requires Earthdata Login and supports asynchronous jobs. Its documented Giovanni
averaging service lists bounding-box support but no shape support; capabilities are also
collection-specific. **Country-shape equivalence is unproven.** Require demonstrated
M2IMNXASM/T2M availability, complete 1991-2025 coverage, matching geometry/mask/weights and
numerical comparison within a scientifically justified tolerance before enabling substitution.
Otherwise retain manual Giovanni exports. A clipped grid alone is not an area mean. [Harmony authentication and capabilities](https://harmony.earthdata.nasa.gov/docs/).

**POWER:** monthly point examples omit credentials; verify unauthenticated access, units,
coverage and actual grid support in a bounded spike. Shared MERRA-2 ancestry does not make
point values equivalent to country averages. Regional output is not automatically an area
average. [POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/).

Use provider-specific authentication; a generic NASA API key is not Earthdata authorization.
Keep any credentials in server-side runtime configuration, outside code, browser bundles,
responses and logs. Bound timeouts, job polling and retries; handle 401/403, redirects,
schema changes, 429 and outages. POWER documents 422/429 responses; honor `Retry-After`
when supplied. [POWER API errors](https://power.larc.nasa.gov/docs/services/api/).
No authenticated retrieval or numerical provider-equivalence test was performed for this proposal.

## 5. Deployment data packaging

Git-ignored `data/raw/` and `data/processed/` are absent from a checkout/backend wheel.
Supply a separate artifact: original CSV, pinned checksum, provenance manifest and validation
report. Verify presence/checksum during packaging/startup; mount/copy read-only and set an
absolute `EARTHSCOPE_DATA_PATH`, independent of the installed package layout.

Offline startup must work without NASA credentials or network access. Optional refreshed
snapshots need a separate writable, persistent directory with bounded retention; preserve the
baseline and last good snapshot across restarts. If persistence is unavailable, run baseline
only. No deployment, data publication, database or cloud infrastructure is part of this proposal.

## 6. Testing and fallback acceptance criteria

- Existing baseline tests/audit still pass; packaged CSV bytes and baseline scientific
  results remain unchanged. CI supplies the ignored integration artifact explicitly.
- Adapter fixtures exercise correct units/conversion, provider fill values, invalid numbers,
  exact ordering/coverage, duplicates, partial responses and annual-summary separation.
- Point/country/bounding-box, product/version, period or processing-setting mismatches
  cannot share cache entries or trigger cross-provider fallback.
- Timeouts, auth failures, login HTML with HTTP 200, 429/5xx, incomplete jobs and schema
  changes leave the previous snapshot bytes/pointer intact. Fault injection covers interrupted
  writes, corrupt manifests, disk-full/read-only storage and concurrent refreshes.
- Valid fallback returns HTTP 200 with truthful provenance and refresh-failure status;
  preserve its retrieval date. Historical baselines are not stale merely because they are old;
  define freshness per dataset. Credentials never enter public output or recorded fixtures.
- Offline restart serves the bundled baseline or an exact validated cache. A new point request
  without matching cache returns a structured unavailable response; it never substitutes
  country data. Missing/corrupt baseline and cache retain degraded health plus data HTTP 503.
  Ordinary tests are deterministic/offline; opt-in provider smoke tests establish access only.

## 7. Smallest safe sequence after approval

1. Pin the baseline manifest and packaging checks; approve provenance/identity contracts.
2. Add the local adapter, exact-match file store and resolver in baseline-only mode;
   demonstrate offline startup, atomic publication and fallback tests.
3. Run a bounded MERRA-2 capability/authentication/equivalence spike. Retain manual country
   exports if equivalence cannot be established; POWER remains a separate option.
4. Enable optional server-side MERRA-2 refresh behind a disabled-by-default setting only
   after the spike and acceptance criteria pass; retain revision review and rollback.
5. Generalize provider-specific metadata, then add POWER point exploration under an explicit
   separate route/mode and cache namespace. Keep country baseline selection unchanged.

Approval requested: this sequence, provenance contract, packaging ownership and the rule that
remote country substitution remains blocked until equivalence is demonstrated. This document
changes no application code and authorizes no implementation or deployment by itself.
