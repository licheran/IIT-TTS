# ADR-0004: The workbook as the canonical interchange format

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
Administrators work in spreadsheets. The configuration must be editable in Excel or CSV and imported and exported without loss (FR-2, FR-3).

## Options
1. **A JSON or XML project file** (like FET's `.fet`). Precise, but not friendly for spreadsheet users.
2. **An ad-hoc CSV per entity** with inline lists. Easy, but ambiguous for many-to-many relationships and for round trips.
3. **A versioned workbook contract**: one sheet per table, code references, canonical join sheets, atomic validation with row-level errors.

## Decision
Option 3 (spec 03), with the same sheets available as a CSV zip.

## Consequences
- Any format change needs a version bump and a migration note.
- The UI table editors mirror the sheets one to one.
