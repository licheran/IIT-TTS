"""A write is committed before the client gets its answer.

A client that reads straight after a successful POST must see its own write. With the dependency
scoped to the request, FastAPI runs its exit code (the commit) after the response is sent, so the
follow-up read can race it. The e2e tests met this as a dataset missing from the list.
"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from tts.api.main import create_app
from tts.store.db import upgrade

pytestmark = pytest.mark.integration


async def post_and_watch(
    app: Any, path: str, payload: dict[str, Any], count_datasets: Callable[[], int]
) -> list[int]:
    """Call the app and, when the last body chunk is sent, count the datasets the database holds."""
    seen_at_send: list[int] = []
    body = json.dumps(payload).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json"), (b"host", b"test")],
        "server": ("test", 80),
        "client": ("test", 1),
    }
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.body" and not message.get("more_body"):
            seen_at_send.append(count_datasets())

    await app(scope, receive, send)
    return seen_at_send


def test_the_dataset_is_committed_before_the_response_is_sent(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'race.db'}"
    upgrade(url)
    app = create_app(url, migrate=False)

    def count_datasets() -> int:
        engine = create_engine(url)
        try:
            with engine.connect() as connection:
                return int(connection.execute(text("SELECT count(*) FROM dataset")).scalar_one())
        finally:
            engine.dispose()

    seen = asyncio.run(
        post_and_watch(
            app, "/datasets", {"name": "Race", "preset": "academic_weekly"}, count_datasets
        )
    )
    assert seen == [1], "the dataset was not yet in the database when the answer was sent"
