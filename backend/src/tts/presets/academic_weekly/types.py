"""Resource types, reference types and vocabularies of the academic preset (spec 02 section 6.1)."""

from tts.core.model import AttributeDef, ReferenceType, ResourceType

UNIVERSITY = "University"
LEVEL = "Level"
PROGRAMME = "Programme"
STUDENT_GROUP = "StudentGroup"
TEACHER = "Teacher"
CAMPUS = "Campus"
BUILDING = "Building"
ROOM = "Room"

RESOURCE_TYPES: tuple[ResourceType, ...] = (
    ResourceType(code=UNIVERSITY, exclusive=False),
    ResourceType(code=LEVEL, exclusive=False),
    ResourceType(code=PROGRAMME, exclusive=False),
    ResourceType(
        code=STUDENT_GROUP,
        exclusive=True,
        has_capacity=True,
        # The optional modules the group takes, `;`-separated (format version 2).
        attribute_schema=(AttributeDef(name="options", kind="str"),),
    ),
    ResourceType(
        code=TEACHER,
        exclusive=True,
        # The modules the teacher may teach, `;`-separated, each `module` or `module:KIND`.
        attribute_schema=(AttributeDef(name="modules", kind="str"),),
    ),
    ResourceType(code=CAMPUS, exclusive=False),
    ResourceType(
        code=BUILDING,
        exclusive=False,
        attribute_schema=(AttributeDef(name="abbreviation", kind="str"),),
    ),
    ResourceType(code=ROOM, exclusive=True, has_capacity=True),
)

MODULE = "Module"
SESSION_TYPE = "SessionType"

REFERENCE_TYPES: tuple[ReferenceType, ...] = (
    ReferenceType(
        code=MODULE,
        name="Module",
        attribute_schema=(
            AttributeDef(name="credits", kind="int"),
            AttributeDef(name="level", kind="str"),
            AttributeDef(name="programme", kind="str"),
            # Format version 2: the programmes that take it (`;`-separated), whether it is
            # optional, and its session types (`;`-separated, each with optional settings).
            AttributeDef(name="programmes", kind="str"),
            AttributeDef(name="optional", kind="bool"),
            AttributeDef(name="sessions", kind="str"),
        ),
    ),
    ReferenceType(
        code=SESSION_TYPE,
        name="Session type",
        attribute_schema=(
            AttributeDef(name="start_pattern", kind="str"),
            AttributeDef(name="delivery", kind="str"),
            AttributeDef(name="room_type", kind="str"),
            AttributeDef(name="max_groups", kind="int"),
            AttributeDef(name="teachers", kind="int"),
            AttributeDef(name="weekly", kind="int"),
        ),
    ),
)

LECTURE = "LEC"
TUTORIAL = "TUT"
LAB = "LAB"
SEMINAR = "SEM"
EVENT_KINDS: tuple[str, ...] = (LECTURE, TUTORIAL, LAB, SEMINAR)

IN_PERSON = "in_person"
ONLINE = "online"
DELIVERIES: tuple[str, ...] = (IN_PERSON, ONLINE)

# Rooms carry their type as this tag, and a room requirement filters on it.
ROOM_TYPE_TAG = "room_type"
