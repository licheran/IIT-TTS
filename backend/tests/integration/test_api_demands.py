"""A run of a configured dataset: the solver's sessions are stored and shown like any event."""

import pytest
from api_helpers import create_dataset
from fastapi.testclient import TestClient

from fixtures import demand, make_dataset, res
from tts.api.main import create_app
from tts.core.model import Dataset
from tts.core.verifier import hard_violations, verify
from tts.store.repositories import RunRepo
from tts.worker.runner import Worker

pytestmark = pytest.mark.integration


def configured() -> Dataset:
    groups = [res(f"g{i}", "G", capacity=10) for i in (1, 2, 3, 4)]
    return make_dataset(
        days=2,
        periods=4,
        resources=[*groups, res("r1", "R", capacity=20)],
        demands=[demand(participants=[g.code for g in groups], limit=2, kind="TUT")],
        validate=False,
    )


@pytest.fixture
def client(db_url: str):
    with TestClient(create_app(db_url)) as c:
        yield c


def solved_run(client: TestClient, session_factory) -> tuple[int, Dataset]:
    ds = configured()
    dataset_id = create_dataset(client)
    with session_factory() as session:
        run_id = RunRepo(session).create(
            dataset_id,
            {"num_workers": 1, "time_limit_s": 30},
            {"dataset": ds.model_dump(mode="json")},
            "h",
        )
        session.commit()
    assert Worker(session_factory, worker_id="w").run_once() is True
    return run_id, ds


def test_the_run_succeeds_and_keeps_the_created_sessions(client, session_factory) -> None:
    run_id, ds = solved_run(client, session_factory)
    assert client.get(f"/runs/{run_id}").json()["status"] == "succeeded"
    with session_factory() as session:
        result = RunRepo(session).result(run_id)
    assert sorted(c.code for c in result.created) == ["d1-TUT-01", "d1-TUT-02"]
    assert hard_violations(verify(ds, result)) == []


def test_the_assignment_list_names_the_created_sessions_with_their_groups(
    client, session_factory
) -> None:
    run_id, _ = solved_run(client, session_factory)
    rows = client.get(f"/runs/{run_id}/assignments").json()
    assert sorted(r["event"] for r in rows) == ["d1-TUT-01", "d1-TUT-02"]
    assert all(len(r["fixed"]) == 2 for r in rows)
    assert {g for r in rows for g in r["fixed"]} == {"g1", "g2", "g3", "g4"}


def test_a_participants_grid_shows_its_session(client, session_factory) -> None:
    run_id, _ = solved_run(client, session_factory)
    grid = client.get(f"/runs/{run_id}/grid", params={"code": "g1"}).json()
    assert [cell["event"] for cell in grid["cells"]] == ["d1-TUT-01"]


def test_the_exports_include_the_created_sessions(client, session_factory) -> None:
    run_id, _ = solved_run(client, session_factory)
    csv = client.get(f"/runs/{run_id}/export", params={"format": "csv"})
    assert csv.status_code == 200
    assert "d1-TUT-01" in csv.text and "d1-TUT-02" in csv.text
    html = client.get(f"/runs/{run_id}/export", params={"format": "html"})
    assert html.status_code == 200
    assert "g1" in html.text


def test_a_second_run_of_the_same_data_gives_the_same_sessions(client, session_factory) -> None:
    first, _ = solved_run(client, session_factory)
    second, _ = solved_run(client, session_factory)
    with session_factory() as session:
        runs = RunRepo(session)
        assert runs.result(first).created == runs.result(second).created
