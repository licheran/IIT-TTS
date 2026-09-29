import pytest
from fastapi.testclient import TestClient

from tts.api.main import app

pytestmark = pytest.mark.integration


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
