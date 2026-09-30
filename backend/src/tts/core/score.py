"""The score of a result (spec 04 section 0): the sum of `weight x p` over soft violations.

The verifier gives each soft violation its raw penalty `p`. The weights live on the dataset's
constraints, so the score is computed here, from the dataset and the verifier's output, never
from the solver's objective.
"""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from tts.core.model import Dataset, Violation


class ScoreLine(BaseModel):
    """One constraint instance's part of the score."""

    model_config = ConfigDict(frozen=True)

    penalty: int
    weight: int
    score: int


class Score(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    breakdown: dict[str, ScoreLine]  # by constraint code, only instances with a penalty


def score(dataset: Dataset, violations: Iterable[Violation]) -> Score:
    weights = {c.code: c.weight for c in dataset.constraints}
    penalties: dict[str, int] = {}
    for v in violations:
        if v.severity == "soft" and v.penalty:
            penalties[v.constraint_code] = penalties.get(v.constraint_code, 0) + v.penalty
    breakdown = {
        code: ScoreLine(penalty=p, weight=weights.get(code, 1), score=p * weights.get(code, 1))
        for code, p in sorted(penalties.items())
    }
    return Score(total=sum(line.score for line in breakdown.values()), breakdown=breakdown)
