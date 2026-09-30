"""L6 written as configuration instead of activities (ADR-0007, P20.8).

The real L6 data gives modules, groups, rooms and teachers. For each module and session kind the
demand is derived from its activities (the assumptions, recorded in docs/STATUS.md):

- the participants are the groups that attend any activity of that module and kind;
- the limit is the most groups any one of those activities had (a lecture shared by 7 groups gives
  a limit of 7), so 19 groups in lectures of up to 7 make 3 blocks;
- `repeat` is the most activities one group attends of that module and kind (always 1 in L6);
- the room type is the one the activities asked for, and none for an online session;
- one teacher per session, chosen from every teacher of any activity of that module and kind.
"""

from collections import defaultdict

from tts.core.model import (
    CapacityRule,
    Dataset,
    Demand,
    PooledSpec,
)

GROUP_TYPE = "StudentGroup"
TEACHER_TYPE = "Teacher"
ROOM_TYPE = "Room"


def configured_l6(l6: Dataset, teacher_count: int = 1) -> Dataset:
    """The L6 dataset with its activities replaced by demands."""
    groups = {r.code for r in l6.resources if r.type == GROUP_TYPE}
    teachers = {r.code for r in l6.resources if r.type == TEACHER_TYPE}
    fixed: dict[str, list[str]] = defaultdict(list)
    for f in l6.fixed:
        fixed[f.event].append(f.resource)
    filters = {q.event: q.filter for q in l6.pooled}

    participants: dict[tuple[str, str], set[str]] = defaultdict(set)
    sizes: dict[tuple[str, str], int] = defaultdict(int)
    per_group: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pools: dict[tuple[str, str], set[str]] = defaultdict(set)
    rooms: dict[tuple[str, str], str | None] = {}
    online: dict[tuple[str, str], bool] = {}
    duration: dict[tuple[str, str], int] = {}
    patterns: dict[tuple[str, str], str] = {}
    for e in l6.events:
        key = (e.reference or e.code, e.kind)
        members = [r for r in fixed[e.code] if r in groups]
        participants[key] |= set(members)
        sizes[key] = max(sizes[key], len(members))
        for g in members:
            per_group[key][g] += 1
        pools[key] |= {r for r in fixed[e.code] if r in teachers}
        rooms[key] = filters.get(e.code)
        online[key] = e.delivery == "online"
        duration[key] = e.duration
        patterns[key] = e.start_pattern

    demands = []
    for key in sorted(participants):
        module, kind = key
        pooled: list[PooledSpec] = []
        if not online[key] and rooms[key] is not None:
            pooled.append(
                PooledSpec(
                    resource_type=ROOM_TYPE,
                    ordinal=0,
                    filter=rooms[key] or "all",
                    capacity_rule=CapacityRule.parse(f"sum_of_fixed:{GROUP_TYPE}"),
                )
            )
        if pools[key]:
            pooled.append(
                PooledSpec(
                    resource_type=TEACHER_TYPE,
                    ordinal=1,
                    count=teacher_count,
                    filter="code:"
                    + ",".join(f'"{t}"' if "," in t else t for t in sorted(pools[key])),
                )
            )
        demands.append(
            Demand(
                code=f"{module}-{kind}",
                kind=kind,
                reference=module,
                participants=tuple(sorted(participants[key])),
                max_participants=sizes[key],
                repeat=max(per_group[key].values()),
                duration=duration[key],
                start_pattern=patterns[key],
                delivery="online" if online[key] else "in_person",
                pooled=tuple(pooled),
            )
        )
    return l6.model_copy(
        update={
            "events": (),
            "fixed": (),
            "pooled": (),
            "pins": (),
            "templates": (),
            "demands": tuple(demands),
        }
    )
