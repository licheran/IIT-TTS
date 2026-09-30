"""Template expansion with the options of the dataset's preset (API and worker)."""

from typing import Any

from tts.core.model import Dataset
from tts.expand.templates import Expansion, expand
from tts.presets import expansion_options


def expand_with_preset(dataset: Dataset) -> Expansion:
    options: dict[str, Any] = expansion_options(dataset.preset)
    return expand(dataset, **options)
