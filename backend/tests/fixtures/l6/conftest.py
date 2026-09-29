"""Fixtures for the L6 regression dataset (a real FET export, see README.md in this folder).

Everything is built once per session from `fet-groups-export.html`. The models are frozen, so a
test cannot change a fixture in place.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from tts.core.model import Dataset, Result
from tts.io.fet_html import FetTimetable, parse_fet_groups_html, to_dataset

L6_DIR = Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def l6_expected() -> dict[str, Any]:
    """The figures measured from the export (`expected.json`)."""
    return json.loads((L6_DIR / "expected.json").read_text("utf-8"))  # type: ignore[no-any-return]


@pytest.fixture(scope="session")
def l6_fet() -> FetTimetable:
    return parse_fet_groups_html(L6_DIR / "fet-groups-export.html")


@pytest.fixture(scope="session")
def l6_converted(l6_fet: FetTimetable) -> tuple[Dataset, Result]:
    return to_dataset(l6_fet)


@pytest.fixture(scope="session")
def l6_dataset(l6_converted: tuple[Dataset, Result]) -> Dataset:
    """The L6 SE + CS dataset, with the assumptions of `Assumptions()`."""
    return l6_converted[0]


@pytest.fixture(scope="session")
def l6_locked_result(l6_converted: tuple[Dataset, Result]) -> Result:
    """The original FET placements: every event's day, start and room."""
    return l6_converted[1]
