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
    ResourceType(code=STUDENT_GROUP, exclusive=True, has_capacity=True),
    ResourceType(code=TEACHER, exclusive=True),
    ResourceType(code=CAMPUS, exclusive=False),
    ResourceType(code=BUILDING, exclusive=False),
    ResourceType(code=ROOM, exclusive=True, has_capacity=True),
)

MODULE = "Module"

REFERENCE_TYPES: tuple[ReferenceType, ...] = (
    ReferenceType(
        code=MODULE,
        name="Module",
        attribute_schema=(
            AttributeDef(name="credits", kind="int"),
            AttributeDef(name="level", kind="str"),
            AttributeDef(name="programme", kind="str"),
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
