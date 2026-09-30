"""H6 `demand_cover`: the events of each demand divide its participants into even blocks.

The events of a demand (declared ones, which are edits, and created ones) are grouped into blocks:
events with the same participants. For each demand:

- every participant is in exactly one block;
- there are exactly `Demand.blocks` blocks;
- each block has at most `max_participants` participants and exactly `repeat` events;
- block sizes differ by at most one;
- every event has the demand's duration and start pattern.

Created events that cannot be made real (unknown demand, reused code, a participant outside the
demand) are reported here too. The verifier makes created events real before it calls any check,
so H0 to H5 already apply to them. A dataset with no demands has nothing to check.
"""

from collections import defaultdict

from tts.core.constraints.base import NoParams, event_ref, hard, resource_ref
from tts.core.constraints.context import VerifyContext, ensure_context
from tts.core.demands import rejected_created
from tts.core.model import Dataset, Ref, Result, Violation

CODE = "H6"
TYPE = "demand_cover"
Params = NoParams


def verify(
    dataset: Dataset, result: Result, context: VerifyContext | None = None
) -> list[Violation]:
    ctx = ensure_context(dataset, result, context)
    found: list[Violation] = []
    for created, why in rejected_created(ctx.base, result):
        found.append(
            hard(TYPE, CODE, f'created event "{created.code}": {why}', event_ref(created.code))
        )

    fixed: dict[str, set[str]] = defaultdict(set)
    for f in dataset.fixed:
        fixed[f.event].add(f.resource)

    for d in dataset.demands:
        here = Ref(kind="demand", code=d.code)
        allowed = set(d.participants)
        blocks: dict[frozenset[str], list[str]] = defaultdict(list)
        for e in dataset.events:
            if e.demand != d.code:
                continue
            if e.duration != d.duration:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'event "{e.code}": duration {e.duration}, the demand says {d.duration}',
                        event_ref(e.code),
                        here,
                    )
                )
            if e.start_pattern != d.start_pattern:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'event "{e.code}": start pattern "{e.start_pattern}", the demand says '
                        f'"{d.start_pattern}"',
                        event_ref(e.code),
                        here,
                    )
                )
            who = frozenset(fixed[e.code] & allowed)
            if not who:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'event "{e.code}": belongs to demand "{d.code}" but has no participants',
                        event_ref(e.code),
                        here,
                    )
                )
            else:
                blocks[who].append(e.code)

        in_blocks: dict[str, int] = defaultdict(int)
        for who in blocks:
            for participant in who:
                in_blocks[participant] += 1
        for participant in d.participants:
            count = in_blocks.get(participant, 0)
            if count == 0:
                message = f'demand "{d.code}": "{participant}" attends no session'
            elif count > 1:
                message = f'demand "{d.code}": "{participant}" is in {count} blocks'
            else:
                continue
            found.append(hard(TYPE, CODE, message, here, resource_ref(participant)))

        if d.participants and len(blocks) != d.blocks:
            found.append(
                hard(
                    TYPE,
                    CODE,
                    f'demand "{d.code}": {len(blocks)} block(s), expected {d.blocks}',
                    here,
                )
            )
        for who, codes in sorted(blocks.items(), key=lambda item: sorted(item[0])):
            label = ", ".join(sorted(who))
            refs = (here, *(event_ref(c) for c in sorted(codes)))
            limit = d.max_participants
            if limit is not None and len(who) > limit:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'demand "{d.code}": block {label} has {len(who)} participants, more '
                        f"than the limit of {limit}",
                        *refs,
                    )
                )
            if len(codes) != d.repeat:
                found.append(
                    hard(
                        TYPE,
                        CODE,
                        f'demand "{d.code}": block {label} has {len(codes)} session(s), expected '
                        f"{d.repeat}",
                        *refs,
                    )
                )
        sizes = sorted((len(who) for who in blocks), reverse=True)
        if len(sizes) > 1 and sizes[0] - sizes[-1] > 1:
            listed = ", ".join(str(n) for n in sizes)
            found.append(
                hard(
                    TYPE,
                    CODE,
                    f'demand "{d.code}": block sizes {listed} are uneven (they may differ by 1)',
                    here,
                )
            )
    return found
