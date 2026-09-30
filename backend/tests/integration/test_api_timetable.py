"""Editing the solver's sessions and rebuilding (P22, ADR-0007)."""

import io

import pytest
from academic_config import dataset as configured_dataset
from academic_config import resource
from api_helpers import create_dataset
from fastapi.testclient import TestClient

from tts.api.main import create_app
from tts.core.verifier import hard_violations, verify
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.store.repositories import DatasetRepo, RunRepo
from tts.worker.runner import Worker

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_url: str):
    with TestClient(create_app(db_url)) as c:
        yield c


def configured():  # type: ignore[no-untyped-def]
    ds = configured_dataset()
    rooms = tuple(
        resource(code, "Room", capacity=100).model_copy(update={"tags": (("room_type", "lab"),)})
        for code in ("R1", "R2")
    )
    return ds.model_copy(update={"resources": (*ds.resources, *rooms)})


def upload(client: TestClient, dataset_id: int) -> None:
    buffer = io.BytesIO()
    export_xlsx(WorkbookData(configured()), buffer)
    files = {"file": ("c.xlsx", buffer.getvalue(), "application/octet-stream")}
    assert client.post(f"/datasets/{dataset_id}/import", files=files).json()["ok"]


def solve(client: TestClient, session_factory, dataset_id: int) -> int:  # type: ignore[no-untyped-def]
    started = client.post(
        f"/datasets/{dataset_id}/runs", json={"num_workers": 1, "time_limit_s": 30}
    )
    assert started.status_code == 201, started.text
    assert Worker(session_factory, worker_id="w").run_once() is True
    run_id = int(started.json()["run_id"])
    assert client.get(f"/runs/{run_id}").json()["status"] == "succeeded"
    return run_id


@pytest.fixture
def solved(client, session_factory):  # type: ignore[no-untyped-def]
    dataset_id = create_dataset(client)
    upload(client, dataset_id)
    run_id = solve(client, session_factory, dataset_id)
    return dataset_id, run_id


def table(client: TestClient, dataset_id: int) -> dict:  # type: ignore[type-arg]
    return client.get(f"/datasets/{dataset_id}/timetable").json()


def row(client: TestClient, dataset_id: int, code: str) -> dict:  # type: ignore[type-arg]
    return next(r for r in table(client, dataset_id)["rows"] if r["code"] == code)


def test_the_table_lists_the_current_runs_sessions_with_their_groups_teachers_and_rooms(
    client, solved
) -> None:
    dataset_id, run_id = solved
    found = table(client, dataset_id)
    assert found["run_id"] == run_id and found["edits"] == 0
    assert sorted(r["code"] for r in found["rows"]) == [
        "M1-LEC-01", "M1-TUT-01", "M1-TUT-02", "M1-TUT-03", "M2-TUT-01", "M3-LEC-01",
    ]  # fmt: skip
    lecture = row(client, dataset_id, "M1-LEC-01")
    assert lecture["groups"] == ["P1/G1", "P1/G2", "P2/G1"]
    assert lecture["teachers"] == ["T1"] and len(lecture["rooms"]) == 1
    assert lecture["edited"] == []


def test_before_any_run_the_table_is_empty(client) -> None:
    dataset_id = create_dataset(client)
    upload(client, dataset_id)
    assert table(client, dataset_id) == {"run_id": None, "edits": 0, "rows": []}


def test_an_edit_is_shown_at_once_and_marks_the_fields_the_user_set(client, solved) -> None:
    dataset_id, _ = solved
    response = client.put(
        f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri", "start": "P3"}
    )
    assert response.status_code == 200, response.text
    edited = row(client, dataset_id, "M1-LEC-01")
    assert (edited["day"], edited["start"]) == ("Fri", "P3")
    assert edited["edited"] == ["groups", "day", "start"]
    assert table(client, dataset_id)["edits"] == 1
    assert row(client, dataset_id, "M1-TUT-01")["edited"] == []


def test_an_edited_room_and_teacher_are_kept(client, solved) -> None:
    dataset_id, _ = solved
    client.put(
        f"/datasets/{dataset_id}/timetable/M1-TUT-01", json={"rooms": ["R2"], "teachers": ["T2"]}
    )
    edited = row(client, dataset_id, "M1-TUT-01")
    assert (edited["rooms"], edited["teachers"]) == (["R2"], ["T2"])
    assert edited["edited"] == ["groups", "rooms", "teachers"]


def test_a_second_edit_of_the_same_session_adds_to_the_first(client, solved) -> None:
    dataset_id, _ = solved
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri"})
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"start": "P3"})
    edited = row(client, dataset_id, "M1-LEC-01")
    assert (edited["day"], edited["start"]) == ("Fri", "P3")
    assert table(client, dataset_id)["edits"] == 1


