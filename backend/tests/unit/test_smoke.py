import importlib

import pytest

PACKAGES = [
    "tts.core",
    "tts.core.constraints",
    "tts.expand",
    "tts.preflight",
    "tts.solver",
    "tts.solver.constraints",
    "tts.io",
    "tts.presets",
    "tts.store",
    "tts.api",
    "tts.api.routers",
    "tts.worker",
]


@pytest.mark.parametrize("name", PACKAGES)
def test_package_is_importable(name: str) -> None:
    assert importlib.import_module(name) is not None
