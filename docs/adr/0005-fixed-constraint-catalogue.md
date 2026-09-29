# ADR-0005: A fixed, parameterised constraint catalogue

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
Users need many rule variations, but every rule must be verifiable, compilable to CP-SAT, explainable and testable.

## Options
1. **A rule or expression language.** Flexible, but hard to compile efficiently, hard to explain, and a large test surface.
2. **A fixed catalogue of constraint types**, each with a params schema, scope selector, hard/soft flag and weight.

## Decision
Option 2 (spec 04). New behaviour means a new catalogue type with verify, compile and tests.

## Consequences
- Rules are data in the `Constraints` sheet.
- Infeasibility explanations can name specific constraint instances.
