# 04 — Constraint Catalogue

Status: **Authoritative.** Each type is implemented as `core/constraints/<type>.py` (`Params`, `verify`) and `solver/constraints/<type>.py` (`compile`). Adding a type means adding a row here, both modules, and tests for verify, for compile, and for hard-mode infeasibility.

## 0. Common definitions

- `S` = the set of resources or events selected by the constraint's `scope`.
- `occ(r, d)` = the ordered list of non-break periods on day `d` in which resource `r` is occupied (see the occupancy rule in `02-domain-model.md` §3).
- **Busy day:** `occ(r, d)` is not empty.
- **Gaps** on a day: the number of non-break periods between the first and last period in `occ(r, d)` that are not themselves occupied.
- **Penalty `p`:** a non-negative integer measuring how far a soft constraint is from being satisfied. The score is `Σ weight × p`. A hard constraint requires `p = 0`.
- **Per-resource constraints** apply to each resource in `S` separately, and their penalties add up.
- **Kind: implicit** constraints always exist and aren't declared in `Constraints`. H1 and H4 are always hard.

## 1. Implicit constraints

| Code | Type | Semantics | Penalty |
|---|---|---|---|
| H0 | `placement` | Each event gets exactly one start in `allowed_starts(e)` and exactly `count` resources for each pooled requirement | always hard |
| H1 | `no_overlap` | For each exclusive resource, the events occupying it do not share a slot | always hard |
| H2 | `unavailable` | No event occupies a resource in a slot with `Availability.status = unavailable` | always hard |
| H3 | `capacity` | Each chosen pooled resource has `capacity ≥` the requirement's capacity rule. `sum_of_fixed:<Type>` means the sum of the capacities of the event's fixed resources of that type (and their exclusive descendants, if the fixed resource is a grouping node) | always hard |
| H4 | `requirement_match` | Each chosen pooled resource matches the requirement's filter | always hard |
| H5 | `pin` | The assignment equals the pin in every field the pin sets | always hard |
| H6 | `demand_cover` | For each demand, its events (declared and created) form blocks, meaning events with the same participants. Each participant is in exactly one block. There are exactly `k = ⌈m / max_participants⌉` blocks (`m` participants; `k = 1` with no limit). Each block has exactly `repeat` events and at most `max_participants` participants. Block sizes differ by at most one. Every created event has the demand's duration, start pattern and pooled requirements | always hard |

## 2. Declared constraints (v1 catalogue)

| Code | `type` | Scope | `params` | Semantics | Penalty `p` |
|---|---|---|---|---|---|
| C1 | `max_per_day` | resources | `max:int`, `unit: "events"\|"periods"` (default periods) | For each day, the events (or occupied periods) for the resource are ≤ `max` | Σ over days of the excess |
| C2 | `max_gaps` | resources | `max:int`, `per: "day"\|"week"` | Gaps per day (or summed over the week) ≤ `max` | excess |
| C3 | `max_days` | resources | `max:int` | Number of busy days ≤ `max` | excess |
| C4 | `min_days_between` | events | `min:int` | For every pair of events in `S`: \|day(a) − day(b)\| ≥ `min` | number of violating pairs |
| C5 | `same_start` | events | — | All events in `S` start in the same slot | number of events not at the most common start |
| C6 | `same_day` | events | — | All events in `S` are on the same day | number of events not on the most common day |
| C7 | `order` | events | `sequence: [event codes]`, `same_day: bool` (default false) | Each event starts after the previous one ends. If `same_day`, they are also on the same day | number of violated adjacent pairs |
| C8 | `consecutive` | events | `sequence: [event codes]` | Each event starts in the slot right after the previous one ends, on the same day | number of violated adjacent pairs |
| C9 | `not_overlapping` | events | — | No two events in `S` share a slot, even without a shared resource | number of overlapping pairs |
| C10 | `travel_gap` | resources | `min_periods:int`, `level: <ResourceType>` (for example Building) | If two consecutive occupied blocks of the resource on a day are at different ancestors of type `level` (through their pooled resources), at least `min_periods` free periods separate them | number of violating transitions |
| C11 | `preferred_times` | events | `slots: [ "Day:Period" ]` | The event starts in one of the slots | 0 or 1 per event |
| C12 | `preferred_resources` | events | `filter: selector` | Every chosen pooled resource matches the filter | number of non-matching choices |
| C13 | `avoid` | resources | (from `Availability` rows with `status=avoid`) | The resource isn't occupied in `avoid` slots | occupied avoid-periods |
| C14 | `max_span` | resources | `max:int` | Per day, last occupied period − first + 1 ≤ `max` | Σ excess |

