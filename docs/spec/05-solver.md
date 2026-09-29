# 05 — Pipeline, Solver, Pre-flight and Explanations

Status: **Authoritative.** Code: `expand/`, `preflight/`, `solver/`, `core/verifier.py`.

## 1. Pipeline

```
snapshot(dataset) → expand → preflight → compile_model → solve → decode → verify → store
```

- Each stage is a pure function with typed input and output, except `store`.
- `snapshot` freezes the dataset into a core model and computes `input_hash` (SHA-256 of the canonical JSON).
- If `preflight` returns any `error`, the pipeline stops and the run status becomes `blocked`.
- If `verify` finds a hard violation, the run status becomes `invalid` (this should never happen, and is treated as a bug), and the violations are stored.

## 2. Expansion (templates → events)

| `mode` | Events created per session_per_week |
|---|---|
| `joint` | 1 event with every group matched by the `groups` selector |
| `per_group` | 1 event per matched group |
| `batched` | Matched groups are sorted by code and split into consecutive batches of `batch_size`. 1 event per batch |

- **Event codes:** `<module>-<kind>-<nn>` where `nn` is 01, 02, … in creation order. They are stable when the inputs don't change.
- **Ordering:** for each module with both a LEC template and a TUT template, add a soft `order` constraint (weight 1) from each LEC event to every TUT event that shares at least one group.
- **Idempotence:** re-expanding replaces only events with `template = <this template>`. Hand-made events (with no template) are never touched.
- **Preview:** `expand(ds, commit=False)` returns a diff of added, changed and removed events.

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

### 4.2 Hard constraints

- **H1:** for each exclusive resource `R`, `AddNoOverlap({iv[e] : e occupies R through fixed/descendant} ∪ {oiv[e,q,R]})`.
- **H2 for pooled resources:** for each `use[e,q,r]` where `r` has unavailable slots, `use[e,q,r] ⇒ start[e] ∉ S_bad(r, δ)`. This is encoded as `AddAllowedAssignments` or linear constraints over the start values.
- **Locks from published runs:** constant intervals added to the matching no-overlap sets.
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

### 4.5 Progress and cancel

A `CpSolverSolutionCallback` writes `{objective, best_bound, elapsed, solutions}` at most once per second and calls `StopSearch()` when the run's `cancel_requested` flag is set. When a run is cancelled with a solution, its status is `cancelled_partial` and the best solution is stored.

## 5. Infeasibility explanation

If the status is INFEASIBLE:
1. Rebuild the model with an assumption literal `a_g` guarding each hard group `g`. The groups are: each declared hard constraint instance, each pin, each availability row, the no-overlap of each resource, and each pooled requirement's candidate set.
2. Solve with every `a_g` as an assumption, then read `SufficientAssumptionsForInfeasibility()`.
3. Shrink the core greedily. Drop `a_g`; if the model is still infeasible, keep it dropped. Each re-solve has a short time limit (default 5 s). The total budget is 60 s.
4. Store one `diagnostic` of kind `infeasible_core`. Its `refs` list the groups, and its message names entities by code, for example: `Conflicting rules: Teacher HAWE unavailable Tue–Thu; 8 events of 2 periods for HAWE; no_overlap(HAWE)`.

## 6. Verifier (`core/verifier.py`)

The verifier takes a dataset snapshot and a result, and checks H0–H5 and every active declared constraint using `core/constraints/*.verify`. It returns `list[Violation(code, constraint_code, severity, penalty, refs, message)]`.

- It doesn't import `solver/`.
- It also runs on externally supplied assignments, such as a FET import (FR-14).

## 7. Scaling strategies (Phase 10, add when measured)

1. **Staged solving** by scope selector (for example `uses:(under:L4)`), locking the earlier stages.
2. **Symmetry breaking:** order the starts of interchangeable events (same kind, same fixed resources, same requirement).
3. **Decomposition:** solve the times with aggregated room-type capacity constraints, then assign rooms per slot as a bipartite matching.
4. **Hints:** start from the published run's assignment.
