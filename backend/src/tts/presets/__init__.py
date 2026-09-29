"""Presets: packaged domains (types, sheets, labels). A preset holds no scheduling logic."""

from collections.abc import Callable

from tts.core.sheets import Preset
from tts.presets.academic_weekly.labels import label as academic_label
from tts.presets.academic_weekly.preset import PRESET as ACADEMIC_WEEKLY


class UnknownPresetError(KeyError):
    """No preset has that name."""


PRESETS: dict[str, Preset] = {ACADEMIC_WEEKLY.name: ACADEMIC_WEEKLY}


LABELLERS: dict[str, Callable[[str], str]] = {ACADEMIC_WEEKLY.name: academic_label}


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
