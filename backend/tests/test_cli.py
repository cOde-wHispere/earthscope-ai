import subprocess
import sys


def test_importer_cli_success_and_failure(write_csv, rows, tmp_path):
    import json

    path = write_csv(rows)
    success = subprocess.run(
        [sys.executable, "-m", "earthscope_backend.importer", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert success.returncode == 0
    assert json.loads(success.stdout)["validation"]["valid"]
    assert not success.stderr
    missing = subprocess.run(
        [sys.executable, "-m", "earthscope_backend.importer", str(tmp_path / "missing.csv")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 2
    assert not missing.stdout
    assert "EARTHSCOPE_DATA_PATH" in missing.stderr
    path.write_text("bad source", encoding="utf-8")
    invalid = subprocess.run(
        [sys.executable, "-m", "earthscope_backend.importer", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert invalid.returncode == 2
    assert not json.loads(invalid.stderr)["valid"]


def test_cli_baseline_flag_rejects_unapproved_fixture(write_csv, rows):
    import json

    path = write_csv(rows)
    result = subprocess.run(
        [sys.executable, "-m", "earthscope_backend.importer", "--verify-baseline", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert not result.stdout
    error = json.loads(result.stderr)
    assert not error["valid"]
    assert "identity_sha256" in {issue["code"] for issue in error["issues"]}
