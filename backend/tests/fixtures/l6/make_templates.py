"""Write `templates.xlsx`: the L6 dataset with its activities expressed as templates (P9.4).

Usage (from `backend/`): `uv run python tests/fixtures/l6/make_templates.py`

For each module and kind, single-group activities that share their teachers and room type become
one `per_group` template (a group appears once per template; a repeat starts another template).
An activity with several groups becomes a `joint` template of its own. The workbook holds no
activities, so expanding the templates is the only way to get them back.
"""

from collections import defaultdict
from pathlib import Path

from tts.core.model import Dataset, PooledSpec, Template
from tts.io.fet_html import parse_fet_groups_html, to_dataset
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.presets.academic_weekly import types

HERE = Path(__file__).parent


def selector(codes: list[str]) -> str:
    return "code:" + ",".join(f'"{c}"' for c in sorted(codes))


def as_templates(dataset: Dataset) -> Dataset:
    kinds = {r.code: r.type for r in dataset.resources}
    fixed: dict[str, list[str]] = defaultdict(list)
    for f in dataset.fixed:
        fixed[f.event].append(f.resource)
    pooled = {q.event: q for q in dataset.pooled}

    # (module, kind, teachers, pooled spec, pattern, duration) -> group lists, one per template
    singles: dict[tuple[object, ...], list[list[str]]] = defaultdict(list)
    templates: list[Template] = []
    counter: dict[tuple[str, str], int] = defaultdict(int)

    def new_code(module: str, kind: str) -> str:
        counter[(module, kind)] += 1
        return f"{module}-{kind}-T{counter[(module, kind)]:02d}"

    for event in dataset.events:
        groups = sorted(r for r in fixed[event.code] if kinds[r] == types.STUDENT_GROUP)
        teachers = tuple(sorted(r for r in fixed[event.code] if kinds[r] == types.TEACHER))
        requirement = pooled.get(event.code)
        spec = (
            None
            if requirement is None
            else PooledSpec(**requirement.model_dump(exclude={"event", "ordinal"}))
        )
        key = (event.reference, event.kind, teachers, spec, event.start_pattern, event.duration)
        if len(groups) == 1:
            for batch in singles[key]:
                if groups[0] not in batch:
                    batch.append(groups[0])
                    break
            else:
                singles[key].append(list(groups))
        else:
            templates.append(
                template(new_code(str(event.reference), event.kind), "joint", key, groups)
            )

    for key, batches in singles.items():
        for batch in batches:
            module, kind = str(key[0]), str(key[1])
            templates.append(template(new_code(module, kind), "each", key, batch))

    return dataset.model_copy(
        update={
            "events": (),
            "fixed": (),
            "pooled": (),
            "templates": tuple(sorted(templates, key=lambda t: t.code)),
        }
    )


def template(code: str, mode: str, key: tuple[object, ...], groups: list[str]) -> Template:
    module, kind, teachers, spec, pattern, duration = key
    return Template(
        code=code,
        kind=str(kind),
        mode=mode,
        reference=str(module),
        targets=selector(groups),
        fixed=teachers,  # type: ignore[arg-type]
        pooled=() if spec is None else (spec,),  # type: ignore[arg-type]
        duration=duration,  # type: ignore[arg-type]
        start_pattern=str(pattern),
    )


def main() -> None:
    dataset, _ = to_dataset(parse_fet_groups_html(HERE / "fet-groups-export.html"))
    out = HERE / "templates.xlsx"
    export_xlsx(
        WorkbookData(as_templates(dataset), meta={"note": "L6 expressed as templates"}), out
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
