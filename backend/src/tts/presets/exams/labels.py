"""User-facing labels for the exams preset."""

from tts.presets.exams import types

LABELS: dict[str, str] = {
    types.COHORT: "Cohort",
    types.HALL: "Hall",
    types.INVIGILATOR: "Invigilator",
    types.PAPER: "Paper",
    types.EXAM: "Exam",
    "PRACTICAL": "Practical",
}


def label(code: str) -> str:
    return LABELS.get(code, code)


def all_labels() -> dict[str, str]:
    return dict(LABELS)
