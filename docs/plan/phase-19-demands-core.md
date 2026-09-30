# Phase 19 — Demands in the core, the verifier and pre-flight

**Goal:** the core can describe a demand and check a result that contains created events, before the solver knows how to make one (rule 2: the verifier comes first).

## Read first
- `docs/adr/0007-solver-decided-sessions.md`
- `docs/spec/02-domain-model.md` §1–§3, `docs/spec/04-constraints.md` §1, `docs/spec/05-solver.md` §2, §3 and §6
- `backend/src/tts/core/model.py`, `core/verifier.py`, `core/hierarchy.py`, `core/constraints/`, `preflight/checks.py`

## Tasks
- [x] P19.1 Core model:
  - `Demand` (frozen, sorted by code in `Dataset.demands`), `Demand.blocks` (`⌈|participants| / max_participants⌉`, 1 with no limit) and `Event.demand`;
  - the invariants in `Dataset.validate_invariants`:
    - participants exist and are exclusive;
    - `max_participants ≥ 1` and `repeat ≥ 1`;
    - an event's `demand` exists;
    - a declared event of a demand has only that demand's participants as fixed resources of the participant type;
    - a dataset doesn't mix demands with events that have no demand;
  - unit tests for each invariant. The core purity test still passes.
- [x] P19.2 Results with created events:
  - the result type carries created events: code, demand, kind, duration, participants, and their assignments;
  - the occupancy helpers (`Hierarchy.occupied_resources` and the clash finder) treat a created event like a declared event whose fixed resources are its participants;
  - round-trip tests of the result JSON.
- [x] P19.3 Verifier H6 `demand_cover`:
  - the events of a demand (declared plus created) group into blocks by their participants;
  - each participant is in exactly one block;
  - there are `Demand.blocks` blocks, each with exactly `repeat` events and at most `max_participants` participants;
  - block sizes differ by at most one;
  - a created event has a known demand, and the demand's duration, start pattern and pooled requirements;
  - H1–H5 hold for created events. H3 `sum_of_fixed` counts the participants.

  Tests first: a correct split; a group left out; a group in two blocks; a block with too many groups; uneven blocks (3 + 3 + 3 + 1); a block with one event missing; a repetition with different companions; an event too big for its room; a clash between two created events. Each should give the expected violations with entity codes.
- [ ] P19.4 Every declared constraint's `verify` accepts created events, with their participants as fixed resources:
  - resource-scoped types count them for their participants;
  - event-scoped types select them with `ref:`, `kind:`, `tag:` and `uses:`.

  One extra test per catalogue type with a created event in scope.
- [ ] P19.5 Pre-flight checks for demands, from spec 05 §3:
  - no candidate pooled resource for a demand: the biggest possible block (the `⌈m/k⌉` largest groups) must fit a room of the type, and the teacher pool must not be empty;
  - a participant's demand is more than its available periods;
  - pooled pressure for demands (the blocks × `repeat` × duration);
  - a demand with no participants (warning);
  - a `code:` scope that matches no declared event while demands exist (warning);
  - an edit (a declared event of a demand) whose groups are not all participants of that demand, or that makes a block bigger than `max_participants` (error: pre-flight names the edit to undo).

  Each check gets a test and a message with codes.

## Acceptance
- `tts validate` on a hand-written result with created events reports exactly the violations each broken variant should have, and none for the correct one.
- The core purity and import-linter checks pass, and the verifier imports nothing from `solver/`.
- L6 still gives the figures in `expected.json`.
