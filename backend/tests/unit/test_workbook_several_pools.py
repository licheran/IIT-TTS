"""Several pooled requirements per sheet row (ADR-0006).

A copy of the academic preset whose Activities sheet also asks for a number of helpers: any
teachers, counted in a `helpers` column. The academic format itself is unchanged.
"""

from datetime import time
from io import BytesIO

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
from tts.core.sheets import ColumnDef, PooledMapping
from tts.io.tables import WorkbookData, WorkbookExportError, build_tables
from tts.io.workbook import export_xlsx, import_xlsx
from tts.presets.academic_weekly.preset import PRESET

HELPERS = PooledMapping(resource_type="Teacher", capacity_rule="none", count_column="helpers")


def with_helpers():
    sheets = []
    for sheet in PRESET.sheets:
        if sheet.name == "Activities":
            helpers = ColumnDef(
                name="helpers", field="pooled_count:1", kind="int", minimum=0, default=0
            )
            sheet = sheet.model_copy(
                update={"columns": (*sheet.columns, helpers), "more_pooled": (HELPERS,)}
            )
        sheets.append(sheet)
    return PRESET.model_copy(update={"sheets": tuple(sheets)})


PRESET2 = with_helpers()
ROOM = PooledRequirement(
    event="E1",
    resource_type="Room",
    filter="tag:room_type=lab",
    capacity_rule=CapacityRule.parse("sum_of_fixed:StudentGroup"),
)


def dataset(*pooled: PooledRequirement) -> Dataset:
    return Dataset(
        preset="academic_weekly",
        resource_types=PRESET.resource_types,
        reference_types=PRESET.reference_types,
        resources=(
            Resource(code="PR1", type="Programme"),
            Resource(code="G1", type="StudentGroup", parent="PR1", capacity=10),
            Resource(code="R1", type="Room", capacity=20, tags={"room_type": "lab"}),
            Resource(code="T1", type="Teacher"),
            Resource(code="T2", type="Teacher"),
        ),
        events=(Event(code="E1", kind="LEC", duration=1, start_pattern="1H"),),
        fixed=(FixedRequirement(event="E1", resource="G1"),),
        pooled=pooled,
        time=TimeModel(
            days=(Day(code="Mon", order=1),),
            periods=(Period(code="P01", start=time(9), end=time(10), order=1),),
            start_patterns=(StartPattern(code="1H", duration=1, start_periods=("P01",)),),
        ),
    )


def round_trip(ds: Dataset) -> Dataset:
    buffer = BytesIO()
    export_xlsx(WorkbookData(ds), buffer, PRESET2)
    outcome = import_xlsx(buffer.getvalue(), PRESET2)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data is not None
    return outcome.data.dataset


def test_a_second_untyped_requirement_round_trips() -> None:
    helpers = PooledRequirement(
        event="E1", resource_type="Teacher", ordinal=1, count=2, capacity_rule=CapacityRule()
    )
    ds = dataset(ROOM, helpers)
    assert round_trip(ds) == ds


def test_a_count_of_zero_means_no_requirement() -> None:
    ds = dataset(ROOM)
    assert round_trip(ds) == ds  # written as helpers = 0, read back as nothing
    activities = next(t for t in build_tables(WorkbookData(ds), PRESET2) if t.name == "Activities")
    assert dict(zip(activities.headers, activities.rows[0], strict=True))["helpers"] == 0


def test_a_filtered_requirement_on_an_untyped_mapping_is_refused() -> None:
    picky = PooledRequirement(
        event="E1",
        resource_type="Teacher",
        ordinal=1,
        filter="code:T1",
        capacity_rule=CapacityRule(),
    )
    with pytest.raises(WorkbookExportError, match='only "all"'):
        build_tables(WorkbookData(dataset(ROOM, picky)), PRESET2)
