"""The `academic_weekly` preset: weekly course timetabling (spec 02 section 6.1).

A preset is configuration and labels only. It holds no scheduling logic.
"""

PRESET_NAME = "academic_weekly"

# Template expansion (spec 05 section 2): lectures come before tutorials, and a template with no
# room type gives online activities (spec 03, Templates sheet).
ORDERING: tuple[tuple[str, str], ...] = (("LEC", "TUT"),)
UNPOOLED_DELIVERY = "online"
