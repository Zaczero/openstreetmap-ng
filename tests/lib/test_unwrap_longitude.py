"""Drive the shipped unwrapLongitude helper (issue #161 globe wrapping)."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve().parent / "run_unwrap_longitude.ts"


def test_unwrap_longitude_shipped_helper():
    result = subprocess.run(
        ["node", "--experimental-strip-types", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("ok")


if __name__ == "__main__":
    test_unwrap_longitude_shipped_helper()
    print("ok")
