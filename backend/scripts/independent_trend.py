"""Independent audit: raw CSV -> NumPy least squares -> manual Newey-West sandwich.

Does not import the application importer, analysis module or statsmodels.
"""

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import t


def audit(path: Path, maxlags: int = 12) -> dict:
    raw = path.read_bytes()
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")), skipinitialspace=True)
    for row in reader:
        if [cell.strip() for cell in row] == ["time", "mean_M2IMNXASM_5_12_4_T2M"]:
            break
    else:
        raise ValueError("NASA data header missing")
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    dates = [datetime.strptime(row[0].strip(), "%Y-%m-%d %H:%M:%S") for row in rows]
    serial = np.array([stamp.year * 12 + stamp.month - 1 for stamp in dates])
    expected = np.arange(1991 * 12, 2026 * 12)
    if not np.array_equal(serial, expected):
        raise ValueError("Audit requires exactly 420 ordered months: 1991-01 through 2025-12")
    kelvin = np.array([float(row[1]) for row in rows])
    if not np.all(np.isfinite(kelvin) & (kelvin >= 150) & (kelvin <= 350)):
        raise ValueError("Audit found invalid temperatures or missing measurements")
    # Twelve separate month intercepts plus time in MONTHS (a different parameterization).
    month_intercepts = np.eye(12)[[stamp.month - 1 for stamp in dates]]
    design = np.column_stack([month_intercepts, serial - serial[0]])
    y = kelvin - 273.15
    coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ coefficients
    scores = design * residuals[:, None]
    meat = scores.T @ scores
    for lag in range(1, maxlags + 1):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (maxlags + 1)) * (cross + cross.T)
    bread = np.linalg.inv(design.T @ design)
    n, k = design.shape
    covariance = (n / (n - k)) * bread @ meat @ bread
    slope = float(coefficients[-1] * 120)
    standard_error = float(np.sqrt(covariance[-1, -1]) * 120)
    critical = float(t.ppf(0.975, n - k))
    return {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "n_observations": n,
        "design_rank": int(rank),
        "residual_degrees_of_freedom": n - k,
        "slope_celsius_per_decade": slope,
        "standard_error_celsius_per_decade": standard_error,
        "ci95_lower": slope - critical * standard_error,
        "ci95_upper": slope + critical * standard_error,
        "p_value": float(2 * t.sf(abs(slope / standard_error), n - k)),
        "hac_maxlags_months": maxlags,
        "method": "NumPy lstsq; manual Bartlett HAC with n/(n-k) correction; Student-t",
        "minimum_celsius": float(y.min()),
        "maximum_celsius": float(y.max()),
        "mean_celsius": float(y.mean()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    print(json.dumps(audit(parser.parse_args().path), indent=2))
