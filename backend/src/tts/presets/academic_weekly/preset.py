"""The `academic_weekly` preset as objects: one per workbook format version."""

from tts.core.sheets import Preset
from tts.presets.academic_weekly import PRESET_NAME, sheets, types

# Format version 1: hand-made datasets (typed or imported activities, such as L6).
PRESET = Preset(
    name=PRESET_NAME,
    resource_types=types.RESOURCE_TYPES,
    reference_types=types.REFERENCE_TYPES,
    sheets=sheets.SHEETS,
    format_version=sheets.HAND_MADE_FORMAT_VERSION,
)

# Format version 2: configuration only (ADR-0007).
PRESET_V2 = Preset(
    name=PRESET_NAME,
    resource_types=types.RESOURCE_TYPES,
    reference_types=types.REFERENCE_TYPES,
    sheets=sheets.SHEETS_V2,
    format_version=sheets.FORMAT_VERSION,
)
