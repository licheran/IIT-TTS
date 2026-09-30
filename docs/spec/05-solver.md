# 05 — Pipeline, Solver, Pre-flight and Explanations

Status: **Authoritative.** Code: `expand/`, `preflight/`, `solver/`, `core/verifier.py`.

## 1. Pipeline

```
snapshot(dataset) → prepare → preflight → compile_model → solve → decode → verify → store
```

`prepare` depends on the dataset's kind (`02-domain-model.md` §2, invariant 7). A **hand-made** dataset expands its templates into events (§2.1). A **configured** dataset has its preset turn the configuration into demands (§2.2), which the solver splits into sessions; it has no expand step.

- Each stage is a pure function with typed input and output, except `store`.
- `snapshot` freezes the dataset into a core model and computes `input_hash` (SHA-256 of the canonical JSON).
- If `preflight` returns any `error`, the pipeline stops and the run status becomes `blocked`.
- If `verify` finds a hard violation, the run status becomes `invalid` (this should never happen, and is treated as a bug), and the violations are stored.

## 2. Preparing events

### 2.1 Templates → events (hand-made datasets)

| `mode` | Events created per session_per_week |
|---|---|
| `joint` | 1 event with every group matched by the `groups` selector |
| `per_group` | 1 event per matched group |
| `batched` | Matched groups are sorted by code and split into consecutive batches of `batch_size`. 1 event per batch |

- **Event codes:** `<module>-<kind>-<nn>` where `nn` is 01, 02, … in creation order. They are stable when the inputs don't change.
- **Ordering:** for each module with both a LEC template and a TUT template, add a soft `order` constraint (weight 1) from each LEC event to every TUT event that shares at least one group.
- **Idempotence:** re-expanding replaces only events with `template = <this template>`. Hand-made events (with no template) are never touched.
- **Preview:** `expand(ds, commit=False)` returns a diff of added, changed and removed events.

### 2.2 Demands → sessions (configured datasets)

The preset derives **demands** from the configuration (`02-domain-model.md` §6.1, `03-workbook-format.md` §2a). The derived demands are part of the run's snapshot, so the input hash covers them. The solver then works as follows.

