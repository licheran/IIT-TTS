"""Preparing a dataset for a run with the options of its preset (API and worker).

A hand-made dataset expands its templates into events. A configured dataset gets the demands its
configuration makes (ADR-0007). Both are a no-op on a dataset that was already prepared.
"""

from typing import Any

from tts.core.model import Dataset, Ref
from tts.expand.templates import Expansion, expand
from tts.preflight.checks import Issue, run_preflight
from tts.presets import configuration_issues, derive_demands, expansion_options, labeller


def expand_with_preset(dataset: Dataset) -> Expansion:
    options: dict[str, Any] = expansion_options(dataset.preset)
    return expand(dataset, **options)


def prepare_with_preset(dataset: Dataset) -> Dataset:
    """The dataset as the solver takes it: templates expanded, or demands derived."""
    if dataset.kind == "hand_made":
        return expand_with_preset(dataset).dataset
    demands = derive_demands(dataset)
    return dataset.model_copy(update={"demands": demands}) if demands else dataset


def preflight_with_preset(dataset: Dataset) -> list[Issue]:
    """Pre-flight of the dataset as the solver takes it, plus the mistakes only its preset can
    see in a configuration (kind `configuration`, always an error)."""
    prepared = prepare_with_preset(dataset)
    issues = run_preflight(prepared, labeller(prepared.preset))
    extra = [
        Issue(
            severity="error",
            kind="configuration",
            message=f'{mistake.sheet} "{mistake.code}": {mistake.message}',
            refs=(Ref(kind="resource", code=mistake.code),)
            if mistake.code in {r.code for r in prepared.resources}
            else (),
        )
        for mistake in configuration_issues(prepared)
    ]
    return sorted([*issues, *extra], key=lambda i: (i.severity != "error", i.kind, i.message))
