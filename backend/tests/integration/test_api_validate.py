from collections.abc import Iterator
from pathlib import Path

import pytest
from api_helpers import workbook_bytes
from fastapi.testclient import TestClient

from tts.api.main import create_app
from tts.core.model import Assignment, Result

pytestmark = pytest.mark.integration

FET = Path(__file__).parent.parent / "fixtures" / "l6" / "fet-groups-export.html"


@pytest.fixture
def client(db_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_url)) as c:
        yield c


def upload(client: TestClient, name: str, payload: bytes):
    return client.post("/validate", files={"file": (name, payload, "application/octet-stream")})


def test_the_fet_export_validates_with_no_violations(client: TestClient, l6_dataset) -> None:
    body = upload(client, "fet-groups-export.html", FET.read_bytes()).json()
    assert body["source"] == "fet"
    assert body["valid"] is True and body["hard"] == 0
    assert body["events"] == body["placed"] == len(l6_dataset.events)
    assert body["violations"] == []


def test_a_workbook_with_assignments_is_checked(
    client: TestClient, l6_dataset, l6_locked_result
) -> None:
    body = upload(client, "l6.xlsx", workbook_bytes(l6_dataset, l6_locked_result)).json()
    assert body["source"] == "workbook" and body["valid"] is True


def test_every_violation_is_reported(client: TestClient, l6_dataset, l6_locked_result) -> None:
    first, second = l6_locked_result.assignments[:2]
    # Put the second event exactly where the first is: they now share resources and a slot.
    broken = Result(
        assignments=(
            first,
            Assignment(
                event=second.event,
                day=first.day,
                start_period=first.start_period,
                chosen=first.chosen,
            ),
            *l6_locked_result.assignments[2:],
        )
    )
    body = upload(client, "l6.xlsx", workbook_bytes(l6_dataset, broken)).json()
    assert body["valid"] is False and body["hard"] >= 1
    assert any(v["constraint_code"] == "H1" for v in body["violations"])
    clash = next(v for v in body["violations"] if v["constraint_code"] == "H1")
    assert clash["refs"] and clash["message"]


def test_a_workbook_without_assignments_is_refused(client: TestClient, l6_dataset) -> None:
    response = upload(client, "l6.xlsx", workbook_bytes(l6_dataset))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_assignments"


def test_unreadable_files_get_a_clear_error(client: TestClient) -> None:
    bad = upload(client, "x.xlsx", b"not a workbook")
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_workbook"
    fet = upload(client, "x.html", b"<html><body>nothing here</body></html>")
    assert fet.status_code == 422 and fet.json()["error"]["code"] == "invalid_fet_export"
