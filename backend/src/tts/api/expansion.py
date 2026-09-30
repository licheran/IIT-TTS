"""Preparing a dataset for a run with the options of its preset (API and worker).

A hand-made dataset already holds its activities (template rows of an old file were expanded once
when it was imported). A configured dataset gets the demands its configuration makes (ADR-0007).
"""

from tts.core.model import Dataset, Ref
from tts.preflight.checks import Issue, run_preflight
from tts.presets import configuration_issues, derive_demands, labeller


def prepare_with_preset(dataset: Dataset) -> Dataset:
    """The dataset as the solver takes it: the demands of a configured dataset derived."""
    if dataset.kind == "hand_made":
        return dataset
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
