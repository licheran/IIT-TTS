"""Template expansion through the API (P9.2): preview, commit, and runs of templates."""

from collections.abc import Iterator

import pytest
from api_helpers import create_dataset, import_dataset
from fastapi.testclient import TestClient

from tts.api.main import create_app
from tts.core.model import CapacityRule, PooledSpec, Template
from tts.store.repositories import DatasetRepo, RunRepo
from tts.worker.runner import Worker

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_url)) as c:
        yield c


def with_templates(l6_dataset):
    """L6 without its activities, and two templates for one module."""
    lab = PooledSpec(
        resource_type="Room",
        filter="tag:room_type=lab",
        capacity_rule=CapacityRule.parse("sum_of_fixed:StudentGroup"),
    )
    templates = (
        Template(
            code="TP-LEC", kind="LEC", mode="joint", reference="6ELEN018C",
            targets='code:"L6 SE / G1","L6 SE / G2"', fixed=("AAM",), pooled=(lab,),
            duration=2, start_pattern="2H",
        ),
        Template(
            code="TP-TUT", kind="TUT", mode="each", reference="6ELEN018C",
            targets='code:"L6 SE / G1","L6 SE / G2"', fixed=("AAM",), pooled=(lab,),
            duration=2, start_pattern="2H",
        ),
    )  # fmt: skip
    return l6_dataset.model_copy(
        update={"events": (), "fixed": (), "pooled": (), "templates": templates}
    )


def load_into(client: TestClient, session_factory, dataset) -> int:
    dataset_id = create_dataset(client, "templates")
    with session_factory() as session:
        DatasetRepo(session).save(dataset_id, dataset)
        session.commit()
    return dataset_id


def test_a_preview_lists_the_activities_and_changes_nothing(
    client: TestClient, session_factory, l6_dataset
) -> None:
    dataset_id = load_into(client, session_factory, with_templates(l6_dataset))
    preview = client.post(f"/datasets/{dataset_id}/expand").json()
    assert preview["committed"] is False
    assert preview["added"] == ["6ELEN018C-LEC-01", "6ELEN018C-TUT-01", "6ELEN018C-TUT-02"]
    assert preview["orders_added"] == 2
    assert client.get(f"/datasets/{dataset_id}/tables/Activities").json()["total"] == 0


def test_a_commit_writes_the_activities_and_a_second_commit_changes_nothing(
    client: TestClient, session_factory, l6_dataset
) -> None:
    dataset_id = load_into(client, session_factory, with_templates(l6_dataset))
    first = client.post(f"/datasets/{dataset_id}/expand", params={"commit": True}).json()
    assert first["committed"] is True
    activities = client.get(f"/datasets/{dataset_id}/tables/Activities").json()
    assert activities["total"] == 3
    assert {r["values"]["template"] for r in activities["rows"]} == {"TP-LEC", "TP-TUT"}
    again = client.post(f"/datasets/{dataset_id}/expand", params={"commit": True}).json()
    assert again["committed"] is False and again["added"] == again["changed"] == []


def test_hand_made_activities_survive_an_expansion(
    client: TestClient, session_factory, l6_dataset
) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    result = client.post(f"/datasets/{dataset_id}/expand", params={"commit": True}).json()
    assert result == {
        "committed": False, "added": [], "changed": [], "removed": [],
        "orders_added": 0, "orders_removed": 0, "problems": [],
    }  # fmt: skip
    assert client.get(f"/datasets/{dataset_id}/tables/Activities").json()["total"] == 77


def test_a_run_of_templates_solves_the_activities_they_make(
    client: TestClient, session_factory, l6_dataset
) -> None:
    dataset_id = load_into(client, session_factory, with_templates(l6_dataset))
    run_id = client.post(f"/datasets/{dataset_id}/runs", json={"time_limit_s": 20}).json()["run_id"]
    Worker(session_factory, "w").run_once()
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "succeeded", run
    with session_factory() as session:
        result = RunRepo(session).result(run_id)
    assert {a.event for a in result.assignments} == {
        "6ELEN018C-LEC-01", "6ELEN018C-TUT-01", "6ELEN018C-TUT-02",
    }  # fmt: skip
    grid = client.get(f"/runs/{run_id}/grid", params={"code": "L6 SE / G1"}).json()
    assert len(grid["cells"]) == 2  # the lecture and G1's tutorial
