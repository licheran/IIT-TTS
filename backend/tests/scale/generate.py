"""A synthetic institute for the scale tests (P10.1), feasible by construction.

`generate(ScaleParams(...), seed)` builds universities, levels, programmes and groups (sizes
20-60), campuses, buildings and rooms (labs and lecture halls, capacities 30-120), teachers (some
shared across the whole institute, the rest local to one programme), and for every programme and
level a set of modules, each with lectures (groups batched so a batch fits the largest hall) and
one tutorial per group. While it creates the activities it places each one in a hidden timetable,
picking a start, a free teacher and a free room of the right type and size, so a timetable with no
hard violation is known to exist. The hidden timetable is returned too.

Usage: `uv run python tests/scale/generate.py <out.xlsx> [--small]` writes the dataset as a
workbook (without the hidden timetable).
"""

import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

from tts.core.model import (
    Assignment,
    CapacityRule,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    PooledChoice,
    PooledRequirement,
    Reference,
    Resource,
    Result,
    StartPattern,
    TimeModel,
)
from tts.core.timegrid import TimeGrid
from tts.presets.academic_weekly import PRESET_NAME, types

LAB, HALL = "lab", "hall"
GROUP_SIZE = (20, 60)
LAB_CAPACITY = (40, 70)
HALL_CAPACITY = (80, 120)


@dataclass(frozen=True)
class ScaleParams:
    universities: tuple[str, ...] = ("UOW", "RGU")
    levels: tuple[str, ...] = ("L4", "L5", "L6", "L7")
    programmes: tuple[str, ...] = ("CS", "SE", "BDS", "AIDS")
    groups_per_programme: int = 9
    modules_per_level: int = 6  # per programme
    shared_teacher_share: float = 0.3
    teachers: int = 260
    buildings: tuple[str, ...] = ("GP", "JAVA", "RAMA", "DIALOG", "SPENCER")
    rooms_per_building: int = 36
    lab_share: float = 0.7
    days: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


SMALL = ScaleParams(
    universities=("UOW",),
    levels=("L5", "L6"),
    programmes=("CS", "SE"),
    groups_per_programme=4,
    modules_per_level=3,
    teachers=24,
    buildings=("GP", "JAVA"),
    rooms_per_building=8,
)


@dataclass
class Generated:
    dataset: Dataset
    hidden: Result
    events_by_level: dict[str, list[str]] = field(default_factory=dict)


def time_model(days: tuple[str, ...]) -> TimeModel:
    """Hourly periods from 08:30 with a lunch break at 12:30 and 2-hour blocks (as L6)."""
    periods = []
    for i in range(14):
        start = time(8 + i, 30)
        end = time(9 + i, 30)
        periods.append(
            Period(code=f"P{i + 1:02d}", start=start, end=end, order=i + 1, is_break=i == 4)
        )
    starts = ("P01", "P03", "P06", "P08", "P10", "P12")
    return TimeModel(
        days=tuple(Day(code=d, label=d, order=i + 1) for i, d in enumerate(days)),
        periods=tuple(periods),
        start_patterns=(StartPattern(code="2H", duration=2, start_periods=starts),),
    )


class _Placer:
    """Occupancy of the hidden timetable."""

    def __init__(self, grid: TimeGrid, starts: list[int], rng: random.Random) -> None:
        self.grid = grid
        self.starts = starts
        self.rng = rng
        self.busy: dict[str, set[int]] = defaultdict(set)

    def free(self, resource: str, slots: range) -> bool:
        return self.busy[resource].isdisjoint(slots)

    def place(
        self,
        groups: list[str],
        teachers: list[str],
        rooms: list[str],
    ) -> tuple[int, str, str] | None:
        """A start, a teacher and a room that are all free, or None."""
        order = self.starts[:]
        self.rng.shuffle(order)
        for t in order:
            slots = range(t, t + 2)
            if not all(self.free(g, slots) for g in groups):
                continue
            teacher = next((x for x in teachers if self.free(x, slots)), None)
            room = next((r for r in rooms if self.free(r, slots)), None)
            if teacher is None or room is None:
                continue
            for resource in (*groups, teacher, room):
                self.busy[resource].update(slots)
            return t, teacher, room
        return None


