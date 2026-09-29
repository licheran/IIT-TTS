from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from tts.core.model import Diagnostic, Ref
from tts.store import models as m
from tts.store.repositories import (
    MAX_ATTEMPTS,
    DatasetRepo,
    NotFoundError,
    NotPublishableError,
    RunRepo,
)


def test_l6_survives_a_save_and_a_load(session, l6_dataset) -> None:
    repo = DatasetRepo(session)
    dataset_id = repo.create("L6", l6_dataset.preset, l6_dataset)
    session.commit()
    session.expire_all()
    assert repo.load(dataset_id) == l6_dataset


def test_saving_replaces_the_rows_and_counts_versions(session, l6_dataset) -> None:
    repo = DatasetRepo(session)
    dataset_id = repo.create("L6", l6_dataset.preset, l6_dataset)
    smaller = l6_dataset.model_copy(
        update={"events": l6_dataset.events[:3], "fixed": (), "pooled": ()}
    )
    info = repo.save(dataset_id, smaller, {"meta": {"institution": "IIT"}})
    session.commit()
    assert info.version == 2
    assert [e.code for e in repo.load(dataset_id).events] == [e.code for e in smaller.events]
    assert repo.extras(dataset_id) == {"meta": {"institution": "IIT"}}


def test_a_dataset_is_deleted_with_its_rows_and_runs(session, l6_dataset) -> None:
    repo = DatasetRepo(session)
    dataset_id = repo.create("L6", l6_dataset.preset, l6_dataset)
    run_id = RunRepo(session).create(dataset_id, {}, {}, "h")
    repo.delete(dataset_id)
    session.commit()
    assert repo.list() == []
    with pytest.raises(NotFoundError):
        RunRepo(session).get(run_id)
    assert session.query(m.EventRow).count() == 0


def test_a_duplicate_code_is_rejected_by_the_database(session, l6_dataset) -> None:
    repo = DatasetRepo(session)
    dataset_id = repo.create("L6", l6_dataset.preset, l6_dataset)
    session.add(m.ResourceRow(dataset_id=dataset_id, code=l6_dataset.resources[0].code, type="X"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_a_run_keeps_its_result_and_diagnostics(session, l6_dataset, l6_locked_result) -> None:
    dataset_id = DatasetRepo(session).create("L6", l6_dataset.preset, l6_dataset)
    runs = RunRepo(session)
    run_id = runs.create(dataset_id, {"seed": 1}, {"snapshot": True}, "abc")
    diag = Diagnostic(
        kind="note", message="hi", refs=(Ref(kind="event", code="E"),), details=("a",)
    )
    runs.finish(run_id, "succeeded", l6_locked_result, [diag], score=3, score_breakdown={"X": 3})
    session.commit()
    session.expire_all()
    assert runs.result(run_id) == l6_locked_result
    assert runs.diagnostics(run_id) == [diag]
    info = runs.get(run_id)
    assert (info.status, info.score, info.score_breakdown) == ("succeeded", 3, {"X": 3})
    assert runs.snapshot(run_id) == {"snapshot": True}


def test_publishing_moves_the_flag_to_the_new_run(session, l6_dataset) -> None:
    dataset_id = DatasetRepo(session).create("L6", l6_dataset.preset, l6_dataset)
    runs = RunRepo(session)
    a, b, c = (runs.create(dataset_id, {}, {}, "h") for _ in range(3))
    runs.finish(a, "succeeded")
    runs.finish(b, "cancelled_partial")
    runs.finish(c, "infeasible")
    runs.publish(a)
    runs.publish(b)
    assert [r.id for r in runs.list(dataset_id) if r.published] == [b]
    assert runs.published(dataset_id).id == b  # type: ignore[union-attr]
    with pytest.raises(NotPublishableError):
        runs.publish(c)


def test_cancelling_a_queued_run_ends_it_and_a_running_one_is_flagged(session, l6_dataset) -> None:
    dataset_id = DatasetRepo(session).create("L6", l6_dataset.preset, l6_dataset)
    runs = RunRepo(session)
    queued = runs.create(dataset_id, {}, {}, "h")
    running = runs.create(dataset_id, {}, {}, "h")
    session.execute(update(m.RunRow).where(m.RunRow.id == running).values(status="running"))
    assert runs.request_cancel(queued).status == "cancelled"
    assert runs.request_cancel(running).cancel_requested
    assert runs.cancel_requested(running)


def test_a_stale_run_is_requeued_twice_and_then_fails(session, l6_dataset) -> None:
    dataset_id = DatasetRepo(session).create("L6", l6_dataset.preset, l6_dataset)
    runs = RunRepo(session)
    run_id = runs.create(dataset_id, {}, {}, "h")
    old = datetime.now(UTC) - timedelta(minutes=5)

    def start(attempts: int) -> None:
        session.execute(
            update(m.RunRow)
            .where(m.RunRow.id == run_id)
            .values(
                status="running", attempts=attempts, heartbeat_at=old, started_at=old, worker_id="w"
            )
        )

    start(1)
    assert runs.reap_stale() == ([run_id], [])
    assert runs.get(run_id).status == "queued"
    start(MAX_ATTEMPTS - 1)
    assert runs.reap_stale() == ([run_id], [])
    start(MAX_ATTEMPTS)
    assert runs.reap_stale() == ([], [run_id])
    assert runs.get(run_id).status == "failed"


def test_a_fresh_heartbeat_is_not_stale(session, l6_dataset) -> None:
    dataset_id = DatasetRepo(session).create("L6", l6_dataset.preset, l6_dataset)
    runs = RunRepo(session)
    run_id = runs.create(dataset_id, {}, {}, "h")
    session.execute(
        update(m.RunRow).where(m.RunRow.id == run_id).values(status="running", attempts=1)
    )
    runs.heartbeat(run_id, {"elapsed": 1})
    assert runs.reap_stale() == ([], [])
    assert runs.get(run_id).progress == {"elapsed": 1}
