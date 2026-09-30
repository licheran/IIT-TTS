"""The exams preset end to end (P11.3): the sample workbook imports, solves, verifies and exports
through the CLI and the API, with no change to the core."""

import math
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from make_exams import PER_INVIGILATOR, build  # type: ignore[import-not-found]
from typer.testing import CliRunner

from tts.api.main import create_app
from tts.cli import app
from tts.core.verifier import hard_violations, verify
from tts.io.csvzip import import_csvzip
from tts.io.workbook import import_xlsx
from tts.presets import get_preset
from tts.presets.exams import types
from tts.worker.runner import Worker

HERE = Path(__file__).parent
WORKBOOK = HERE / "exams.xlsx"
runner = CliRunner()


def test_the_sample_workbook_is_what_the_script_writes() -> None:
    outcome = import_xlsx(WORKBOOK)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data is not None and outcome.data.dataset == build()


def test_the_preset_has_its_own_types_labels_and_defaults() -> None:
    preset = get_preset("exams")
    assert {t.code for t in preset.resource_types} == {"Cohort", "Hall", "Invigilator"}
    assert [s.name for s in preset.sheets][:4] == ["_meta", "Days", "Sessions", "StartPatterns"]
    spread = [c for c in build().constraints if c.code.startswith("EX-SPREAD-")]
    assert len(spread) == 8 and all(c.type == "min_days_between" and not c.hard for c in spread)


def test_the_cli_solves_validates_and_exports_the_exams(tmp_path: Path) -> None:
    assert runner.invoke(app, ["preflight", str(WORKBOOK)]).exit_code == 0
    solved = tmp_path / "solved.xlsx"
    result = runner.invoke(
        app, ["solve", str(WORKBOOK), "--out", str(solved), "--time-limit", "30", "--workers", "2"]
    )
    assert result.exit_code == 0, result.output
    assert "Verifier: 0 hard violation(s)" in result.output
    assert runner.invoke(app, ["validate", str(solved)]).exit_code == 0

    data = import_xlsx(solved).data
    assert data is not None and data.result is not None
    sizes = {r.code: r.capacity or 0 for r in data.dataset.resources}
    cohorts = {e.code: [] for e in data.dataset.events}
    for f in data.dataset.fixed:
        cohorts[f.event].append(f.resource)
    for a in data.result.assignments:
        halls, invigilators = (c.resources for c in a.chosen)
        size = sum(sizes[c] for c in cohorts[a.event])
        assert len(halls) == 1 and sizes[halls[0]] >= size
        assert len(invigilators) == math.ceil(size / PER_INVIGILATOR)
    assert hard_violations(verify(data.dataset, data.result)) == []

    zipped = tmp_path / "solved.zip"
    assert runner.invoke(app, ["export", str(solved), "--out", str(zipped)]).exit_code == 0
    again = import_csvzip(zipped).data
    assert again is not None and again.result == data.result


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(f"sqlite:///{tmp_path / 'exams.db'}")) as c:
        yield c


def test_the_api_runs_the_exams_and_shows_their_words(client: TestClient, tmp_path: Path) -> None:
    dataset = client.post("/datasets", json={"name": "June exams", "preset": "exams"}).json()
    dataset_id = dataset["id"]
    schema = client.get(f"/datasets/{dataset_id}/schema").json()
    assert schema["labels"]["Cohort"] == "Cohort" and schema["labels"]["EXAM"] == "Exam"
    assert "Exams" in [s["name"] for s in schema["sheets"]]

    files = {"file": ("exams.xlsx", WORKBOOK.read_bytes(), "application/octet-stream")}
    assert client.post(f"/datasets/{dataset_id}/import", files=files).json()["ok"]
    assert client.post(f"/datasets/{dataset_id}/preflight").json()["has_errors"] is False

    run_id = client.post(f"/datasets/{dataset_id}/runs", json={"time_limit_s": 30}).json()["run_id"]
    from tts.store.db import make_engine, make_session_factory

    worker = Worker(make_session_factory(make_engine(f"sqlite:///{tmp_path / 'exams.db'}")), "w")
    assert worker.run_once()
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "succeeded", run

    grid = client.get(
        f"/runs/{run_id}/grid", params={"type": types.COHORT, "code": "BSC-CS-1"}
    ).json()
    assert len(grid["cells"]) == 5  # CS101, CS102, CS103, DS102 and MA101
    assert [d["label"] for d in grid["days"]][0] == "Mon 01 Jun"
    html = client.get(
        f"/runs/{run_id}/export",
        params={"format": "html", "type": types.COHORT, "code": "BSC-CS-1"},
    ).text
    assert "Cohort</span>" in html and "Exam · CS101-EXAM" in html