def generate(params: ScaleParams | None = None, seed: int = 0) -> Generated:
    params = params or ScaleParams()
    rng = random.Random(seed)
    time_ = time_model(params.days)
    grid = TimeGrid(time_)
    pattern = time_.start_patterns[0]
    starts = [grid.slot(d.code, p) for d in time_.days for p in pattern.start_periods]
    placer = _Placer(grid, starts, rng)

    resources: list[Resource] = [Resource(code="MAIN", type=types.CAMPUS)]
    rooms: dict[str, list[tuple[str, int]]] = {LAB: [], HALL: []}
    for building in params.buildings:
        resources.append(Resource(code=building, type=types.BUILDING, parent="MAIN"))
        for n in range(params.rooms_per_building):
            kind = LAB if rng.random() < params.lab_share else HALL
            low, high = LAB_CAPACITY if kind == LAB else HALL_CAPACITY
            code = f"{building}-{n + 1:02d}"
            capacity = rng.randint(low, high)
            rooms[kind].append((code, capacity))
            resources.append(
                Resource(
                    code=code,
                    type=types.ROOM,
                    parent=building,
                    capacity=capacity,
                    tags={types.ROOM_TYPE_TAG: kind},
                )
            )

    teachers = [f"T{n:03d}" for n in range(params.teachers)]
    resources += [Resource(code=t, type=types.TEACHER) for t in teachers]
    shared_count = int(len(teachers) * params.shared_teacher_share)
    shared, local = teachers[:shared_count], teachers[shared_count:]

    references: list[Reference] = []
    events: list[Event] = []
    fixed: list[FixedRequirement] = []
    pooled: list[PooledRequirement] = []
    assignments: list[Assignment] = []
    by_level: dict[str, list[str]] = defaultdict(list)
    units = [
        (u, lv, pr) for u in params.universities for lv in params.levels for pr in params.programmes
    ]
    local_share = max(1, len(local) // max(1, len(units)))

    for index, (uni, level, programme) in enumerate(units):
        if not any(r.code == uni for r in resources):
            resources.append(Resource(code=uni, type=types.UNIVERSITY))
        level_code = f"{uni} {level}"
        if not any(r.code == level_code for r in resources):
            resources.append(Resource(code=level_code, type=types.LEVEL, parent=uni))
        prog_code = f"{uni} {level} {programme}"
        resources.append(Resource(code=prog_code, type=types.PROGRAMME, parent=level_code))
        groups: list[tuple[str, int]] = []
        for g in range(params.groups_per_programme):
            code = f"{prog_code} / G{g + 1}"
            size = rng.randint(*GROUP_SIZE)
            groups.append((code, size))
            resources.append(
                Resource(code=code, type=types.STUDENT_GROUP, parent=prog_code, capacity=size)
            )
        pool = local[index * local_share : (index + 1) * local_share] + shared

        for m in range(params.modules_per_level):
            module = f"{uni}-{level}-{programme}-M{m + 1}"
            references.append(Reference(code=module, type=types.MODULE))
            batches: list[list[tuple[str, int]]] = [[]]
            for group in groups:
                if sum(s for _, s in batches[-1]) + group[1] > HALL_CAPACITY[0]:
                    batches.append([])
                batches[-1].append(group)
            lectures = [
                (types.LECTURE, HALL, [g for g, _ in b], sum(s for _, s in b)) for b in batches if b
            ]
            tutorials = [(types.TUTORIAL, LAB, [g], s) for g, s in groups]
            for n, (kind, room_type, members, size) in enumerate([*lectures, *tutorials]):
                code = f"{module}-{kind}-{n + 1:02d}"
                candidates = [c for c, capacity in rooms[room_type] if capacity >= size]
                rng.shuffle(candidates)
                team = pool[:]
                rng.shuffle(team)
                found = placer.place(members, team, candidates)
                if found is None:
                    raise RuntimeError(f"no room in the hidden timetable for {code}; add rooms")
                t, teacher, room = found
                day, period = grid.codes(t)
                events.append(
                    Event(code=code, kind=kind, duration=2, start_pattern="2H", reference=module)
                )
                fixed += [FixedRequirement(event=code, resource=r) for r in (*members, teacher)]
                pooled.append(
                    PooledRequirement(
                        event=code,
                        resource_type=types.ROOM,
                        filter=f"tag:{types.ROOM_TYPE_TAG}={room_type}",
                        capacity_rule=CapacityRule.parse(f"sum_of_fixed:{types.STUDENT_GROUP}"),
                    )
                )
                assignments.append(
                    Assignment(
                        event=code,
                        day=day,
                        start_period=period,
                        chosen=(PooledChoice(ordinal=0, resources=(room,)),),
                    )
                )
                by_level[level].append(code)

    dataset = Dataset(
        preset=PRESET_NAME,
        resource_types=types.RESOURCE_TYPES,
        resources=tuple(resources),
        reference_types=types.REFERENCE_TYPES,
        references=tuple(references),
        time=time_,
        events=tuple(events),
        fixed=tuple(fixed),
        pooled=tuple(pooled),
    )
    return Generated(dataset, Result(assignments=tuple(assignments)), dict(by_level))


def main() -> None:
    from tts.io.tables import WorkbookData
    from tts.io.workbook import export_xlsx

    out = Path(sys.argv[1])
    params = SMALL if "--small" in sys.argv else ScaleParams()
    made = generate(params)
    export_xlsx(WorkbookData(made.dataset, meta={"note": "synthetic institute (tests/scale)"}), out)
    print(
        f"wrote {out}: {len(made.dataset.events)} events, {len(made.dataset.resources)} resources"
    )


if __name__ == "__main__":
    main()
