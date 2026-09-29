import pytest
from typer.testing import CliRunner

from tts.cli import app

runner = CliRunner()


@pytest.mark.parametrize("command", ["solve", "validate", "import-fet", "export"])
def test_stub_command_reports_not_implemented(command: str) -> None:
    result = runner.invoke(app, [command])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("solve", "validate", "import-fet", "export"):
        assert command in result.output
