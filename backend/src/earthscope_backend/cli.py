"""Command-line validation using the same canonical exception types as the application."""

import argparse
import sys
from pathlib import Path

from earthscope_backend.config import data_path
from earthscope_backend.identity import load_baseline_identity, load_verified_dataset
from earthscope_backend.importer import (
    DatasetUnavailableError,
    DatasetValidationError,
    import_giovanni,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Giovanni CSV or approved MVP baseline."
    )
    parser.add_argument("path", nargs="?", type=Path, default=data_path())
    parser.add_argument(
        "--verify-baseline",
        action="store_true",
        help="Also verify the packaged approved baseline identity and checksum.",
    )
    args = parser.parse_args()
    try:
        dataset = (
            load_verified_dataset(args.path, load_baseline_identity())
            if args.verify_baseline
            else import_giovanni(args.path)
        )
    except DatasetUnavailableError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 2
    except DatasetValidationError as exc:
        print(exc.summary.model_dump_json(indent=2), file=sys.stderr)
        return 2
    print(dataset.metadata.model_dump_json(indent=2))
    return 0
