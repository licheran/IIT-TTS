# ADR-0001: Generic scheduling core with domain presets

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
The first target is academic weekly timetabling (FR-15), but the product must not be limited to it (FR-16, NFR-5). The institute's data varies: levels, programmes, universities and buildings, some not yet known.

## Options
1. **An academic-only model** (Teacher, Room and Group as first-class tables). Fastest to build, but every new domain or variation needs code changes.
2. **A fully user-defined meta-model with a rule language.** Maximum flexibility, but it becomes a database product in its own right, is hard to validate, and is hard to solve efficiently.
3. **A fixed generic core** (resources, events, requirements, time, constraints) **plus presets** that supply types, sheets, labels and defaults.

## Decision
Option 3. The core is fixed and domain-neutral. Presets are configuration only. Academic variation (levels, programmes, universities, buildings) is expressed through the hierarchy and tags.

## Consequences
- The core-purity and dependency tests are required (spec 06 §8).
- The UI and workbook I/O must be driven by the preset's sheet definitions.
- A new domain means a new preset. Phase 11 proves it.
