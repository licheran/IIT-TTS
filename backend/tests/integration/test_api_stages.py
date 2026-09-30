"""Staged runs and locks from published runs through the API (P10.2, spec 05 section 4.4)."""

from collections.abc import Iterator

import pytest
from api_helpers import import_dataset
from fastapi.testclient import TestClient

from tts.api.main import create_app
from tts.core.staging import occupied_slots
from tts.core.verifier import hard_violations, verify
from tts.store.repositories import DatasetRepo, RunRepo
from tts.worker.runner import Worker

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_url)) as c:
        yield c


def run(client: TestClient, worker: Worker, dataset_id: int, **params: object) -> dict:
    run_id = client.post(f"/datasets/{dataset_id}/runs", json=params).json()["run_id"]
    assert worker.run_once()
    return client.get(f"/runs/{run_id}").json()


def test_a_second_stage_locks_the_published_first_stage(
    client: TestClient, session_factory, l6_dataset
) -> None:
    worker = Worker(session_factory, "w")
    dataset_id = import_dataset(client, l6_dataset)
    first = run(client, worker, dataset_id, stage_scope="kind:LEC", time_limit_s=20)
    assert first["status"] == "succeeded"
    client.post(f"/runs/{first['id']}/publish")
    second = run(client, worker, dataset_id, stage_scope="kind:TUT", time_limit_s=20)
    assert second["status"] == "succeeded"
    with session_factory() as session:
        runs = RunRepo(session)
        lectures, everything = runs.result(first["id"]), runs.result(second["id"])
    assert len(lectures.assignments) == 22 and len(everything.assignments) == 77
    placed = {a.event: a for a in everything.assignments}
    assert all(placed[a.event] == a for a in lectures.assignments)
    assert hard_violations(verify(l6_dataset, everything)) == []


def test_a_bad_stage_scope_is_refused(client: TestClient, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    response = client.post(f"/datasets/{dataset_id}/runs", json={"stage_scope": "nonsense:"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_stage_scope"


def test_a_run_keeps_off_what_another_dataset_published(
    client: TestClient, session_factory, l6_dataset
) -> None:
    worker = Worker(session_factory, "w")
    other_id = import_dataset(client, l6_dataset, "other")
    published = run(client, worker, other_id, time_limit_s=20)
    client.post(f"/runs/{published['id']}/publish")

    # A second dataset that shares one teacher with the published one.
    teacher = "HAWE"
    mine = l6_dataset.model_copy(
        update={
            "events": tuple(e for e in l6_dataset.events if any(
                f.event == e.code and f.resource == teacher for f in l6_dataset.fixed
            )),
        }
    )  # fmt: skip
    events = {e.code for e in mine.events}
    mine = mine.model_copy(
        update={
            "fixed": tuple(f for f in mine.fixed if f.event in events),
            "pooled": tuple(q for q in mine.pooled if q.event in events),
        }
    )
    mine_id = import_dataset(client, mine, "mine")
    locked = run(client, worker, mine_id, time_limit_s=20)
    free = run(client, worker, mine_id, time_limit_s=20, lock_published=False)
    assert locked["status"] == "succeeded" and free["status"] == "succeeded"

    with session_factory() as session:
        runs = RunRepo(session)
        theirs = occupied_slots(l6_dataset, runs.result(published["id"]))[teacher]
        ours = occupied_slots(DatasetRepo(session).load(mine_id), runs.result(locked["id"]))
    assert ours[teacher].isdisjoint(theirs)


def test_the_clash_report_names_published_runs_that_share_resources(
    client: TestClient, session_factory, l6_dataset
) -> None:
    worker = Worker(session_factory, "w")
    first = import_dataset(client, l6_dataset, "first")
    second = import_dataset(client, l6_dataset, "second")
    assert client.get("/clashes").json() == []
    a = run(client, worker, first, time_limit_s=20)
    client.post(f"/runs/{a['id']}/publish")
    b = run(client, worker, second, time_limit_s=20, lock_published=False)
    client.post(f"/runs/{b['id']}/publish")
    clashes = client.get("/clashes").json()
    assert clashes, "two copies of L6 solved independently must share some periods"
    assert {u["dataset"] for u in clashes[0]["uses"]} == {"first", "second"}
