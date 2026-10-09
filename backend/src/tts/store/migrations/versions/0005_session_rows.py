"""a module's sessions become rows of the Session table (ADR-0007, Amendment 1, Phase 24)

A configured academic dataset used to keep each module's session types in the module's `sessions`
attribute, for example `LEC;TUT;LAB(start_pattern=3H,max_groups=2)`. They are now references of
the type `Session`, one for each module and session type, with the settings the item overrode.
The dataset's reference types change with it: `Session` is added and `Module` loses `sessions`.

The old text is read here with its own copy of the old parser, so this migration does not depend
on the preset's code. An entry that cannot be read is dropped (the importer never let one in).

Revision ID: 0005
Revises: 0004
"""

import json
import re
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SESSION = "Session"
SETTINGS = ("start_pattern", "delivery", "room_type", "max_groups", "teachers", "weekly")
NUMBERS = ("max_groups", "teachers", "weekly")
ITEM = re.compile(r"^(?P<code>[^()]+?)\s*(?:\((?P<settings>.*)\))?$")

reference = sa.table(
    "reference",
    sa.column("id", sa.Integer),
    sa.column("dataset_id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("type", sa.String),
    sa.column("name", sa.Text),
    sa.column("attributes", sa.JSON),
    sa.column("tags", sa.JSON),
)
reference_type = sa.table(
    "reference_type",
    sa.column("id", sa.Integer),
    sa.column("dataset_id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.Text),
    sa.column("attribute_schema", sa.JSON),
)

SESSION_SCHEMA: list[dict[str, Any]] = [
    {"name": name, "kind": kind}
    for name, kind in (
        ("module", "str"),
        ("session_type", "str"),
        ("start_pattern", "str"),
        ("delivery", "str"),
        ("room_type", "str"),
        ("max_groups", "int"),
        ("teachers", "int"),
        ("weekly", "int"),
    )
]


def parse_item(text: str) -> tuple[str, dict[str, object]] | None:
    """The old `Modules.sessions` item as (session type, overrides), or None if unreadable."""
    match = ITEM.match(text.strip())
    if match is None:
        return None
    settings: dict[str, object] = {}
    if match["settings"] is not None:
        for part in match["settings"].split(","):
            if not part.strip():
                continue
            name, equals, value = part.partition("=")
            if not equals or name.strip() not in SETTINGS:
                return None
            value = value.strip()
            if name.strip() in NUMBERS:
                if not re.fullmatch(r"[+-]?\d+", value):
                    return None
                settings[name.strip()] = int(value)
            else:
                settings[name.strip()] = value
    return match["code"].strip(), settings


def pairs(value: Any) -> list[list[Any]]:
    loaded = json.loads(value) if isinstance(value, str) else value
    return [list(p) for p in loaded or []]


def upgrade() -> None:
    bind = op.get_bind()
    modules = bind.execute(
        sa.select(reference.c.id, reference.c.dataset_id, reference.c.code, reference.c.attributes)
        .where(reference.c.type == "Module")
        .order_by(reference.c.id)
    ).all()
    touched: set[int] = set()
    for row_id, dataset_id, code, attributes in modules:
        attrs = pairs(attributes)
        if not any(name == "sessions" for name, _ in attrs):
            continue
        touched.add(dataset_id)
        text = next((value for name, value in attrs if name == "sessions"), None)
        kept = [[name, value] for name, value in attrs if name != "sessions"]
        bind.execute(sa.update(reference).where(reference.c.id == row_id).values(attributes=kept))
        seen: set[str] = set()
        for item in str(text or "").split(";"):
            parsed = parse_item(item) if item.strip() else None
            if parsed is None or parsed[0] in seen:
                continue
            kind, overrides = parsed
            seen.add(kind)
            made: list[list[Any]] = [["module", code], ["session_type", kind]]
            made += [[name, overrides[name]] for name in SETTINGS if name in overrides]
            bind.execute(
                sa.insert(reference).values(
                    dataset_id=dataset_id,
                    code=f"{code}-{kind}",
                    type=SESSION,
                    name="",
                    attributes=made,
                    tags=[],
                )
            )
    # Every dataset that has modules in the new shape also needs the new reference type.
    for dataset_id in sorted(touched):
        have = bind.execute(
            sa.select(reference_type.c.id).where(
                reference_type.c.dataset_id == dataset_id, reference_type.c.code == SESSION
            )
        ).first()
        if have is None:
            bind.execute(
                sa.insert(reference_type).values(
                    dataset_id=dataset_id,
                    code=SESSION,
                    name="Session row",
                    attribute_schema=SESSION_SCHEMA,
                )
            )
    for type_id, schema in bind.execute(
        sa.select(reference_type.c.id, reference_type.c.attribute_schema).where(
            reference_type.c.code == "Module", reference_type.c.dataset_id.in_(touched or [-1])
        )
    ).all():
        trimmed = [a for a in pairs_or_dicts(schema) if a.get("name") != "sessions"]
        bind.execute(
            sa.update(reference_type)
            .where(reference_type.c.id == type_id)
            .values(attribute_schema=trimmed)
        )


def pairs_or_dicts(value: Any) -> list[dict[str, Any]]:
    loaded = json.loads(value) if isinstance(value, str) else value
    return [dict(a) for a in loaded or []]


def downgrade() -> None:
    """The inline list cannot be restored from rows that override more than it could say."""
