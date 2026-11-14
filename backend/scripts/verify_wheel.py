"""Build without network/installing, then verify packaged manifests and APIs from the wheel."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="earthscope-m17-wheel-") as directory:
        task = Path(directory)
        source = task / "source"
        source.mkdir()
        shutil.copyfile(ROOT / "backend/pyproject.toml", source / "pyproject.toml")
        shutil.copytree(
            ROOT / "backend/src",
            source / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--no-build-isolation",
                "--no-index",
                "--wheel-dir",
                str(task / "wheels"),
                str(source),
            ],
            check=True,
        )
        (wheel,) = (task / "wheels").glob("*.whl")
        with ZipFile(wheel) as archive:
            manifests = sorted(name for name in archive.namelist() if "/manifests/" in name)
            expected = {"gambia_merra2_1991_2025.json"} | {
                f"gambia_merra2_{variable}_1991_2025.json"
                for variable in ("prectotcorr", "qv2m", "u10m", "v10m", "ps")
            }
            if {Path(name).name for name in manifests} != expected:
                raise ValueError("Wheel does not contain exactly the six approved manifests")
            if any(name.lower().endswith(".csv") for name in archive.namelist()):
                raise ValueError("Raw CSV included in wheel")
        # Isolated interpreter, unrelated cwd, wheel first on sys.path; do not install it.
        script = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import earthscope_backend
assert '.whl' in earthscope_backend.__file__, earthscope_backend.__file__
from fastapi.testclient import TestClient
from earthscope_backend.main import create_app
raw = Path(sys.argv[2])
with TestClient(create_app(raw / 'giovanni_merra2_gambia_t2m_1991_2025.csv',
                           v2_directory=raw)) as client:
    catalog = client.get('/v2/datasets').json()['datasets']
    assert len(catalog) == 6 and all(item['status'] == 'ready' for item in catalog), catalog
    for item in catalog:
        for key in ('metadata_url', 'monthly_url', 'annual_url'):
            assert client.get(item[key]).status_code == 200
    assert client.get('/trend').status_code == 200
print(json.dumps({'wheel_import': True, 'ready_datasets': 6, 'v2_responses_200': 18,
                  'legacy_trend_200': True}))
"""
        subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                script,
                str(wheel),
                str(ROOT / "data/raw"),
            ],
            cwd=task,
            check=True,
        )
        print(json.dumps({"manifests": len(manifests), "raw_csvs_packaged": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
