import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tts.cli import app
from tts.core.model import Dataset, Result
from tts.core.verifier import verify
from tts.io.fet_html import parse_fet_groups_html, to_dataset

runner = CliRunner()
L6_HTML = Path(__file__).resolve().parents[1] / "fixtures" / "l6" / "fet-groups-export.html"


@pytest.mark.parametrize("command", ["solve", "validate", "export"])
def test_stub_command_reports_not_implemented(command: str) -> None:
    result = runner.invoke(app, [command])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("solve", "validate", "import-fet", "export"):
        assert command in result.output


def test_import_fet_writes_a_json_that_loads_back_into_the_same_dataset(tmp_path: Path) -> None:
    out = tmp_path / "l6.json"
    result = runner.invoke(app, ["import-fet", str(L6_HTML), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "30 groups and 77 events" in result.output
    assert "Anomaly: 6CCGD007C LEC on Thursday at 17:30" in result.output

    payload = json.loads(out.read_text("utf-8"))
    assert payload["format"] == "tts-import-json"
    assert len(payload["anomalies"]) == 1
    assert any("Group size: 30" in line for line in payload["assumptions"])

    dataset = Dataset.model_validate(payload["dataset"])
    placements = Result.model_validate(payload["result"])
    expected_dataset, expected_result = to_dataset(parse_fet_groups_html(L6_HTML))
    assert dataset == expected_dataset
    assert placements == expected_result
    assert dataset.validate_invariants() == []
    assert verify(dataset, placements) == []


def test_import_fet_accepts_the_short_output_option(tmp_path: Path) -> None:
    out = tmp_path / "short.json"
    assert runner.invoke(app, ["import-fet", str(L6_HTML), "-o", str(out)]).exit_code == 0
    assert out.exists()


def test_import_fet_rejects_a_missing_input_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["import-fet", str(tmp_path / "nope.html"), "--out", str(tmp_path / "x.json")]
    )
    assert result.exit_code == 2


def test_import_fet_reports_unreadable_input_and_writes_nothing(tmp_path: Path) -> None:
    bad = tmp_path / "bad.html"
    bad.write_text("<html><body><p>not a timetable</p></body></html>", "utf-8")
    out = tmp_path / "out.json"
    result = runner.invoke(app, ["import-fet", str(bad), "--out", str(out)])
    assert result.exit_code == 1
    assert "no group tables found" in result.output
    assert not out.exists()
