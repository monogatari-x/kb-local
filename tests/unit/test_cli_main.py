from typer.testing import CliRunner

from kb_cli.main import app


def test_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "watch" in result.stdout
    assert "jobs" in result.stdout
    assert "add" in result.stdout
    assert "search" in result.stdout
    assert "status" in result.stdout


def test_version():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1" in result.stdout
