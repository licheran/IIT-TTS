"""Compilers for declared constraint types, keyed by type name.

Each `solver/constraints/<type>.py` exposes `compile(ctx, instance) -> None` and is listed here,
one line per type, as it is written (Phase 8). The implicit rules H0 to H5 are part of the
compile step itself (`compile.py`), not entries here.
"""

from collections.abc import Callable

from tts.core.model import Constraint
from tts.solver.context import CompileContext

Compiler = Callable[[CompileContext, Constraint], None]

COMPILERS: dict[str, Compiler] = {}


def _register() -> None:
    """Fill `COMPILERS`, one line per type (imported here: the compilers import this module)."""
    from tts.solver.constraints import max_gaps, max_per_day

    COMPILERS.update(
        {
            "max_gaps": max_gaps.compile,
            "max_per_day": max_per_day.compile,
        }
    )


class UnsupportedConstraintError(ValueError):
    """A hard constraint whose type the solver cannot compile. Ignoring it would break the rule."""


def compile_declared(ctx: CompileContext) -> None:
    """Compile every active declared constraint of the dataset.

    A soft constraint of a type with no compiler is ignored with a warning. A hard one raises,
    because a result that ignores it could break a rule the user declared.
    """
    for constraint in ctx.dataset.constraints:
        if not constraint.active:
            continue
        compiler = COMPILERS.get(constraint.type)
        if compiler is not None:
            compiler(ctx, constraint)
        elif constraint.hard:
            raise UnsupportedConstraintError(
                f'hard constraint "{constraint.code}": type "{constraint.type}" is not supported '
                "by the solver yet"
            )
        else:
            ctx.warnings.append(
                f'constraint "{constraint.code}" ({constraint.type}) is not supported by the '
                "solver yet and was ignored"
            )


_register()
