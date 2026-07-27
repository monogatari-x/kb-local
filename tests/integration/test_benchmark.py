import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent.parent / "scripts"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker not installed"),
]


def test_benchmark_smoke():
    env = {**os.environ, "HF_HUB_OFFLINE": "1"}
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "benchmark.py"),
            "--sample-size",
            "5",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "index_spec_pass" in result.stdout
