"""The `academic_weekly` preset as one object."""

from tts.core.sheets import Preset
from tts.presets.academic_weekly import PRESET_NAME, sheets, types

PRESET = Preset(
    name=PRESET_NAME,
    resource_types=types.RESOURCE_TYPES,
    reference_types=types.REFERENCE_TYPES,
    sheets=sheets.SHEETS,
)
