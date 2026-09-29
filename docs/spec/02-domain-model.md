# 02 — Domain Model

Status: **Authoritative.** Code lives in `backend/src/tts/core/`. The words in this file are the only vocabulary allowed in the core.

## 1. Core concepts

| Concept | Definition |
|---|---|
| **ResourceType** | A kind of resource. `exclusive: bool` means it can be used by at most one event per period. `has_capacity: bool`. `attribute_schema` gives the typed attributes. |
| **Resource** | An instance of a type, with `code` (unique per dataset), `name`, `parent` (optional, any type), `capacity` (optional), `attributes` and `tags`. |
| **Hierarchy** | The forest formed by `parent` links. It must be acyclic. |
| **Tag** | A `key=value` string pair on a resource or event, used by selectors. |
| **ReferenceType / Reference** | A non-schedulable lookup entity (for example the academic *Module*). An event may point to one reference. |
| **Day, Period** | Ordered time units. A period has `start`, `end` and `is_break`. `P` is the number of periods per day. |
| **StartPattern** | `code`, `duration` (periods), `start_periods` (period codes), `days` (optional, default all). |
| **Event** | `code`, `kind` (free label), `duration`, `start_pattern`, `reference` (optional), `delivery` (free label), `tags`, `template` (optional). |
| **Fixed requirement** | Event → Resource. The event always occupies that resource. |
| **Pooled requirement** | `event`, `resource_type`, `count ≥ 1`, `filter` (selector), `capacity_rule`. The solver chooses `count` resources that match. |
| **Availability** | `resource`, `day`, `period`, `status ∈ {unavailable, avoid}`. |
| **Constraint** | `code`, `type` (from the catalogue in `04-constraints.md`), `scope` (selector), `params`, `hard: bool`, `weight ≥ 0`, `active: bool`. |
| **Template** | A rule that expands into events (`05-solver.md` §2). |
| **Pin** | `event`, `day?`, `start_period?`, `resources?` (pooled choices), `source ∈ {user, lock}`. |
| **Run** | One solve of one dataset snapshot. |
| **Assignment** | A run's result for one event: `day`, `start_period` and the chosen pooled resources. |

## 2. Invariants (enforced on import and by the verifier)

1. Codes are unique per sheet and dataset. References resolve.
2. The hierarchy is acyclic.
3. `duration ≥ 1`. Every start in `start_pattern` must let the event fit within one day without covering a break period. Otherwise it is a pre-flight error.
4. A pooled requirement's `resource_type` must be exclusive.
5. `weight` is ignored when `hard = true`.

## 3. Occupancy rule (central to conflict detection)

An event **occupies**, during every slot it covers:
1. each of its fixed resources,
2. each **exclusive descendant** of each fixed resource, and
3. each pooled resource chosen for it.

It does **not** occupy ancestors.

Example: an event with fixed resource `L6 SE` (grouping) occupies `L6 SE / G1 … G11` (exclusive). An event for `L6 SE / G1` does not occupy `L6 SE`, so it can't clash with a sibling group through the parent.

Two events **clash** if they occupy the same exclusive resource in at least one common slot.

## 4. Time

- Slot index: `t = day_index × P + period_index`.
- An event starting at `t` covers `t … t + duration − 1`.
- `allowed_starts(event)` is the set of `t` where the day is allowed, the period is in `start_periods`, all covered periods are in the same day, and none is a break.

## 5. Selectors

A selector is a string of clauses separated by `;`, combined with AND. The literal `all` matches everything.

| Clause | Target | Matches |
|---|---|---|
| `type:<ResourceType>` | resources | resources of that type |
| `code:<c1>,<c2>` | both | the listed codes |
| `under:<code>` | resources | exclusive descendants of the resource |
| `tag:<k>=<v>` / `tag:<k>!=<v>` | both | a tag equal / not equal |
| `attr:<name><op><value>` | resources | an attribute comparison. Ops: `= != < <= > >=`. `capacity` counts as an attribute |
| `kind:<k1>,<k2>` | events | the event kind |
| `ref:<code>` | events | the event's reference (for example a module) |
| `uses:<selector-in-parens>` | events | events that have a fixed resource matching the inner selector, for example `uses:(under:L6 SE)` |

Grammar (EBNF):
```
selector := "all" | clause (";" clause)*
clause   := name ":" value
name     := "type"|"code"|"under"|"tag"|"attr"|"kind"|"ref"|"uses"
```
Values are trimmed. Codes may contain spaces and `/` (for example `L6 SE / G1`). A value containing `;` or `,` is quoted with double quotes.

## 6. Presets

A preset is a Python package under `presets/<name>/`. It provides:
- `resource_types`, `reference_types` and event `kinds`,
- the **sheet definitions** (sheet name → core table + column mapping + labels), which drive both the workbook I/O and the UI,
- default time model, constraints and templates (as data),
- UI labels.

A preset contains **no scheduling logic**.

### 6.1 `academic_weekly` preset

| Resource type | Exclusive | Capacity | Typical parent |
|---|---|---|---|
| University | no | — | — |
| Level | no | — | University |
| Programme | no | — | Level |
| StudentGroup | yes | size | Programme, or StudentGroup (subgroups) |
| Teacher | yes | — | — |
| Campus | no | — | — |
| Building | no | — | Campus |
| Room | yes | seats | Building |

- **Reference type:** Module (`code`, `name`, `level`, `programme`, `credits?`).
- **Event kinds:** LEC, TUT, LAB, SEM (configurable).
- **Delivery values:** `in_person` (default), `online`. An online event has no Room requirement.
- **Room requirement:** Room, count 1, filter `tag:room_type=<X>`, `capacity_rule = sum_of_fixed:StudentGroup` (the sum of the fixed groups' capacities).

| Academic phrase | Core expression |
|---|---|
| "Lecture for SE G1–G4" | Event kind LEC with fixed resources G1…G4 |
| "Needs a lab" | Pooled Room with filter `tag:room_type=Lab` |
| "Taught by HAWE and HARR" | Fixed resources Teacher HAWE, HARR |
| "Rooms in GP only" | Pooled filter `under:GP` combined with the room type |
| "Online" | `delivery=online`, no pooled requirement |
