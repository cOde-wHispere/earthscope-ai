import csv
import hashlib
from collections.abc import Callable
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from earthscope_backend.config import DEFAULT_DATA_PATH, VALUE_COLUMN
from earthscope_backend.identity import load_baseline_identity
from earthscope_backend.importer import import_giovanni, month_range


@pytest.fixture
def rows() -> list[list[str]]:
    months = month_range(date(1991, 1, 1), date(2025, 12, 1))
    noise = np.random.default_rng(42).normal(0, 0.25, len(months))
    return [
        [f"{month} 00:00:00", str(300 + 3 * np.sin(2 * np.pi * i / 12) + noise[i])]
        for i, month in enumerate(months)
    ]


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable:
    def write(rows, *, metadata=None, header=None, filename="source.csv") -> Path:
        path = tmp_path / filename
        entries = (
            metadata
            if metadata is not None
            else [
                ["Title:", "Synthetic test fixture, not NASA observations"],
                ["User Start Date:", "1991-01-01T00:00:00Z"],
                ["User End Date:", "2025-12-31T23:59:59Z"],
                ["User Bounding Box:", "-16.8296,13.0839,-13.8084,13.82"],
                [
                    "URL to Reproduce Results:",
                    "https://giovanni.gsfc.nasa.gov/giovanni/#service=ArAvTs"
                    "&shape=test_shapes/synthetic_region&bbox=-16.8296,13.0839,-13.8084,13.82"
                    "&data=M2IMNXASM_5_12_4_T2M",
                ],
                [f"Fill Value ({VALUE_COLUMN}):", "1000000000000000"],
            ]
        )
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerows(entries)
            writer.writerow([])
            writer.writerow(header if header is not None else ["time", f" {VALUE_COLUMN}"])
            writer.writerows(rows)
        return path

    return write


@pytest.fixture
def fixture_identity():
    def approve(path):
        return load_baseline_identity().model_copy(
            update={
                "dataset_id": "synthetic-monthly-test-fixture-v1",
                "shape_id": "test_shapes/synthetic_region",
                "region": "Synthetic test region (not NASA observations)",
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    return approve


@pytest.fixture
def app_factory(fixture_identity):
    from earthscope_backend.main import create_app

    def create(path):
        return create_app(path, identity=fixture_identity(path))

    return create


@pytest.fixture
def dataset(write_csv, rows):
    return import_giovanni(write_csv(rows))


@pytest.fixture
def nasa_path() -> Path:
    assert DEFAULT_DATA_PATH.is_file(), (
        f"Local NASA integration source is required at {DEFAULT_DATA_PATH}. "
        "Restore it locally; raw data must remain ignored."
    )
    return DEFAULT_DATA_PATH
