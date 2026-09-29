import pytest

from tts.core.model import Dataset, Reference, Resource
from tts.presets.academic_weekly import PRESET_NAME, labels, types


def test_the_preset_name() -> None:
    assert PRESET_NAME == "academic_weekly"


@pytest.mark.parametrize(
    ("code", "exclusive", "has_capacity"),
    [
        (types.UNIVERSITY, False, False),
        (types.LEVEL, False, False),
        (types.PROGRAMME, False, False),
        (types.STUDENT_GROUP, True, True),
        (types.TEACHER, True, False),
        (types.CAMPUS, False, False),
        (types.BUILDING, False, False),
        (types.ROOM, True, True),
    ],
)
def test_resource_types_match_the_spec_table(
    code: str, exclusive: bool, has_capacity: bool
) -> None:
    (found,) = [t for t in types.RESOURCE_TYPES if t.code == code]
    assert (found.exclusive, found.has_capacity) == (exclusive, has_capacity)


def test_there_are_exactly_the_eight_resource_types_of_the_spec() -> None:
    assert len(types.RESOURCE_TYPES) == 8
    assert len({t.code for t in types.RESOURCE_TYPES}) == 8


def test_a_dataset_using_the_preset_types_is_sound() -> None:
    ds = Dataset(
        preset=PRESET_NAME,
        resource_types=types.RESOURCE_TYPES,
        reference_types=types.REFERENCE_TYPES,
        resources=(
            Resource(code="L6", type=types.LEVEL),
            Resource(code="L6 SE", type=types.PROGRAMME, parent="L6"),
            Resource(code="L6 SE / G1", type=types.STUDENT_GROUP, parent="L6 SE", capacity=30),
            Resource(code="HAWE", type=types.TEACHER),
            Resource(code="GP", type=types.BUILDING),
            Resource(
                code="[2LA] -GP",
                type=types.ROOM,
                parent="GP",
                capacity=90,
                tags={types.ROOM_TYPE_TAG: "lab"},
            ),
        ),
        references=(Reference(code="6SENG005C", type=types.MODULE, attributes={"credits": 20}),),
    )
    assert ds.validate_invariants() == []


def test_the_module_attribute_schema_rejects_a_wrongly_typed_attribute() -> None:
    ds = Dataset(
        reference_types=types.REFERENCE_TYPES,
        references=(
            Reference(code="ok", type=types.MODULE, attributes={"credits": 20}),
            Reference(code="bad", type=types.MODULE, attributes={"credits": "many"}),
            Reference(code="odd", type=types.MODULE, attributes={"colour": "red"}),
        ),
    )
    found = sorted((i.kind, i.table, i.key) for i in ds.validate_invariants())
    assert found == [
        ("bad_attribute", "reference", "bad"),
        ("unknown_attribute", "reference", "odd"),
    ]


def test_every_resource_type_kind_and_delivery_has_a_label() -> None:
    codes = (
        [t.code for t in types.RESOURCE_TYPES]
        + [t.code for t in types.REFERENCE_TYPES]
        + list(types.EVENT_KINDS)
        + list(types.DELIVERIES)
    )
    tables = (labels.TYPE_LABELS, labels.KIND_LABELS, labels.DELIVERY_LABELS)
    assert [c for c in codes if not any(c in t for t in tables)] == []
    assert labels.label(types.STUDENT_GROUP) == "Group"
    assert labels.label(types.LECTURE) == "Lecture"
    assert labels.label(types.ONLINE) == "Online"
    assert labels.label("unknown-code") == "unknown-code"
