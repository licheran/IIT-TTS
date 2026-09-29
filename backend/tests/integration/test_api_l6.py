"""L6 end to end through the API, with a worker running in the background (P6.7)."""

import threading
import time
from collections.abc import Iterator

import pytest
from api_helpers import create_dataset, workbook_bytes
from fastapi.testclient import TestClient

from tts.api.main import create_app
from tts.worker.runner import Worker

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_url)) as c:
        yield c


@pytest.fixture
def background_worker(session_factory) -> Iterator[None]:
    stop = threading.Event()
    thread = threading.Thread(
        target=Worker(session_factory, "bg").serve, args=(stop.is_set, 0.05), daemon=True
    )
    thread.start()
    yield
    stop.set()
    thread.join(timeout=30)


def wait_for(client: TestClient, run_id: int, done: set[str], timeout: float = 60) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = client.get(f"/runs/{run_id}").json()
        if run["status"] in done:
            return run
        time.sleep(0.1)
    raise AssertionError(f"run {run_id} did not reach {done}: {run['status']}")


def test_l6_from_upload_to_exported_grid(client, background_worker, l6_dataset) -> None:
    dataset_id = create_dataset(client, "L6 SE + CS")
    upload = client.post(
        f"/datasets/{dataset_id}/import",
        files={"file": ("l6.xlsx", workbook_bytes(l6_dataset), "application/octet-stream")},
    ).json()
    assert upload["ok"] is True and upload["summary"]["Activities"] == 77

    assert client.post(f"/datasets/{dataset_id}/preflight").json()["issues"] == []

    run_id = client.post(f"/datasets/{dataset_id}/runs", json={"time_limit_s": 30}).json()["run_id"]
    run = wait_for(client, run_id, {"succeeded", "failed", "blocked", "infeasible", "invalid"})
    assert run["status"] == "succeeded", run
    assert not [d for d in run["diagnostics"] if d["severity"] == "error"]

    grid = client.get(
        f"/runs/{run_id}/grid", params={"type": "StudentGroup", "code": "L6 SE / G1"}
    ).json()
    assert grid["cells"]

    html = client.get(
        f"/runs/{run_id}/export",
        params={"format": "html", "type": "StudentGroup", "code": "L6 SE / G1"},
    )
    assert html.status_code == 200 and "L6 SE / G1" in html.text

    assert client.post(f"/runs/{run_id}/publish").json()["published"] is True
