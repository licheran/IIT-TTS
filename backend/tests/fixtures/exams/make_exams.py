"""Write `exams.xlsx`: a small exam session for the exams preset (P11.2).

Usage (from `backend/`): `uv run python tests/fixtures/exams/make_exams.py`

Two weeks of dated exam days with a morning and an afternoon session, eight cohorts, four halls
and twelve invigilators. Each paper is sat by one or two cohorts and needs one invigilator per
60 candidates (rounded up), written in its `invigilators` column. All sizes are made up.
"""

import math
from datetime import date, time, timedelta
from pathlib import Path

from tts.core.model import (
    Availability,
    CapacityRule,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    PooledRequirement,
    Reference,
    Resource,
    StartPattern,
    TimeModel,
)
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.presets.exams import PRESET_NAME, types
from tts.presets.exams.defaults import with_defaults

HERE = Path(__file__).parent
FIRST_DAY = date(2026, 6, 1)  # a Monday
PER_INVIGILATOR = 60

COHORTS = {
    "BSC-CS-1": 160, "BSC-CS-2": 140, "BSC-SE-1": 120, "BSC-SE-2": 90,
    "BSC-DS-1": 70, "BSC-DS-2": 60, "MSC-AI": 45, "MSC-DS": 40,
}  # fmt: skip
HALLS = {"MAIN-HALL": 320, "HALL-B": 160, "HALL-C": 120, "EXAM-ROOM": 60}
INVIGILATORS = [f"INV{n:02d}" for n in range(1, 13)]

PAPERS = [  # (paper, minutes, cohorts)
    ("CS101", 180, ["BSC-CS-1"]),
    ("CS102", 120, ["BSC-CS-1"]),
    ("CS103", 120, ["BSC-CS-1", "BSC-SE-1"]),
    ("CS201", 180, ["BSC-CS-2"]),
    ("CS202", 120, ["BSC-CS-2"]),
    ("CS203", 120, ["BSC-CS-2", "BSC-SE-2"]),
    ("SE101", 120, ["BSC-SE-1"]),
    ("SE102", 180, ["BSC-SE-1"]),
    ("SE201", 120, ["BSC-SE-2"]),
    ("SE202", 180, ["BSC-SE-2"]),
    ("DS101", 120, ["BSC-DS-1"]),
    ("DS102", 120, ["BSC-DS-1", "BSC-CS-1"]),
    ("DS201", 180, ["BSC-DS-2"]),
    ("DS202", 120, ["BSC-DS-2"]),
    ("MA101", 120, ["BSC-CS-1", "BSC-DS-1"]),
    ("MA201", 120, ["BSC-CS-2", "BSC-DS-2"]),
    ("AI501", 180, ["MSC-AI"]),
    ("AI502", 120, ["MSC-AI"]),
    ("AI503", 120, ["MSC-AI", "MSC-DS"]),
    ("DS501", 180, ["MSC-DS"]),
    ("DS502", 120, ["MSC-DS"]),
    ("PR101", 120, ["BSC-SE-1", "BSC-DS-1"]),
    ("PR201", 120, ["BSC-SE-2", "BSC-CS-2"]),
    ("ET500", 60, ["MSC-AI"]),
]


def exam_days() -> list[date]:
    days, current = [], FIRST_DAY
    while len(days) < 10:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def build() -> Dataset:
    days = exam_days()
    time_model = TimeModel(
        days=tuple(
            Day(code=d.isoformat(), label=d.strftime("%a %d %b"), order=i + 1)
            for i, d in enumerate(days)
        ),
        periods=(
            Period(code="AM", start=time(9, 0), end=time(12, 0), order=1),
            Period(code="PM", start=time(14, 0), end=time(17, 0), order=2),
        ),
        start_patterns=(StartPattern(code="SESSION", duration=1, start_periods=("AM", "PM")),),
    )
    resources = [
        *(Resource(code=c, type=types.COHORT, capacity=size) for c, size in COHORTS.items()),
        *(Resource(code=h, type=types.HALL, capacity=cap) for h, cap in HALLS.items()),
        *(Resource(code=i, type=types.INVIGILATOR) for i in INVIGILATORS),
    ]
    events, fixed, pooled = [], [], []
    for paper, _minutes, cohorts in PAPERS:
        code = f"{paper}-EXAM"
        size = sum(COHORTS[c] for c in cohorts)
        events.append(
            Event(code=code, kind=types.EXAM, duration=1, start_pattern="SESSION", reference=paper)
        )
        fixed += [FixedRequirement(event=code, resource=c) for c in cohorts]
        pooled.append(
            PooledRequirement(
                event=code,
                resource_type=types.HALL,
                capacity_rule=CapacityRule.parse(f"sum_of_fixed:{types.COHORT}"),
            )
        )
        pooled.append(
            PooledRequirement(
                event=code,
                resource_type=types.INVIGILATOR,
                ordinal=1,
                count=math.ceil(size / PER_INVIGILATOR),
            )
        )
    first = days[0].isoformat()
    availability = [
        Availability(resource="INV01", day=first, period="AM", status="unavailable"),
        Availability(resource="INV01", day=first, period="PM", status="unavailable"),
        Availability(resource="HALL-C", day=days[4].isoformat(), period="PM", status="unavailable"),
    ]
    dataset = Dataset(
        preset=PRESET_NAME,
        resource_types=types.RESOURCE_TYPES,
        reference_types=types.REFERENCE_TYPES,
        resources=tuple(resources),
        references=tuple(
            Reference(code=p, type=types.PAPER, attributes={"minutes": m}) for p, m, _ in PAPERS
        ),
        time=time_model,
        events=tuple(events),
        fixed=tuple(fixed),
        pooled=tuple(pooled),
        availability=tuple(availability),
    )
    return with_defaults(dataset)


def main() -> None:
    out = HERE / "exams.xlsx"
    export_xlsx(WorkbookData(build(), meta={"institution": "Sample exam session"}), out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
