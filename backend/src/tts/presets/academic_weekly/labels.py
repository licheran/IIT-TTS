"""User-facing labels for the academic preset. The UI shows these instead of core codes."""

from tts.presets.academic_weekly import types

TYPE_LABELS: dict[str, str] = {
    types.UNIVERSITY: "University",
    types.LEVEL: "Level",
    types.PROGRAMME: "Programme",
    types.STUDENT_GROUP: "Group",
    types.TEACHER: "Teacher",
    types.CAMPUS: "Campus",
    types.BUILDING: "Building",
    types.ROOM: "Room",
    types.MODULE: "Module",
}

KIND_LABELS: dict[str, str] = {
    types.LECTURE: "Lecture",
    types.TUTORIAL: "Tutorial",
    types.LAB: "Lab",
    types.SEMINAR: "Seminar",
}

DELIVERY_LABELS: dict[str, str] = {
    types.IN_PERSON: "In person",
    types.ONLINE: "Online",
}


def label(code: str) -> str:
    """The label for a resource type, reference type, event kind or delivery, else the code."""
    for table in (TYPE_LABELS, KIND_LABELS, DELIVERY_LABELS):
        if code in table:
            return table[code]
    return code
