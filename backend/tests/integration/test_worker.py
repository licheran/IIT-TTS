import random
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from api_helpers import import_dataset, row_path
from fastapi.testclient import TestClient
from sqlalchemy import update

from tts.api.main import create_app
from tts.core.model import Constraint, Dataset
from tts.core.verifier import hard_violations, verify
from tts.solver import registry
from tts.solver.context import CompileContext
from tts.store.models import RunRow
from tts.store.repositories import DatasetRepo, RunRepo
from tts.worker.runner import Worker

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_url)) as c:
        yield c


@pytest.fixture
def worker(session_factory) -> Worker:
    return Worker(session_factory, worker_id="test-worker")


def start(client: TestClient, dataset_id: int, **params: object) -> int:
    response = client.post(f"/datasets/{dataset_id}/runs", json=params)
    assert response.status_code == 201, response.text
    return int(response.json()["run_id"])


def test_a_queued_run_is_solved_stored_and_verified(client, worker, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    run_id = start(client, dataset_id, num_workers=2, time_limit_s=30)
    assert client.get(f"/runs/{run_id}").json()["status"] == "queued"

    assert worker.run_once() is True
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "succeeded"
    assert len(run["input_hash"]) == 64
    assert run["progress"]["solver_status"] in ("optimal", "feasible")

    with worker.factory() as session:
        result = RunRepo(session).result(run_id)
        dataset = DatasetRepo(session).load(dataset_id)
    assert len(result.assignments) == len(l6_dataset.events)
    assert hard_violations(verify(dataset, result)) == []
    assert worker.run_once() is False  # nothing left in the queue


def test_the_same_dataset_gives_the_same_hash(client, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    first, second = start(client, dataset_id), start(client, dataset_id)
    hashes = {client.get(f"/runs/{r}").json()["input_hash"] for r in (first, second)}
    assert len(hashes) == 1


def test_pre_flight_errors_block_the_run_with_diagnostics(client, worker, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    rooms = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"]
    hall = next(r for r in rooms if r["values"]["room_type"] == "auditorium")
    client.delete(row_path(dataset_id, "Rooms", hall["key"]))
    run_id = start(client, dataset_id)
    worker.run_once()
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "blocked"
    assert any(d["kind"] == "no_candidate" and d["severity"] == "error" for d in run["diagnostics"])


def test_claims_never_hand_out_a_run_twice(client, session_factory, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    runs = [start(client, dataset_id) for _ in range(3)]
    first, second = Worker(session_factory, "a"), Worker(session_factory, "b")
    claimed = [first.claim(), second.claim(), first.claim(), second.claim()]
    assert sorted(c for c in claimed if c is not None) == sorted(runs)
    assert claimed[3] is None


def test_workers_racing_take_each_run_once(client, session_factory, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    runs = [start(client, dataset_id) for _ in range(8)]
    taken: list[int] = []
    lock = threading.Lock()

    def work(name: str) -> None:
        w = Worker(session_factory, name)
        while (run_id := w.claim()) is not None:
            with lock:
                taken.append(run_id)

    threads = [threading.Thread(target=work, args=(f"w{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(taken) == sorted(runs)


def test_a_worker_that_dies_leaves_a_run_that_is_requeued(
    client, session_factory, worker, l6_dataset
) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    run_id = start(client, dataset_id)
    assert worker.claim() == run_id  # claimed, then the worker "dies"
    old = datetime.now(UTC) - timedelta(minutes=5)
    with session_factory() as session:
        session.execute(
            update(RunRow).where(RunRow.id == run_id).values(heartbeat_at=old, started_at=old)
        )
        session.commit()
    assert worker.run_once() is True  # reaps it, claims it again and solves it
    run = client.get(f"/runs/{run_id}").json()
    assert (run["status"], run["attempts"]) == ("succeeded", 2)


def _slow_objective(ctx: CompileContext, constraint: Constraint) -> None:
    """A test-only soft rule whose optimum is hard to prove, so the search keeps running."""
    rng = random.Random(1)
    terms = [rng.randint(1, 50) * ctx.day_is(code, day) for code in ctx.start for day in range(6)]
    ctx.model.minimize(sum(terms))


def with_slow_rule(dataset: Dataset) -> Dataset:
    rule = Constraint(code="TEST-SLOW", type="test_slow", hard=False, weight=1)
    return dataset.model_copy(update={"constraints": (rule,)})


def test_cancel_stops_a_long_run_within_two_seconds_and_keeps_the_best_solution(
    client, worker, l6_dataset, session_factory, monkeypatch
) -> None:
    monkeypatch.setitem(registry.COMPILERS, "test_slow", _slow_objective)
    dataset_id = import_dataset(client, l6_dataset)
    with session_factory() as session:
        DatasetRepo(session).save(dataset_id, with_slow_rule(l6_dataset))
        session.commit()
    run_id = start(client, dataset_id, time_limit_s=120, num_workers=2)

    thread = threading.Thread(target=worker.run_once)
    thread.start()
    deadline = time.monotonic() + 30
    while client.get(f"/runs/{run_id}").json()["progress"].get("solutions", 0) < 1:
        assert time.monotonic() < deadline, "the search never found a solution"
        time.sleep(0.2)
    asked = time.monotonic()
    assert client.post(f"/runs/{run_id}/cancel").json()["cancel_requested"] is True
    thread.join(timeout=10)
    stopped_after = time.monotonic() - asked

    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "cancelled_partial"
    assert stopped_after < 2.0
    with session_factory() as session:
        result = RunRepo(session).result(run_id)
    assert len(result.assignments) == len(l6_dataset.events)
    assert hard_violations(verify(with_slow_rule(l6_dataset), result)) == []


def test_cancelling_a_queued_run_ends_it_at_once(client, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    run_id = start(client, dataset_id)
    assert client.post(f"/runs/{run_id}/cancel").json()["status"] == "cancelled"
    assert client.post(f"/runs/{run_id}/cancel").status_code == 200  # cancelling twice is harmless
