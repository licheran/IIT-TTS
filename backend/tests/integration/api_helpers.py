"""Helpers for the API integration tests."""

from io import BytesIO
from urllib.parse import quote

from fastapi.testclient import TestClient

from tts.core.model import Dataset, Result
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx


def workbook_bytes(dataset: Dataset, result: Result | None = None) -> bytes:
    buffer = BytesIO()
    export_xlsx(WorkbookData(dataset, result), buffer)
    return buffer.getvalue()


def create_dataset(client: TestClient, name: str = "L6") -> int:
    response = client.post("/datasets", json={"name": name, "preset": "academic_weekly"})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def import_dataset(client: TestClient, dataset: Dataset, name: str = "L6") -> int:
    dataset_id = create_dataset(client, name)
    files = {"file": ("l6.xlsx", workbook_bytes(dataset), "application/octet-stream")}
    response = client.post(f"/datasets/{dataset_id}/import", files=files)
    assert response.status_code == 200, response.text
    assert response.json()["ok"], response.json()
    return dataset_id


def row_path(dataset_id: int, sheet: str, key: str) -> str:
    return f"/datasets/{dataset_id}/tables/{sheet}/{quote(key, safe='')}"