- **Block count.** A demand with `m` participants and `max_participants = n` has `k = ⌈m / n⌉` blocks (1 without a limit). The solver decides who is in which block. Block sizes differ by at most one (`⌊m/k⌋` or `⌈m/k⌉`), so 10 groups with `n = 3` give 3 + 3 + 2 + 2.
- **Repetition.** Every block has `repeat` events, each with its own start and its own pooled choices (room, teacher), but always the block's participants.
- **Codes.** Created events are coded `<reference or demand code>-<kind>-<nn>`, numbered by block (in order of the block's lowest participant code), then repetition, skipping codes declared events use. The same solution always gives the same codes.
- **Edits.** A declared event of a demand is an edit. Its fixed resources are its block's participants (they are kept together); its `Pin` carries an edited day, start, room or teacher. The solver treats the participants of edited events as a **fixed block**: it creates the missing repetitions for it (up to `repeat`) and splits the remaining participants into the remaining blocks. An edit whose participants are not all participants of the demand, or that is larger than `max_participants`, is a pre-flight error naming the edit.
- **A complete rebuild.** A run never patches an earlier timetable. It solves from scratch with the edits as inputs.
- **Defaults.** No `AUTO-ORDER` constraints are generated (created events have no codes before solving).

## 3. Pre-flight checks

| Check | Severity | Message example |
|---|---|---|
| Unresolved references | error | `ActivityGroups: unknown group "L6 SE / G12"` |
| Hierarchy cycle | error | `Groups: cycle at "L6 SE / G1"` |
| Empty start domain | error | `6SENG005C-TUT-03: no allowed start fits duration 2` |
| No candidate pooled resource | error | `6COSC023C-LEC-01: no Room with room_type=auditorium and capacity ≥ 210` |
| Resource over-demand | error | `Teacher HAWE: needs 16 periods, 12 available` |
| Pooled pressure | warning | `Rooms room_type=lab: 64 periods needed, 60 available` |
| Conflicting pins | error | `Pins: 2 activities pinned to [2LA] -GP on Wed P01` |
| Unused resource | warning | `Room [1LA] -GP is never a candidate` |
| Soft constraint on empty scope | warning | `C-GAPS: scope matches nothing` |
| **Demands** | | |
| No teacher for a module and kind | error | `6SENG005C TUT: no teacher lists this module` |
| Teacher pool too small for the load | error | `6SENG005C TUT: 4 sessions at once need 4 teachers, 3 can teach it` |
| A block cannot fit any room | error | `6SENG005C TUT: no Room with room_type=lab and capacity ≥ 90` (the largest possible block: the `⌈m/k⌉` biggest groups) |
| A participant's demand over its free periods | error | `L6 SE / G1: needs 26 periods, 24 available` |
| Pooled pressure from demands | warning | `Rooms room_type=lab: 64 periods needed, 60 available` (sessions = blocks × `repeat`) |
| A module with sessions and no groups | warning | `6SENG005C: no group takes this module` |
| A module with no session types | warning | `6SENG005C: no session types, nothing to schedule` |
| Nothing to schedule | warning | `No demands and no events: the timetable would be empty` |
| An edit that does not match | error | `6SENG005C-TUT-03: group "L6 SE / G99" is not a participant of demand 6SENG005C-TUT` |
| `code:` scope with demands | warning | `C-SAT: scope names no declared event, while demands make events with codes only after solving` |
| `uses:` scope, hard | error | `C-X: a hard rule with a uses: scope cannot be enforced on sessions the solver creates` |
| `uses:` scope, soft | warning | `C-X: only declared events are optimised for this scope; the score is still exact` |

"Available" means periods that are not breaks, minus `unavailable` availability rows. Demand is the sum of the durations of the events that occupy the resource. For pooled types, demand and supply are counted over the candidate sets.

## 4. CP-SAT model

### 4.1 Variables

For each event `e` with duration `δ`:
- `start[e]`: an IntVar with domain `allowed_starts(e)` after removing unavailable slots of its fixed resources and applying the pin.
- `iv[e]`: an IntervalVar with start `start[e]`, size `δ` and end `start[e]+δ`.
- `day_is[e,d]`: a BoolVar with `Σ_d day_is[e,d] = 1`, linked by `start[e] ∈ [d·P, d·P+P−1] ⇔ day_is[e,d]`.
- For each pooled requirement `q` of `e` and each candidate `r ∈ cand(q)`:
  - Candidates are resources of the type that pass H3 and H4 **at compile time**.
  - `use[e,q,r]`: a BoolVar with `Σ_r use[e,q,r] = count(q)`.
  - `oiv[e,q,r]`: an OptionalIntervalVar sharing `start[e]`, present iff `use[e,q,r]`.

### 4.1a Variables for demands

The dataset the solver compiles is the **materialised** dataset (`core/demands.py`): for each demand, the created events exist as ordinary events with `repeat` events per block and no fixed participants yet, edits are fixed blocks with constant membership, and a split with one possible answer (`k = 1`, or `n = 1`) has constant membership too. For the free blocks:

- `x[p, b]` for each participant `p` and block `b`: `Σ_b x[p, b] = 1` and `⌊m/k⌋ ≤ Σ_p x[p, b] ≤ ⌈m/k⌉`.
- Participant `p`'s occupancy of event `e` of block `b` is an optional interval sharing `start[e]`, present iff `x[p, b]`, in the no-overlap set of each exclusive resource `p` occupies (H1).
- H2: `x[p, b] ⇒ start[e] ∉ S_bad(p, δ)`.
- H3 for a `sum_of_fixed` requirement of `e`: `use[e, q, r] ⇒ Σ_p size(p) · x[p, b] ≤ capacity(r)`. Candidates are pre-filtered by the smallest block's size.
- **Symmetry breaking:** participant `i` may only be in blocks `b ≤ i`, and block `b` holds the lowest participant not in an earlier block.
- **Hint:** a greedy split (participants by code, cut into `k` even blocks) is given with `AddHint`.
- `CompileContext.occupying_events` and `occupied` include created events with their membership literals, so the resource-scoped declared types (§4.3) compile unchanged. Event-scoped types select created events by `kind`, `ref` and `tag` (`04-constraints.md` §5).
- Decomposition (§7) is **off** for configured datasets unless the Phase 20 measurement shows it helps (decision recorded in STATUS).

### 4.2 Hard constraints

- **H1:** for each exclusive resource `R`, `AddNoOverlap({iv[e] : e occupies R through fixed/descendant} ∪ {oiv[e,q,R]})`.
- **H2 for pooled resources:** for each `use[e,q,r]` where `r` has unavailable slots, `use[e,q,r] ⇒ start[e] ∉ S_bad(r, δ)`. This is encoded as `AddAllowedAssignments` or linear constraints over the start values.
- **Locks from published runs:** constant intervals added to the matching no-overlap sets. They are built as `unavailable` availability rows on the shared resources (`core/staging.py`), which gives the solver the same model and lets the verifier check them.
- **Pins:** fix the domain of `start[e]` and fix the `use` literals.

### 4.3 Soft constraints and objective

Each soft constraint instance `k` compiles to an IntVar `p_k ≥ 0` using the semantics in `04-constraints.md`. The objective is `minimise Σ weight_k · p_k`. Hard instances compile the same expression with `p_k == 0`.

### 4.4 Parameters (`RunParams`)

| Field | Default | Notes |
|---|---|---|
| `time_limit_s` | 120 | `max_time_in_seconds` |
| `num_workers` | number of CPUs | set to 1 for NFR-3 determinism tests |
| `seed` | 0 | `random_seed` |
| `mode` | `optimise` | `feasible` stops at the first solution. `two_phase` finds a feasible solution, then optimises with `AddHint` |
| `lock_published` | true | adds locks from other published runs that share resource codes |
| `stage_scope` | none | an event selector: solve only these events, locking the ones an earlier stage placed (§7). The earlier stage is the dataset's published run (API) or the workbook's `Assignments` (CLI `--stage`) |

### 4.5 Progress and cancel

A `CpSolverSolutionCallback` writes `{objective, best_bound, elapsed, solutions}` at most once per second and calls `StopSearch()` when the run's `cancel_requested` flag is set. When a run is cancelled with a solution, its status is `cancelled_partial` and the best solution is stored.

## 5. Infeasibility explanation

If the status is INFEASIBLE:
1. Rebuild the model with an assumption literal `a_g` guarding each hard group `g`. The groups are: each declared hard constraint instance, each pin, each availability row, the no-overlap of each resource, and each pooled requirement's candidate set.
2. Solve with every `a_g` as an assumption, then read `SufficientAssumptionsForInfeasibility()`.
3. Shrink the core greedily. Drop `a_g`; if the model is still infeasible, keep it dropped. Each re-solve has a short time limit (default 5 s). The total budget is 60 s.
4. For configured datasets, each participant of a demand adds a rule set of kind `demand` (its block membership). Store one `diagnostic` of kind `infeasible_core`. Its `refs` list the groups, and its message names entities by code, for example: `Conflicting rules: Teacher HAWE unavailable Tue–Thu; 8 events of 2 periods for HAWE; no_overlap(HAWE)`.
5. If no core is found within that time (the first proof needs more than the per-solve limit), store one `diagnostic` of kind `infeasible_unexplained` saying so, so that an infeasible run never ends without a message. It is added only when compilation found no reason of its own (`infeasible_reason`).

## 6. Verifier (`core/verifier.py`)

The verifier takes a dataset snapshot and a result, and checks H0–H5 and every active declared constraint using `core/constraints/*.verify`. It returns `list[Violation(code, constraint_code, severity, penalty, refs, message)]`.

- It doesn't import `solver/`.
- It also runs on externally supplied assignments, such as a FET import (FR-14).

## 7. Scaling strategies (Phase 10, add when measured)

1. **Staged solving** by scope selector (for example `uses:(under:L4)`), locking the earlier stages.
2. **Symmetry breaking:** order the starts of interchangeable events (same kind, same fixed resources, same requirement).
3. **Decomposition:** solve the times with aggregated room-type capacity constraints, then assign rooms per slot as a bipartite matching.
4. **Hints:** start from the published run's assignment.

## 8. Result storage for configured datasets

A `Result` holds `assignments` (one per event, declared or created) and `created`: for each created event its code, demand and participants. The store keeps them in `assignment`, `assigned_resource`, `created_event` and `created_participant` rows of the run. The solver writes only these (rule 3). `core.demands.realise(dataset, result)` turns a result into a dataset whose created events are ordinary events with their participants as fixed resources; grids, exports, the verifier and the clash finder all work on that.
