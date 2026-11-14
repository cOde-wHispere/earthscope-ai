from dataclasses import replace

import numpy as np
import pytest

from earthscope_backend.analysis import (
    AnalysisError,
    annual_series,
    climatology,
    estimate_trend,
    monthly_series,
)
from earthscope_backend.importer import Observation


def synthetic(dataset, slope):
    rng = np.random.default_rng(127)
    count = len(dataset.observations)
    noise = rng.normal(0, 0.3, count)
    # AR(1) noise exercises a setting where independent-error uncertainty is inappropriate.
    for index in range(1, count):
        noise[index] += 0.5 * noise[index - 1]
    return replace(
        dataset,
        observations=tuple(
            Observation(
                point.time,
                300 + 4 * np.cos(2 * np.pi * index / 12) + slope * index / 120 + noise[index],
            )
            for index, point in enumerate(dataset.observations)
        ),
    )


@pytest.mark.parametrize("slope", [0.5, -0.5])
def test_synthetic_trend(dataset, slope):
    result = estimate_trend(synthetic(dataset, slope))
    stats = result.observations
    assert stats.slope_celsius_per_decade == pytest.approx(slope, abs=0.08)
    assert stats.confidence_interval_celsius_per_decade.lower < slope
    assert stats.confidence_interval_celsius_per_decade.upper > slope
    assert stats.p_value < 0.05
    assert result.interpretation.significant
    assert ("warming" if slope > 0 else "cooling") in result.interpretation.conclusion
    assert stats.hac_maxlags_months == 12
    assert stats.residual_degrees_of_freedom == 407


def test_synthetic_no_trend(dataset):
    result = estimate_trend(synthetic(dataset, 0))
    assert result.observations.p_value > 0.05
    assert result.observations.confidence_interval_celsius_per_decade.lower < 0
    assert result.observations.confidence_interval_celsius_per_decade.upper > 0
    assert not result.interpretation.significant
    assert result.interpretation.conclusion == "no statistically significant trend detected"


def test_fixed_effects_remove_seasonality(dataset):
    series = synthetic(dataset, 0.5)
    seasonal_offset = replace(
        series,
        observations=tuple(
            Observation(point.time, point.kelvin + point.time.month * 0.2)
            for point in series.observations
        ),
    )
    first, second = estimate_trend(series), estimate_trend(seasonal_offset)
    assert second.observations.slope_celsius_per_decade == pytest.approx(
        first.observations.slope_celsius_per_decade, abs=1e-11
    )
    assert second.observations.standard_error_celsius_per_decade == pytest.approx(
        first.observations.standard_error_celsius_per_decade, abs=1e-11
    )


def test_annual_means_and_monthly_anomalies(dataset):
    annual = annual_series(dataset)
    assert len(annual.observations) == 35
    assert annual.observations[0].mean_celsius == pytest.approx(
        np.mean([point.celsius for point in dataset.observations[:12]])
    )
    monthly = monthly_series(dataset)
    baseline = climatology(dataset)
    assert len(baseline.observations) == 12
    assert all(point.observations == 35 for point in baseline.observations)
    for month in range(1, 13):
        anomalies = [
            point.anomaly_celsius for point in monthly.observations if point.time.month == month
        ]
        assert np.mean(anomalies) == pytest.approx(0, abs=1e-12)
    point = monthly.observations[0]
    assert point.anomaly_celsius == pytest.approx(
        point.temperature_celsius - point.climatology_celsius
    )


@pytest.mark.parametrize("lag", [-1, 420, True, 1.5])
def test_invalid_hac_lag(dataset, lag):
    with pytest.raises(AnalysisError, match="lag"):
        estimate_trend(dataset, hac_maxlags=lag)


def test_incomplete_and_unordered_series(dataset):
    with pytest.raises(AnalysisError, match="24"):
        estimate_trend(replace(dataset, observations=dataset.observations[:12]))
    with pytest.raises(AnalysisError, match="equally spaced"):
        estimate_trend(replace(dataset, observations=dataset.observations[::-1]))
    with pytest.raises(AnalysisError, match="12 months"):
        annual_series(replace(dataset, observations=dataset.observations[:-1]))


def test_perfect_fit_does_not_report_fabricated_certainty(dataset):
    constant = replace(
        dataset, observations=tuple(Observation(point.time, 300) for point in dataset.observations)
    )
    with pytest.raises(AnalysisError, match="uncertainty is not estimable"):
        estimate_trend(constant)
