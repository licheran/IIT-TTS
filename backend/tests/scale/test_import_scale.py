"""NFR-4: a workbook with 10,000 rows imports in 10 seconds or less."""

import io
import time
from datetime import time as clock

import pytest

from tts.core.model import (
    CapacityRule,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    PooledRequirement,
    Resource,
    StartPattern,
    TimeModel,
)
from tts.io.csvzip import export_csvzip, import_csvzip
from tts.io.tables import WorkbookData, build_tables
from tts.io.workbook import export_xlsx, import_xlsx
from tts.presets.academic_weekly.preset import PRESET

pytestmark = pytest.mark.scale

LIMIT_SECONDS = 10.0
ROOM_RULE = CapacityRule.parse("sum_of_fixed:StudentGroup")


def big_dataset(events: int = 3000, groups: int = 1500, teachers: int = 1500) -> Dataset:
    """About 15,000 rows over Groups, Teachers, Rooms, Activities and the two join sheets."""
    resources = [Resource(code="PR", type="Programme")]
    resources += [
        Resource(code=f"G{i}", type="StudentGroup", parent="PR", capacity=30) for i in range(groups)
    ]
    resources += [
        Resource(code=f"T{i}", type="Teacher", name=f"Teacher {i}") for i in range(teachers)
    ]
    resources += [
        Resource(code=f"R{i}", type="Room", capacity=60, tags={"room_type": "lab"})
        for i in range(200)
    ]
    fixed: list[FixedRequirement] = []
    pooled: list[PooledRequirement] = []
    scheduled: list[Event] = []
    for i in range(events):
        code = f"A{i}"
        scheduled.append(Event(code=code, kind="LEC", duration=1, start_pattern="1H"))
        fixed += [
            FixedRequirement(event=code, resource=f"G{i % groups}"),
            FixedRequirement(event=code, resource=f"G{(i + 1) % groups}"),
            FixedRequirement(event=code, resource=f"T{i % teachers}"),
        ]
        pooled.append(
            PooledRequirement(
                event=code,
                resource_type="Room",
                filter="tag:room_type=lab",
                capacity_rule=ROOM_RULE,
            )
        )
    return Dataset(
        preset="academic_weekly",
        resource_types=PRESET.resource_types,
        reference_types=PRESET.reference_types,
        resources=tuple(resources),
        time=TimeModel(
            days=(Day(code="Mon", order=1),),
            periods=(Period(code="P1", start=clock(8), end=clock(9), order=1),),
            start_patterns=(StartPattern(code="1H", duration=1, start_periods=("P1",)),),
        ),
        events=tuple(scheduled),
        fixed=tuple(fixed),
        pooled=tuple(pooled),
    )


def test_ten_thousand_rows_import_from_xlsx_in_ten_seconds() -> None:
    data = WorkbookData(big_dataset())
    assert sum(len(t.rows) for t in build_tables(data, PRESET)) >= 10_000
    buffer = io.BytesIO()
    export_xlsx(data, buffer)
    content = buffer.getvalue()

    started = time.perf_counter()
    outcome = import_xlsx(content)
    elapsed = time.perf_counter() - started

    assert outcome.ok, [e.format() for e in outcome.errors[:5]]
    assert outcome.data == data
    assert elapsed <= LIMIT_SECONDS, f"import took {elapsed:.1f} s"


def test_ten_thousand_rows_import_from_a_csv_zip_in_ten_seconds() -> None:
    data = WorkbookData(big_dataset())
    buffer = io.BytesIO()
    export_csvzip(data, buffer)
    content = buffer.getvalue()

    started = time.perf_counter()
    outcome = import_csvzip(content)
    elapsed = time.perf_counter() - started

    assert outcome.ok, [e.format() for e in outcome.errors[:5]]
    assert outcome.data == data
    assert elapsed <= LIMIT_SECONDS, f"import took {elapsed:.1f} s"
