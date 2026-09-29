"""Presets: packaged domains (types, sheets, labels). A preset holds no scheduling logic."""

from tts.core.sheets import Preset
from tts.presets.academic_weekly.preset import PRESET as ACADEMIC_WEEKLY


class UnknownPresetError(KeyError):
    """No preset has that name."""


PRESETS: dict[str, Preset] = {ACADEMIC_WEEKLY.name: ACADEMIC_WEEKLY}


def get_preset(name: str) -> Preset:
    try:
        return PRESETS[name]
    except KeyError:
        known = ", ".join(sorted(PRESETS))
        raise UnknownPresetError(f'unknown preset "{name}" (known: {known})') from None
