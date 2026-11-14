# Scientific methods: first backend phase

## Source and validation

The local NASA Giovanni export contains MERRA-2 **M2IMNXASM v5.12.4**, T2M (2-meter
air temperature), monthly country-shape area averages for The Gambia, January 1991–December
2025. The [NASA product record](https://disc.gsfc.nasa.gov/datasets/M2IMNXASM_5.12.4/summary)
identifies the collection. The CSV's reproduction URL retains the country shape and bounding
box. The preamble and metadata entries are retained; a SHA-256 identifies the exact bytes read.
The CSV does not explicitly declare units: Kelvin is taken from the supplied product
specification and made explicit in the API's `units_basis` field.

The parser uses UTF-8 (optional BOM) and standard CSV parsing, supporting quoted commas
and multiline metadata. It locates `time, mean_M2IMNXASM_5_12_4_T2M` after metadata.
It requires title, declared start/end months and the expected fill-value declaration.
Every row must have two columns, a first-of-month midnight timestamp and a finite number.
`1000000000000000` is a missing-data sentinel, never a temperature. A conservative **150–350 K**
screen catches implausible monthly T2M or wrong units; this is an engineering sanity check,
not an exhaustive scientific quality flag. Native export values and precision are retained.
Conversion is exactly **C = K − 273.15**; there is no early rounding.

Expected coverage is enumerated independently: exactly 420 distinct monthly timestamps.
Missing boundary/internal months, duplicates, unexpected months, malformed rows, invalid
numbers and fill values reject the entire import with structured issues. Invalid measurements
are counted separately from missing timestamps; a timestamp with a fill value is present but
unusable. No interpolation, replacement, duplicate averaging or row dropping occurs. Valid
out-of-order exports are sorted, and this action is recorded in validation warnings.

For the fixed MVP, startup separately checks the reviewed dataset manifest: collection/version,
variable/value column, trusted Giovanni URL origin/path, `ArAvTs` processing service,
`state_dept_countries_2017/shp_85` country shape, selection bounds, period and approved raw-file
SHA-256. Only after all checks pass is the region labelled The Gambia. Generic CSV parsing
does not establish geographic identity and labels it unverified. The manifest is included in
the backend package; the ignored CSV must be supplied separately. Future independently
approved snapshots require separate identities. This approval is file/provenance verification,
not an independent reconstruction of Giovanni's spatial mask or weights. See the backend
README for verification, CORS and deployment packaging instructions.

## Descriptive observations

Monthly data retains native Kelvin and converted Celsius. Annual means are arithmetic
means of all 12 monthly means, weighting each month equally. They are **not** day-weighted
annual means; incomplete years are rejected. Month-of-year climatology is the arithmetic mean
for each calendar month over **1991–2025**, with 35 observations per month. An anomaly is
the month's Celsius value minus that calendar month's climatological mean. This full-record
baseline is descriptive and is not a WMO standard 30-year normal. It is fixed for this phase.

## Trend and uncertainty

For consecutive month index `i = 0, …, n−1`, define `t = i / 120` in decades and fit:

```text
T_i (degC) = intercept + beta * t_i
            + sum(gamma_m * 1[month_i = m], m = February..December) + error_i
```

January is the reference month. The model has 13 parameters. The reported `beta` is directly
in **degrees Celsius per decade**. This fits temperature and seasonal effects jointly;
it does not regress precomputed anomalies on an unadjusted time index.

Ordinary least squares estimates coefficients. Uncertainty uses the
[statsmodels HAC interface](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html)
with explicit `maxlags=12`, `kernel='bartlett'`, `use_correction=True`, `use_t=True`.
At lag `l`, the Bartlett weight is `1 − l / 13`. Lag 12 initially allows residual covariance
through one year; this is a documented design choice, not an optimized or empirically proven
cutoff. The sandwich covariance is multiplied by `n / (n − 13)`.

The 95% confidence interval is `beta ± t(0.975, n−13) * SE_HAC(beta)`. The two-sided p-value
tests `beta = 0` against a Student-t reference with `n−13` degrees of freedom (407 here).
This is an approximate finite-sample reference for asymptotic HAC inference. The model requires
consecutive monthly observations, full rank, at least 24 observations and positive, finite
uncertainty. An effectively perfect fit produces an explicit analysis error.

The interpretation reports a statistically significant warming or cooling trend only when
`p < 0.05`; otherwise it says **"no statistically significant trend detected."** A nonsignificant
result does not demonstrate that the true slope is exactly zero. Numerical observations and
interpretation occupy separate API fields. The analysis does not infer causation or forecast.

The independent audit reads the raw CSV separately, fits 12 month-specific intercepts and time
in months using NumPy least squares, constructs the Bartlett sandwich by matrix products,
scales the slope and standard error by 120, and obtains inference from SciPy. It imports
neither application importer/analysis code nor statsmodels. Integration tests compare the slope,
standard error, both interval endpoints and p-value across these implementations.

## Assumptions and limits

MERRA-2 combines a physical model and assimilated observations; it is not a direct country-wide
thermometer record. The country is narrow relative to the native 0.5° × 0.625° grid. The CSV
cannot independently validate Giovanni's spatial mask, spatial weighting, product revisions
or original retrieval provenance. Its checksum verifies file identity, not scientific authenticity.

Inference assumes a linear conditional mean, fixed seasonal effects and sufficiently weak
residual dependence for HAC. Correlation beyond 12 months, nonstationarity, breaks, nonlinear
change, evolving seasonality and lag sensitivity need further assessment. The interval covers
regression sampling uncertainty under these assumptions; it excludes reanalysis structural,
measurement and spatial aggregation uncertainty. Statistical significance alone does not
establish attribution or practical importance.
