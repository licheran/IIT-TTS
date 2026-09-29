"""Parameters of one solve (spec 05 section 4.4). Stored with each run, so they are a core type."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunParams(BaseModel):
    """How to solve. `num_workers=None` means one worker per CPU.

    `mode`: `optimise` searches for the best score within the time limit, `feasible` stops at the
    first solution, `two_phase` finds a feasible solution and then optimises from it. With no soft
    constraints they behave alike.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    time_limit_s: float = Field(default=120.0, gt=0)
    num_workers: int | None = Field(default=None, ge=1)
    seed: int = 0
    mode: Literal["optimise", "feasible", "two_phase"] = "optimise"
    lock_published: bool = True
