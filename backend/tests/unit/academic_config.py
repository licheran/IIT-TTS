"""Builders for a small configured academic dataset (format version 2), shared by tests.

Level L6 has programmes P1 and P2 (P5 belongs to level L5). Modules: M1 (mandatory, LEC and TUT),
M2 (optional, for P1, TUT) and M3 (mandatory, for P2, LEC). Teacher T1 teaches M1, T2 teaches the
tutorials of M1 and M2, T3 teaches M3. Group P1/G1 takes the option M2.
"""

from datetime import time

from tts.core.model import Dataset, Day, Period, Reference, Resource, StartPattern, TimeModel
from tts.presets.academic_weekly import types


def resource(
    code: str, type_: str, parent: str | None = None, capacity: int | None = None, **attrs
):  # type: ignore[no-untyped-def]
    return Resource(
        code=code, type=type_, parent=parent, capacity=capacity, attributes=tuple(attrs.items())
    )


def module(code: str, level: str = "L6", **attrs):  # type: ignore[no-untyped-def]
    return Reference(code=code, type=types.MODULE, attributes=(("level", level), *attrs.items()))


def session_type(code: str, **attrs):  # type: ignore[no-untyped-def]
    base = {
        "start_pattern": "2H",
        "delivery": "in_person",
        "room_type": "lab",
        "teachers": 1,
        "weekly": 1,
    }
    base.update(attrs)
    return Reference(code=code, type=types.SESSION_TYPE, attributes=tuple(base.items()))


def dataset(**changes) -> Dataset:  # type: ignore[no-untyped-def]
    resources = [
        resource("L6", types.LEVEL),
        resource("L5", types.LEVEL),
        resource("P1", types.PROGRAMME, "L6"),
        resource("P2", types.PROGRAMME, "L6"),
        resource("P5", types.PROGRAMME, "L5"),
        resource("P1/G1", types.STUDENT_GROUP, "P1", 30, options="M2"),
        resource("P1/G2", types.STUDENT_GROUP, "P1", 30),
        resource("P2/G1", types.STUDENT_GROUP, "P2", 30),
        resource("T1", types.TEACHER, modules="M1"),
        resource("T2", types.TEACHER, modules="M1:TUT;M2"),
        resource("T3", types.TEACHER, modules="M3"),
    ]
    references = [
        session_type("LEC", max_groups=3),
        session_type("TUT", max_groups=1),
        module("M1", sessions="LEC;TUT"),
        module("M2", optional=True, programmes="P1", sessions="TUT"),
        module("M3", programmes="P2", sessions="LEC"),
    ]
    base = Dataset(
        preset="academic_weekly",
        resource_types=types.RESOURCE_TYPES,
        reference_types=types.REFERENCE_TYPES,
        resources=tuple(resources),
        references=tuple(references),
        time=TimeModel(
            days=tuple(
                Day(code=d, order=i) for i, d in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri"), 1)
            ),
            periods=tuple(
                Period(code=f"P{i}", start=time(7 + i, 0), end=time(8 + i, 0), order=i)
                for i in range(1, 5)
            ),
            start_patterns=(StartPattern(code="2H", duration=2, start_periods=("P1", "P3")),),
        ),
    )
    return base.model_copy(update=changes)


def replaced(ds: Dataset, code: str, **attrs) -> Dataset:  # type: ignore[no-untyped-def]
    """`ds` with the attributes of one row changed (resource or reference)."""

    def patch(row):  # type: ignore[no-untyped-def]
        if row.code != code:
            return row
        merged = dict(row.attributes)
        merged.update(attrs)
        return row.model_copy(update={"attributes": tuple(merged.items())})

    return ds.model_copy(
        update={
            "resources": tuple(patch(r) for r in ds.resources),
            "references": tuple(patch(r) for r in ds.references),
        }
    )
