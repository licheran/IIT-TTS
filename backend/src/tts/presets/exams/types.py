"""Resource types, reference types and event kinds of the exams preset."""

from tts.core.model import AttributeDef, ReferenceType, ResourceType

COHORT = "Cohort"
HALL = "Hall"
INVIGILATOR = "Invigilator"

RESOURCE_TYPES: tuple[ResourceType, ...] = (
    ResourceType(code=COHORT, exclusive=True, has_capacity=True),  # capacity = size
    ResourceType(code=HALL, exclusive=True, has_capacity=True),
    ResourceType(code=INVIGILATOR, exclusive=True),
)

PAPER = "Paper"

REFERENCE_TYPES: tuple[ReferenceType, ...] = (
    ReferenceType(
        code=PAPER,
        name="Paper",
        attribute_schema=(AttributeDef(name="minutes", kind="int"),),
    ),
)

EXAM = "EXAM"
KINDS = (EXAM, "PRACTICAL")
