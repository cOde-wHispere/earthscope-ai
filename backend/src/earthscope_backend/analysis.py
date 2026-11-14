"""Descriptive summaries and seasonality-adjusted linear association, not attribution."""

from collections import defaultdict
from math import fsum

import numpy as np
import statsmodels.api as sm

from earthscope_backend.importer import Dataset
from earthscope_backend.schemas import (
    AnnualPoint,
    AnnualResponse,
    ClimatologyPoint,
    ClimatologyResponse,
    ConfidenceInterval,
    MonthlyPoint,
    MonthlyResponse,
    TrendInterpretation,
    TrendResponse,
    TrendStatistics,
)

ASSUMPTIONS = (
    "Source values are monthly area-averaged T2M in Kelvin for the specified country shape.",
    "The conditional mean has one linear time slope and fixed month-of-year effects.",
    "HAC inference assumes weakly dependent residuals and a sufficiently long record.",
)
LIMITATIONS = (
    "MERRA-2 is a model and observation reanalysis, not a direct country-wide thermometer record.",
    "Grid resolution and Giovanni country masking may limit representation of The Gambia.",
    "The CSV alone cannot independently verify spatial weights, source revisions or units.",
    "HAC lag 12 is an initial choice; longer dependence and lag sensitivity remain unassessed.",
    "The confidence interval excludes source, model structural and spatial sampling uncertainty.",
    "A linear trend can conceal nonlinear changes, breaks and changing seasonality.",
    "The full-record 1991-2025 climatology is descriptive, not a standard 30-year normal.",
    "Statistical significance does not establish practical importance or a causal mechanism.",
)


class AnalysisError(ValueError):
    """The requested model cannot support finite, meaningful uncertainty."""


def climatology(dataset: Dataset) -> ClimatologyResponse:
    groups: dict[int, list[float]] = defaultdict(list)
    for observation in dataset.observations:
        groups[observation.time.month].append(observation.celsius)
    return ClimatologyResponse(
        source_sha256=dataset.metadata.source_sha256,
        baseline_start=dataset.observations[0].time,
        baseline_end=dataset.observations[-1].time,
        observations=tuple(
            ClimatologyPoint(
                month=month, mean_celsius=fsum(values) / len(values), observations=len(values)
            )
            for month, values in sorted(groups.items())
        ),
    )


def monthly_series(dataset: Dataset) -> MonthlyResponse:
    baseline = climatology(dataset)
    means = {point.month: point.mean_celsius for point in baseline.observations}
    return MonthlyResponse(
        source_sha256=dataset.metadata.source_sha256,
        baseline_start=baseline.baseline_start,
        baseline_end=baseline.baseline_end,
        observations=tuple(
            MonthlyPoint(
                time=point.time,
                temperature_kelvin=point.kelvin,
                temperature_celsius=point.celsius,
                climatology_celsius=means[point.time.month],
                anomaly_celsius=point.celsius - means[point.time.month],
            )
            for point in dataset.observations
        ),
    )


def annual_series(dataset: Dataset) -> AnnualResponse:
    groups: dict[int, list[float]] = defaultdict(list)
    for observation in dataset.observations:
        groups[observation.time.year].append(observation.celsius)
    if any(len(values) != 12 for values in groups.values()):
        raise AnalysisError(
            "Annual means require all 12 months of every year; no imputation is used."
        )
    return AnnualResponse(
        source_sha256=dataset.metadata.source_sha256,
        observations=tuple(
            AnnualPoint(year=year, mean_celsius=fsum(values) / 12)
            for year, values in sorted(groups.items())
        ),
    )


def estimate_trend(dataset: Dataset, *, hac_maxlags: int = 12) -> TrendResponse:
    points = dataset.observations
    count = len(points)
    if count < 24:
        raise AnalysisError(
            "Month fixed effects require at least 24 complete monthly observations."
        )
    if isinstance(hac_maxlags, bool) or not isinstance(hac_maxlags, int):
        raise AnalysisError("HAC maximum lag must be an integer number of months.")
    if not 0 <= hac_maxlags < count:
        raise AnalysisError("HAC maximum lag must be between 0 and n - 1 months.")
    serial = np.array([point.time.year * 12 + point.time.month - 1 for point in points])
    if not np.all(np.diff(serial) == 1):
        raise AnalysisError("HAC requires unique, ordered, equally spaced monthly observations.")
    # Time is in decades, so slope, standard error and CI are directly degC/decade.
    decades = (serial - serial[0]) / 120.0
    months = np.array([point.time.month for point in points])
    design = np.column_stack(
        [np.ones(count), decades, *[(months == month).astype(float) for month in range(2, 13)]]
    )
    if np.linalg.matrix_rank(design) != 13:
        raise AnalysisError("Trend design is rank deficient; verify coverage of all 12 months.")
    values = np.array([point.celsius for point in points])
    ordinary = sm.OLS(values, design, missing="raise").fit()
    if float(np.max(np.abs(ordinary.resid))) < 1e-10:
        raise AnalysisError("Residual variation is effectively zero; uncertainty is not estimable.")
    robust = ordinary.get_robustcov_results(
        cov_type="HAC",
        maxlags=hac_maxlags,
        kernel="bartlett",
        use_correction=True,
        use_t=True,
    )
    slope = float(robust.params[1])
    standard_error = float(robust.bse[1])
    lower, upper = map(float, robust.conf_int(alpha=0.05)[1])
    p_value = float(robust.pvalues[1])
    if (
        not np.all(np.isfinite([slope, standard_error, lower, upper, p_value]))
        or standard_error <= 0
    ):
        raise AnalysisError("HAC uncertainty is not finite and positive; inspect source variation.")
    significant = p_value < 0.05
    conclusion = "no statistically significant trend detected"
    if significant:
        conclusion = (
            "statistically significant warming trend detected"
            if slope > 0
            else "statistically significant cooling trend detected"
        )
    return TrendResponse(
        source_sha256=dataset.metadata.source_sha256,
        observations=TrendStatistics(
            slope_celsius_per_decade=slope,
            standard_error_celsius_per_decade=standard_error,
            confidence_interval_celsius_per_decade=ConfidenceInterval(lower=lower, upper=upper),
            p_value=p_value,
            n_observations=count,
            start=points[0].time,
            end=points[-1].time,
            hac_maxlags_months=hac_maxlags,
            residual_degrees_of_freedom=int(robust.df_resid),
        ),
        interpretation=TrendInterpretation(significant=significant, conclusion=conclusion),
        assumptions=ASSUMPTIONS,
        limitations=LIMITATIONS,
    )
