"""Stdlib/Decimal audit of original CSVs; does not import application conversion code."""

import argparse
import csv
import hashlib
import io
import json
from calendar import monthrange
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

VARIABLES = ("T2M", "PRECTOTCORR", "QV2M", "U10M", "V10M", "PS")
ROOT = Path(__file__).resolve().parents[2]


def audit(directory: Path) -> dict:
    results = {}
    for variable in VARIABLES:
        path = directory / f"giovanni_merra2_gambia_{variable.lower()}_1991_2025.csv"
        raw = path.read_bytes()
        manifest_name = (
            "gambia_merra2_1991_2025.json"
            if variable == "T2M"
            else f"gambia_merra2_{variable.lower()}_1991_2025.json"
        )
        manifest = json.loads(
            (ROOT / "backend/src/earthscope_backend/manifests" / manifest_name).read_text(
                encoding="utf-8"
            )
        )
        checksum = hashlib.sha256(raw).hexdigest()
        if checksum != manifest["source_sha256"]:
            raise ValueError(f"{variable}: approved checksum mismatch")
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")), skipinitialspace=True)
        for row in reader:
            if len(row) == 2 and row[0].strip() == "time":
                break
        else:
            raise ValueError(f"{variable}: missing data header")
        monthly = []
        groups = defaultdict(list)
        dates = []
        for row in reader:
            if not row:
                continue
            stamp = datetime.strptime(row[0].strip(), "%Y-%m-%d %H:%M:%S").date()
            source = Decimal(row[1].strip())
            days = monthrange(stamp.year, stamp.month)[1]
            value = source
            if variable == "T2M":
                value = source - Decimal("273.15")
            elif variable == "PRECTOTCORR":
                value = source * 86400 * days
            elif variable == "QV2M":
                value = source * 1000
            dates.append(stamp.isoformat())
            monthly.append(float(value))
            groups[stamp.year].append((stamp.month, value, days))
        expected = [f"{year}-{month:02}-01" for year in range(1991, 2026) for month in range(1, 13)]
        if dates != expected:
            raise ValueError(f"{variable}: not exactly the ordered 420 approved months")
        annual = []
        for year, points in sorted(groups.items()):
            if len(points) != 12 or {month for month, _, _ in points} != set(range(1, 13)):
                raise ValueError(f"{variable}: incomplete year {year}")
            if variable == "PRECTOTCORR":
                value = sum(point[1] for point in points)
            elif variable == "T2M":
                value = sum(point[1] for point in points) / 12
            else:
                value = sum(point[1] * point[2] for point in points) / sum(p[2] for p in points)
            annual.append(float(value))
        results[variable] = {
            "source_sha256": checksum,
            "source_bytes": len(raw),
            "monthly_observations": len(monthly),
            "complete_years": len(annual),
            "start": dates[0],
            "end": dates[-1],
            "negative_monthly_values": sum(value < 0 for value in monthly),
            "monthly_values": monthly,
            "annual_values": annual,
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=ROOT / "data/raw")
    args = parser.parse_args()
    results = audit(args.directory)
    print(
        json.dumps(
            {
                variable: {
                    key: value
                    for key, value in result.items()
                    if key not in {"monthly_values", "annual_values"}
                }
                for variable, result in results.items()
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
