"""Presets: packaged domains (types, sheets, labels). A preset holds no scheduling logic."""

from collections.abc import Callable

from tts.core.model import Dataset, Demand
from tts.core.sheets import ConfigIssue, Preset
from tts.presets import academic_weekly
from tts.presets.academic_weekly.configuration import configuration_issues as academic_issues
from tts.presets.academic_weekly.configuration import demands as academic_demands
from tts.presets.academic_weekly.defaults import with_defaults as academic_defaults
from tts.presets.academic_weekly.labels import all_labels as academic_labels
from tts.presets.academic_weekly.labels import label as academic_label
from tts.presets.academic_weekly.preset import PRESET as ACADEMIC_WEEKLY
from tts.presets.academic_weekly.preset import PRESET_V2 as ACADEMIC_WEEKLY_V2
from tts.presets.exams.defaults import with_defaults as exams_defaults
from tts.presets.exams.labels import all_labels as exams_labels
from tts.presets.exams.labels import label as exams_label
from tts.presets.exams.preset import PRESET as EXAMS
from tts.presets.exams.sheets import FORMAT_VERSION as EXAMS_FORMAT


class UnknownPresetError(KeyError):
    """No preset has that name."""


# Every workbook format version of each preset (spec 03). A preset with one version has one entry.
PRESET_VERSIONS: dict[str, dict[int, Preset]] = {
    ACADEMIC_WEEKLY.name: {
        ACADEMIC_WEEKLY.format_version: ACADEMIC_WEEKLY,
        ACADEMIC_WEEKLY_V2.format_version: ACADEMIC_WEEKLY_V2,
    },
    EXAMS.name: {EXAMS_FORMAT: EXAMS},
}

# The newest version of each preset: what a new dataset uses.
PRESETS: dict[str, Preset] = {
    name: versions[max(versions)] for name, versions in PRESET_VERSIONS.items()
}

# The highest format version each preset's workbooks may have.
FORMAT_VERSIONS: dict[str, int] = {
    name: max(versions) for name, versions in PRESET_VERSIONS.items()
}

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


DEMANDS: dict[str, Callable[[Dataset], tuple[Demand, ...]]] = {
    ACADEMIC_WEEKLY.name: academic_demands,
}

ISSUES: dict[str, Callable[[Dataset], list[ConfigIssue]]] = {
    ACADEMIC_WEEKLY.name: academic_issues,
}


def derive_demands(dataset: Dataset) -> tuple[Demand, ...]:
    """The demands a configured dataset's configuration makes (none for a preset without any)."""
    derive = DEMANDS.get(dataset.preset)
    return () if derive is None else derive(dataset)


def configuration_issues(dataset: Dataset) -> list[ConfigIssue]:
    """The mistakes of a configured dataset that its sheets cannot show (spec 03 section 3)."""
    check = ISSUES.get(dataset.preset)
    if check is None or dataset.kind == "hand_made":
        return []
    return check(dataset)


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


def get_preset(name: str, version: int | None = None) -> Preset:
    """The preset `name` at workbook format `version` (the newest when not given)."""
    try:
        versions = PRESET_VERSIONS[name]
    except KeyError:
        known = ", ".join(sorted(PRESETS))
        raise UnknownPresetError(f'unknown preset "{name}" (known: {known})') from None
    if version is None:
        return versions[max(versions)]
    try:
        return versions[version]
    except KeyError:
        raise UnknownPresetError(
            f"format_version {version} not supported (max {max(versions)})"
        ) from None


def preset_for_kind(name: str, kind: str) -> Preset:
    """The preset at the format version that can hold a dataset of this kind.

    A hand-made dataset (typed or imported activities) needs the oldest format version; a
    configured one uses the newest. A preset with one version always gives that one.
    """
    versions = PRESET_VERSIONS.get(name)
    if versions is None:
        return get_preset(name)
    return versions[min(versions)] if kind == "hand_made" else versions[max(versions)]


def preset_for(dataset: Dataset) -> Preset:
    """The preset, at the format version that can hold this dataset."""
    return preset_for_kind(dataset.preset, dataset.kind)
