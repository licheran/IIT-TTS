from collections.abc import Iterator

import pytest
from api_helpers import create_dataset, import_dataset, row_path, workbook_bytes
from fastapi.testclient import TestClient

from tts.api.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_url)) as c:
        yield c


def test_a_dataset_is_created_listed_renamed_and_deleted(client: TestClient) -> None:
    dataset_id = create_dataset(client, "Term 1")
    assert [d["name"] for d in client.get("/datasets").json()] == ["Term 1"]
    renamed = client.patch(f"/datasets/{dataset_id}", json={"name": "Term 2"})
    assert renamed.json()["name"] == "Term 2"
    assert client.delete(f"/datasets/{dataset_id}").status_code == 204
    assert client.get(f"/datasets/{dataset_id}").status_code == 404


def test_errors_use_the_standard_shape(client: TestClient) -> None:
    missing = client.get("/datasets/99")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    unknown = client.post("/datasets", json={"name": "x", "preset": "nope"})
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "unknown_preset"
    invalid = client.post("/datasets", json={"preset": "academic_weekly"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["details"][0]["where"].endswith("name")


def test_the_schema_holds_the_sheets_and_labels_of_the_preset(client: TestClient) -> None:
    dataset_id = create_dataset(client)
    schema = client.get(f"/datasets/{dataset_id}/schema").json()
    names = [s["name"] for s in schema["sheets"]]
    assert {"Rooms", "Teachers", "Activities"} <= set(names)
    assert schema["labels"]["Room"] == "Room"
    assert schema["format_version"] == 1


def test_an_empty_dataset_can_be_exported_and_read_back(client: TestClient) -> None:
    dataset_id = create_dataset(client)
    response = client.get(f"/datasets/{dataset_id}/export")
    assert response.status_code == 200
    other = create_dataset(client, "copy")
    files = {"file": ("x.xlsx", response.content, "application/octet-stream")}
    assert client.post(f"/datasets/{other}/import", files=files).json()["ok"]


def test_l6_imports_and_exports_both_formats_without_loss(client: TestClient, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    original = client.get(f"/datasets/{dataset_id}/export", params={"format": "csvzip"}).content
    for fmt, name in (("xlsx", "a.xlsx"), ("csvzip", "a.zip")):
        exported = client.get(f"/datasets/{dataset_id}/export", params={"format": fmt})
        assert exported.status_code == 200
        other = create_dataset(client, f"copy-{fmt}")
        files = {"file": (name, exported.content, "application/octet-stream")}
        assert client.post(f"/datasets/{other}/import", files=files).json()["ok"]
        # The CSV zip is byte-for-byte reproducible, so it shows that nothing was lost.
        again = client.get(f"/datasets/{other}/export", params={"format": "csvzip"}).content
        assert again == original


def test_a_bad_import_reports_every_problem_and_changes_nothing(
    client: TestClient, l6_dataset
) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    before = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["total"]
    files = {"file": ("bad.xlsx", b"not a workbook", "application/octet-stream")}
    result = client.post(f"/datasets/{dataset_id}/import", files=files).json()
    assert result["ok"] is False and result["errors"]
    assert client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["total"] == before


def test_rows_are_listed_paged_sorted_and_filtered(client: TestClient, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    page = client.get(f"/datasets/{dataset_id}/tables/Rooms", params={"size": 3}).json()
    assert page["total"] == 10 and len(page["rows"]) == 3
    assert "capacity" in page["headers"]
    by_capacity = client.get(
        f"/datasets/{dataset_id}/tables/Rooms", params={"sort": "-capacity"}
    ).json()["rows"]
    capacities = [r["values"]["capacity"] for r in by_capacity]
    assert capacities == sorted(capacities, reverse=True)
    hall = client.get(
        f"/datasets/{dataset_id}/tables/Rooms", params={"filter": "room_type:auditorium"}
    ).json()
    assert hall["total"] == 1
    assert client.get(f"/datasets/{dataset_id}/tables/Nope").status_code == 404


def test_a_room_is_edited_added_and_deleted(client: TestClient, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    room = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"][0]
    changed = client.patch(
        row_path(dataset_id, "Rooms", room["key"]), json={"values": {"capacity": 77}}
    )
    assert changed.status_code == 200, changed.text
    rows = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"]
    assert {r["key"]: r["values"]["capacity"] for r in rows}[room["key"]] == 77

    new = {**room["values"], "code": "NEW-ROOM", "capacity": 40}
    assert (
        client.post(f"/datasets/{dataset_id}/tables/Rooms", json={"values": new}).status_code == 201
    )
    duplicate = client.post(f"/datasets/{dataset_id}/tables/Rooms", json={"values": new})
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "duplicate_key"
    assert client.delete(row_path(dataset_id, "Rooms", "NEW-ROOM")).status_code == 204
    assert client.delete(row_path(dataset_id, "Rooms", "NEW-ROOM")).status_code == 404


def test_an_invalid_edit_returns_row_errors_and_changes_nothing(
    client: TestClient, l6_dataset
) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    room = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"][0]
    bad = client.patch(
        row_path(dataset_id, "Rooms", room["key"]), json={"values": {"building": "NOWHERE"}}
    )
    assert bad.status_code == 422
    error = bad.json()["error"]
    assert error["code"] == "invalid_table"
    assert error["details"][0]["sheet"] == "Rooms" and "NOWHERE" in error["details"][0]["message"]
    unknown = client.patch(row_path(dataset_id, "Rooms", room["key"]), json={"values": {"nope": 1}})
    assert unknown.json()["error"]["code"] == "unknown_column"
    after = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"][0]
    assert after == room


def test_a_note_column_survives_an_edit(client: TestClient, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    room = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"][0]
    path = row_path(dataset_id, "Rooms", room["key"])
    assert client.patch(path, json={"values": {"x_note": "projector"}}).status_code == 200
    page = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()
    assert "x_note" in page["headers"]
    assert client.patch(path, json={"values": {"capacity": 55}}).status_code == 200
    again = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"][0]["values"]
    assert again["x_note"] == "projector"


def test_preflight_reports_the_issues_of_the_dataset(client: TestClient, l6_dataset) -> None:
    dataset_id = import_dataset(client, l6_dataset)
    clean = client.post(f"/datasets/{dataset_id}/preflight").json()
    assert clean == {"issues": [], "has_errors": False}
    rooms = client.get(f"/datasets/{dataset_id}/tables/Rooms").json()["rows"]
    hall = next(r for r in rooms if r["values"]["room_type"] == "auditorium")
    client.delete(row_path(dataset_id, "Rooms", hall["key"]))
    broken = client.post(f"/datasets/{dataset_id}/preflight").json()
    assert broken["has_errors"]
    assert any(i["kind"] == "no_candidate" for i in broken["issues"])


def test_workbook_bytes_helper_matches_the_dataset(l6_dataset) -> None:
    assert workbook_bytes(l6_dataset)[:2] == b"PK"
