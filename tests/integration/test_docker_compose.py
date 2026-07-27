import shutil
import subprocess
from pathlib import Path

import pytest

COMPOSE = Path(__file__).parent.parent.parent / "docker-compose.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="docker CLI not installed",
)


def test_compose_file_valid():
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "qdrant" in result.stdout
