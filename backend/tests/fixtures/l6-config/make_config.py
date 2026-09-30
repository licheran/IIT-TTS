"""Write `l6-config.xlsx`: L6 as a configured dataset, workbook format version 2 (P21.6, ADR-0007).

Usage (from `backend/`): `uv run python tests/fixtures/l6-config/make_config.py`

The real L6 export gives the modules, groups, teachers and rooms. Its hand-made activities become
configuration, and the solver makes the sessions again. The assumptions (also written to `_meta`):

- a **session type** for each kind (LEC, TUT) with the settings most modules of that kind share;
  a module overrides what differs, for example `LEC(max_groups=7)`;
- the groups of a module and kind are the groups that attend any of its activities;
- `max_groups` is the most groups any one of its activities had (a lecture shared by 7 groups
  gives 7), and `weekly` the most activities one group attends (1 in L6);
- a module is **mandatory** when every group of its programmes takes it, **optional** otherwise,
  and then each group that takes it lists it in `options`;
- a teacher teaches the modules (or module and kind, `module:KIND`) they took in L6, and the
  solver chooses which of them takes each session: one teacher per session.
"""

from collections import Counter, defaultdict
from pathlib import Path

from tts.core.model import Dataset, Reference, Resource
from tts.io.fet_html import parse_fet_groups_html, to_dataset
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.presets.academic_weekly import types

HERE = Path(__file__).parent
L6_EXPORT = HERE.parent / "l6" / "fet-groups-export.html"

ASSUMPTIONS = (
    "L6 (SE and CS) written as configuration. Session types LEC and TUT hold the settings most "
    "modules share and a module overrides the rest. Groups per session and sessions per week "
    "are the most the real activities had. A module is optional when a group of its programmes "
    "does not take it. Teachers list the modules they taught; the solver chooses among them. "
    "Group size 30, room capacities, room types and the break period are the assumptions of the "
    "L6 fixture."
)


def _settings(reference: Reference) -> dict[str, object]:
    return dict(reference.attributes)


def as_configuration(dataset: Dataset) -> Dataset:
    kinds = {r.code: r.type for r in dataset.resources}
    groups = {r.code: r for r in dataset.resources if r.type == types.STUDENT_GROUP}
    members: dict[str, list[str]] = defaultdict(list)
    for f in dataset.fixed:
        members[f.event].append(f.resource)
    room_of = {q.event: q.filter for q in dataset.pooled}

    # What each (module, kind) looked like in the real timetable.
    shared: dict[tuple[str, str], int] = defaultdict(int)
    weekly: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    takers: dict[str, set[str]] = defaultdict(set)
    teachers: dict[str, set[tuple[str, str]]] = defaultdict(set)
    online: dict[tuple[str, str], bool] = {}
    room_type: dict[tuple[str, str], str] = {}
    for e in dataset.events:
        key = (str(e.reference), e.kind)
        attending = [r for r in members[e.code] if kinds[r] == types.STUDENT_GROUP]
        shared[key] = max(shared[key], len(attending))
        for g in attending:
            weekly[key][g] += 1
        takers[key[0]] |= set(attending)
        for r in members[e.code]:
            if kinds[r] == types.TEACHER:
                teachers[r].add(key)
        online[key] = online.get(key, False) or e.delivery == types.ONLINE
        wanted = room_of.get(e.code, "")
        if wanted.startswith("tag:room_type="):
            room_type[key] = wanted.removeprefix("tag:room_type=")

    # The session type of each kind: the settings most modules of that kind share.
    by_kind: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key in shared:
        by_kind[key[1]].append(key)
    base: dict[str, dict[str, object]] = {}
    for kind, keys in sorted(by_kind.items()):
        pattern = next(e.start_pattern for e in dataset.events if e.kind == kind)
        most = Counter(shared[k] for k in keys).most_common(1)[0][0]
        base[kind] = {
            "start_pattern": pattern,
            "delivery": types.IN_PERSON,
            "room_type": Counter(room_type[k] for k in keys if k in room_type).most_common(1)[0][0],
            "max_groups": most,
            "teachers": 1,
            "weekly": 1,
        }
    session_types = [
        Reference(code=kind, type=types.SESSION_TYPE, attributes=tuple(settings.items()))
        for kind, settings in base.items()
    ]

    # Modules: one level, mandatory unless some group of its programmes does not take it.
    programme_groups: dict[str, set[str]] = defaultdict(set)
    for g in groups.values():
        programme_groups[str(g.parent)].add(g.code)
    modules: list[Reference] = []
    optional: set[str] = set()
    for code in sorted(takers):
        programmes = sorted({str(groups[g].parent) for g in takers[code]})
        full = all(programme_groups[p] <= takers[code] for p in programmes)
        if not full:
            optional.add(code)
        items = []
        for kind in sorted(base):
            key = (code, kind)
            if key not in shared:
                continue
            changes = []
            if shared[key] != base[kind]["max_groups"]:
                changes.append(f"max_groups={shared[key]}")
            if online[key]:
                changes.append("delivery=online")
            elif room_type.get(key) != base[kind]["room_type"]:
                changes.append(f"room_type={room_type[key]}")
            per_week = max(weekly[key].values())
            if per_week != 1:
                changes.append(f"weekly={per_week}")
            items.append(f"{kind}({','.join(changes)})" if changes else kind)
        attributes: list[tuple[str, object]] = [
            ("level", "L6"),
            ("optional", not full),
            ("programmes", ";".join(programmes)),
            ("sessions", ";".join(items)),
        ]
        modules.append(Reference(code=code, type=types.MODULE, attributes=tuple(attributes)))

    resources: list[Resource] = []
    for r in dataset.resources:
        attributes = dict(r.attributes)
        if r.type == types.STUDENT_GROUP:
            taken = sorted(m for m in optional if r.code in takers[m])
            if taken:
                attributes["options"] = ";".join(taken)
        if r.type == types.TEACHER:
            attributes["modules"] = ";".join(_teacher_modules(teachers[r.code], by_kind, shared))
        resources.append(r.model_copy(update={"attributes": tuple(attributes.items())}))

    return dataset.model_copy(
        update={
            "events": (),
            "fixed": (),
            "pooled": (),
            "pins": (),
            "templates": (),
            "demands": (),
            "resources": tuple(resources),
            "references": tuple(sorted([*session_types, *modules], key=lambda x: x.code)),
        }
    )


def _teacher_modules(
    taught: set[tuple[str, str]],
    by_kind: dict[str, list[tuple[str, str]]],
    shared: dict[tuple[str, str], int],
) -> list[str]:
    """`module` when the teacher took every kind the module has, else `module:KIND` for each."""
    per_module: dict[str, set[str]] = defaultdict(set)
    for module, kind in taught:
        per_module[module].add(kind)
    out = []
    for module in sorted(per_module):
        every = {kind for kind in by_kind if (module, kind) in shared}
        if per_module[module] == every:
            out.append(module)
        else:
            out.extend(f"{module}:{kind}" for kind in sorted(per_module[module]))
    return out


def build() -> Dataset:
    dataset, _ = to_dataset(parse_fet_groups_html(L6_EXPORT))
    return as_configuration(dataset)


def main() -> None:
    out = HERE / "l6-config.xlsx"
    export_xlsx(WorkbookData(build(), meta={"assumptions": ASSUMPTIONS}), out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
