"""Presets: packaged domains (types, sheets, labels). A preset holds no scheduling logic."""

from collections.abc import Callable

from tts.core.model import Dataset
from tts.core.sheets import Preset
from tts.presets import academic_weekly
from tts.presets.academic_weekly.defaults import with_defaults as academic_defaults
from tts.presets.academic_weekly.labels import all_labels as academic_labels
from tts.presets.academic_weekly.labels import label as academic_label
from tts.presets.academic_weekly.preset import PRESET as ACADEMIC_WEEKLY
from tts.presets.academic_weekly.sheets import FORMAT_VERSION as ACADEMIC_FORMAT
from tts.presets.exams.defaults import with_defaults as exams_defaults
from tts.presets.exams.labels import all_labels as exams_labels
from tts.presets.exams.labels import label as exams_label
from tts.presets.exams.preset import PRESET as EXAMS
from tts.presets.exams.sheets import FORMAT_VERSION as EXAMS_FORMAT


class UnknownPresetError(KeyError):
    """No preset has that name."""


PRESETS: dict[str, Preset] = {ACADEMIC_WEEKLY.name: ACADEMIC_WEEKLY, EXAMS.name: EXAMS}

FORMAT_VERSIONS: dict[str, int] = {ACADEMIC_WEEKLY.name: ACADEMIC_FORMAT, EXAMS.name: EXAMS_FORMAT}

LABELLERS: dict[str, Callable[[str], str]] = {
    ACADEMIC_WEEKLY.name: academic_label,
    EXAMS.name: exams_label,
}

LABEL_TABLES: dict[str, Callable[[], dict[str, str]]] = {
    ACADEMIC_WEEKLY.name: academic_labels,
    EXAMS.name: exams_labels,
}

DEFAULTS: dict[str, Callable[[Dataset], Dataset]] = {
    ACADEMIC_WEEKLY.name: academic_defaults,
    EXAMS.name: exams_defaults,
}

ExpansionOptions = dict[str, object]  # keyword arguments of `tts.expand.templates.expand`

EXPANSION: dict[str, ExpansionOptions] = {
    ACADEMIC_WEEKLY.name: {
        "ordering": academic_weekly.ORDERING,
        "unpooled_delivery": academic_weekly.UNPOOLED_DELIVERY,
    },
}


def expansion_options(name: str) -> ExpansionOptions:
    """How a preset's templates expand (ordering pairs, delivery without a pool)."""
    return dict(EXPANSION.get(name, {}))


def with_defaults(dataset: Dataset) -> Dataset:
    """The dataset plus its preset's default constraints (unchanged for a preset with none)."""
    apply = DEFAULTS.get(dataset.preset)
    return dataset if apply is None else apply(dataset)


def labels(name: str) -> dict[str, str]:
    """Every label of a preset by code, for the UI. Empty for an unknown preset."""
    table = LABEL_TABLES.get(name)
    return {} if table is None else table()


def labeller(name: str) -> Callable[[str], str]:
    """The function that turns a type or kind code into the preset's word for it.

    A dataset with no preset, or one this build does not know, keeps its codes.
    """
    return LABELLERS.get(name, str)


def get_preset(name: str) -> Preset:
    try:
        return PRESETS[name]
    except KeyError:
        known = ", ".join(sorted(PRESETS))
        raise UnknownPresetError(f'unknown preset "{name}" (known: {known})') from None
