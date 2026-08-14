import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent.parent / "scripts"


def test_init_db_help_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "init_db.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "config" in result.stdout.lower() or "config" in result.stderr.lower()


def test_download_models_help_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "download_models.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0


def test_backup_help_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "backup.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "dry-run" in result.stdout.lower()