def test_an_edit_naming_something_that_does_not_exist_is_refused(client, solved) -> None:
    dataset_id, _ = solved
    response = client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Sunday"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_edit"
    assert table(client, dataset_id)["edits"] == 0


def test_a_group_the_module_does_not_teach_is_refused(client, solved) -> None:
    dataset_id, _ = solved
    response = client.put(
        f"/datasets/{dataset_id}/timetable/M2-TUT-01", json={"groups": ["P1/G1", "P2/G1"]}
    )
    assert response.status_code == 422, response.text


def test_an_unknown_session_is_not_found(client, solved) -> None:
    dataset_id, _ = solved
    assert (
        client.put(f"/datasets/{dataset_id}/timetable/NOPE", json={"day": "Fri"}).status_code == 404
    )


def test_undo_forgets_one_edit_and_clear_forgets_them_all(client, solved) -> None:
    dataset_id, _ = solved
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri"})
    client.put(f"/datasets/{dataset_id}/timetable/M1-TUT-01", json={"day": "Fri"})
    assert table(client, dataset_id)["edits"] == 2
    after = client.delete(f"/datasets/{dataset_id}/timetable/M1-LEC-01").json()
    assert after["edits"] == 1
    assert row(client, dataset_id, "M1-LEC-01")["edited"] == []
    assert client.delete(f"/datasets/{dataset_id}/timetable/M1-LEC-01").status_code == 404
    assert client.delete(f"/datasets/{dataset_id}/timetable").json()["edits"] == 0


def test_the_check_shows_a_clash_an_edit_causes_before_any_rebuild(client, solved) -> None:
    dataset_id, _ = solved
    assert client.get(f"/datasets/{dataset_id}/timetable/check").json()["violations"] == []
    other = row(client, dataset_id, "M1-TUT-02")
    # Put another tutorial of the same module and groups into its time and room.
    client.put(
        f"/datasets/{dataset_id}/timetable/M1-TUT-01",
        json={"day": other["day"], "start": other["start"], "rooms": other["rooms"]},
    )
    found = client.get(f"/datasets/{dataset_id}/timetable/check").json()["violations"]
    assert any(v["code"] == "no_overlap" for v in found), found


def test_the_check_never_changes_the_stored_run(client, solved, session_factory) -> None:
    dataset_id, run_id = solved
    with session_factory() as session:
        before = RunRepo(session).result(run_id)
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri"})
    client.get(f"/datasets/{dataset_id}/timetable/check")
    with session_factory() as session:
        assert RunRepo(session).result(run_id) == before


def test_a_rebuild_keeps_the_edited_values_and_the_verifier_accepts_the_result(
    client, solved, session_factory
) -> None:
    dataset_id, _ = solved
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri", "start": "P3"})
    second = solve(client, session_factory, dataset_id)
    assert second is not None
    kept = row(client, dataset_id, "M1-LEC-01")
    assert (kept["day"], kept["start"]) == ("Fri", "P3")
    assert kept["edited"] == ["groups", "day", "start"]
    with session_factory() as session:
        repo = DatasetRepo(session)
        ds = repo.load(dataset_id)
        from tts.api.expansion import prepare_with_preset

        prepared = prepare_with_preset(ds)
        result = RunRepo(session).result(second)
    assert hard_violations(verify(prepared, result)) == []


def test_a_hand_made_dataset_has_no_timetable_table(client, l6_dataset) -> None:
    from api_helpers import import_dataset

    dataset_id = import_dataset(client, l6_dataset)
    assert client.get(f"/datasets/{dataset_id}/timetable").status_code == 409


def test_a_change_made_through_a_table_keeps_the_edits(client, solved) -> None:
    from api_helpers import row_path

    dataset_id, _ = solved
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri"})
    changed = client.patch(
        row_path(dataset_id, "SessionTypes", "LEC"), json={"values": {"name": "Lecture"}}
    )
    assert changed.status_code == 200, changed.text
    assert table(client, dataset_id)["edits"] == 1
    assert row(client, dataset_id, "M1-LEC-01")["day"] == "Fri"


def test_the_export_holds_the_configuration_only_and_an_import_starts_without_edits(
    client, solved
) -> None:
    dataset_id, _ = solved
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri"})
    exported = client.get(f"/datasets/{dataset_id}/export")
    assert exported.status_code == 200
    copy = create_dataset(client, "copy")
    files = {"file": ("c.xlsx", exported.content, "application/octet-stream")}
    assert client.post(f"/datasets/{copy}/import", files=files).json()["ok"]
    assert table(client, copy)["edits"] == 0


def test_importing_again_replaces_the_edits(client, solved) -> None:
    dataset_id, _ = solved
    client.put(f"/datasets/{dataset_id}/timetable/M1-LEC-01", json={"day": "Fri"})
    upload(client, dataset_id)
    assert table(client, dataset_id)["edits"] == 0
