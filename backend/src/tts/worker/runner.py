"""The worker: claims queued runs, runs the pipeline, heartbeats and honours cancel.

The claim query is the one place outside `store/` that uses raw SQL (`backend/CLAUDE.md`). On
PostgreSQL it uses `FOR UPDATE SKIP LOCKED`, so several workers never take the same run. SQLite
has one writer at a time, and a guarded single `UPDATE ... RETURNING` is just as exclusive there.
"""

import logging
import os
import socket
import threading
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.orm import Session, sessionmaker

from tts.core.model import Dataset
from tts.core.run import RunParams
from tts.solver.solve import SolveControl
from tts.store.db import session_scope
from tts.store.models import utcnow
from tts.store.repositories import RunRepo
from tts.worker.pipeline import PipelineOutcome, run_pipeline

log = logging.getLogger("tts.worker")

HEARTBEAT_S = 1.0
CANCEL_POLL_S = 0.25

_CLAIM_PG = text(
    """
    UPDATE run SET status='running', started_at=:now, heartbeat_at=:now, worker_id=:w,
                   attempts=attempts+1
    WHERE id = (SELECT id FROM run WHERE status='queued' ORDER BY created_at, id
                FOR UPDATE SKIP LOCKED LIMIT 1)
    RETURNING id
    """
).bindparams(bindparam("now", type_=DateTime(timezone=True)))

_CLAIM_SQLITE = text(
    """
    UPDATE run SET status='running', started_at=:now, heartbeat_at=:now, worker_id=:w,
                   attempts=attempts+1
    WHERE id = (SELECT id FROM run WHERE status='queued' ORDER BY created_at, id LIMIT 1)
      AND status='queued'
    RETURNING id
    """
).bindparams(bindparam("now", type_=DateTime(timezone=True)))


class Worker:
    def __init__(
        self,
        factory: sessionmaker[Session],
        worker_id: str | None = None,
        pipeline: Callable[..., PipelineOutcome] = run_pipeline,
    ) -> None:
        self.factory = factory
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}"
        self.pipeline = pipeline

    def claim(self) -> int | None:
        """Take the oldest queued run, or return None."""
        with session_scope(self.factory) as session:
            dialect = session.get_bind().dialect.name
            statement = _CLAIM_PG if dialect == "postgresql" else _CLAIM_SQLITE
            row = session.execute(statement, {"now": utcnow(), "w": self.worker_id}).first()
            return None if row is None else int(row[0])

    def run_once(self) -> bool:
        """Re-queue stale runs, then claim and execute one run. True if a run was executed."""
        with session_scope(self.factory) as session:
            requeued, failed = RunRepo(session).reap_stale()
        if requeued or failed:
            log.warning("stale runs: re-queued %s, failed %s", requeued, failed)
        run_id = self.claim()
        if run_id is None:
            return False
        self.execute(run_id)
        return True

    def serve(self, should_stop: Callable[[], bool], interval_s: float = 1.0) -> None:
        log.info("worker %s started", self.worker_id)
        while not should_stop():
            if not self.run_once():
                time.sleep(interval_s)
        log.info("worker %s stopped", self.worker_id)

    def execute(self, run_id: int) -> None:
        """Run one claimed run to the end and store what came out."""
        with session_scope(self.factory) as session:
            runs = RunRepo(session)
            snapshot = runs.snapshot(run_id)
            params_json = runs.get(run_id).params
        control = SolveControl()
        latest: dict[str, Any] = {}
        lock = threading.Lock()
        done = threading.Event()

        def on_progress(progress: dict[str, Any]) -> None:
            with lock:
                latest.update(progress)

        watcher = threading.Thread(
            target=self._watch, args=(run_id, control, latest, lock, done), daemon=True
        )
        watcher.start()
        try:
            dataset = Dataset.model_validate(snapshot["dataset"])
            outcome = self.pipeline(dataset, RunParams(**params_json), control, on_progress)
        except Exception as error:  # a bug must fail the run, not kill the worker
            log.exception("run %s failed", run_id)
            outcome = PipelineOutcome(
                "failed", progress={"error": f"{type(error).__name__}: {error}"}
            )
        finally:
            done.set()
            watcher.join()
        with session_scope(self.factory) as session:
            RunRepo(session).finish(
                run_id,
                outcome.status,
                outcome.result,
                outcome.diagnostics,
                score=outcome.score,
                score_breakdown=outcome.score_breakdown,
                progress=outcome.progress,
            )

    def _watch(
        self,
        run_id: int,
        control: SolveControl,
        latest: dict[str, Any],
        lock: threading.Lock,
        done: threading.Event,
    ) -> None:
        """Heartbeat with progress once a second and stop the search when cancel is requested."""
        last_beat = float("-inf")
        while not done.wait(CANCEL_POLL_S):
            try:
                with session_scope(self.factory) as session:
                    runs = RunRepo(session)
                    if not control.stopped and runs.cancel_requested(run_id):
                        control.stop()
                    now = time.monotonic()
                    if now - last_beat >= HEARTBEAT_S:
                        with lock:
                            snapshot = dict(latest)
                        runs.heartbeat(run_id, snapshot or None)
                        last_beat = now
            except Exception:  # a database hiccup must not end the search
                log.exception("heartbeat for run %s failed", run_id)