Rules for every declared type:
- Any declared type may be `hard: true` (then `p` must be 0) or soft with a `weight`.
- `scope` must select the kind of target stated in the Scope column. Otherwise the import fails with an error.

## 3. Academic preset defaults (data, in `presets/academic_weekly/defaults.py`)

| Code | type | scope | params | hard | weight |
|---|---|---|---|---|---|
| AC-GAPS | `max_gaps` | `type:StudentGroup` | `{"max": 2, "per": "day"}` | false | 5 |
| AC-TGAPS | `max_gaps` | `type:Teacher` | `{"max": 3, "per": "day"}` | false | 2 |
| AC-TRAVEL | `travel_gap` | `type:StudentGroup` | `{"min_periods": 1, "level": "Building"}` | false | 10 (inactive by default) |
| AC-SAT | `preferred_times` | `kind:LEC,TUT` | all non-Saturday slots | false | 3 |

`AC-TRAVEL` is created with `active: false`: the institute needs no free period for a change of building (answered 2026-09-30), and a user can switch it on. `AC-SAT` exists only when the time model has a Saturday. The defaults are added to new datasets and to `tts import-fet` output (unless `--no-defaults`).

Lecture-before-tutorial ordering is added per module by the expander (`05-solver.md` §2) as soft `order` constraints with weight 1. It applies to hand-made datasets only (see §5).

## 4. Test requirements for each type

1. `verify` returns the exact expected penalty on at least three hand-built cases (0, 1 and several violations).
2. `compile` + solve on a small instance finds an optimum where `verify` gives the same penalty as the solver's objective term.
3. The hard version on a deliberately impossible instance is INFEASIBLE, and the explanation lists this constraint instance's code.

## 5. Created events and the declared constraints

Sessions the solver creates from a demand (ADR-0007) are events like any other once the solver has chosen their blocks. The verifier makes them real first (each created event gets its participants as fixed resources), then runs H0–H5 and every declared type unchanged. The solver's model treats them as follows.

| Kind of constraint | Types | With created events |
|---|---|---|
| **Resource-scoped** | C1, C2, C3, C10, C13, C14 | Work on the resource's occupancy. A created event occupies a participant exactly when the participant is in its block, so the penalty counts it through that membership. No change to the semantics |
| **Event-scoped** | C4, C5, C6, C9, C11, C12 | The scope selects created events by properties known before solving: `kind:`, `ref:`, `tag:` and `type:`-free selectors. A created event has its demand's kind, reference and tags. They then behave as any event |
| Types that name events | C7 `order`, C8 `consecutive` | `params.sequence` lists event codes, and the codes of sessions the solver creates do not exist before solving, so these two apply to declared events only (hand-made events, or edits of a configured dataset) |
| Scope with `code:` | event-scoped | Codes of created events do not exist before solving, so `code:` selects declared events only. The verifier, which sees the real codes, may select more. Pre-flight warns when a `code:` scope matches no declared event while demands exist |
| Scope with `uses:` | event-scoped | Which resources a created event uses depends on the grouping. The solver ignores created events for a `uses:` scope. Pre-flight gives an **error** when such a constraint is hard (the solver could not enforce it) and a **warning** when it is soft (the solver optimises only the declared events, while the score is still measured exactly by the verifier) |

**No automatic ordering.** The expander's `AUTO-ORDER:` constraints need event codes, so they are not generated for configured datasets. A lecture-before-tutorial rule has to be written as an `order` constraint over declared events, or left to the administrator.

**Academic defaults** (spec 04 §3) apply unchanged: `AC-GAPS`, `AC-TGAPS` and `AC-SAT` select by resource type or event kind.
