"""The declared constraint types of the catalogue (`docs/spec/04-constraints.md` section 2).

A fixed list (ADR-0005). Importers use it to reject unknown types and to check that a
constraint's scope selects the kind of target its type applies to. A type being listed here does
not mean it is implemented: `registry.DECLARED` lists the ones the verifier checks.
"""

from typing import Literal

Target = Literal["resource", "event"]

# type name -> what its scope selects
CATALOGUE: dict[str, Target] = {
    "max_per_day": "resource",
    "max_gaps": "resource",
    "max_days": "resource",
    "min_days_between": "event",
    "same_start": "event",
    "same_day": "event",
    "order": "event",
    "consecutive": "event",
    "not_overlapping": "event",
    "travel_gap": "resource",
    "preferred_times": "event",
    "preferred_resources": "event",
    "avoid": "resource",
    "max_span": "resource",
}
