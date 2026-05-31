import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chart_engine.py"
PY = sys.executable
BASE_ARGS = [
    PY,
    str(SCRIPT),
    "--name", "Test",
    "--gender", "女",
    "--date", "1990-06-15",
    "--time", "08:30",
    "--tz", "8",
    "--lat", "25.0",
    "--lon", "121.5",
    "--target", "2025-01-01",
]


def run_engine(*extra):
    return subprocess.run(
        [*BASE_ARGS, *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_json_output():
    proc = run_engine("--json")
    assert proc.returncode == 0, proc.stderr or proc.stdout
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    for key in ["schema_version", "input", "western", "human_design", "ziwei", "meta"]:
        assert key in data
    assert len(data["western"]["planets"]) == 12
    assert len(data["western"]["houses"]) == 12
    assert data["ziwei"]["palaces"]
    for palace in data["ziwei"]["palaces"]:
        assert "name" in palace
        assert "ganzhi" in palace


def test_markdown_output():
    proc = run_engine()
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "西洋星盤" in proc.stdout


if __name__ == "__main__":
    test_json_output()
    test_markdown_output()
    print("ok")
