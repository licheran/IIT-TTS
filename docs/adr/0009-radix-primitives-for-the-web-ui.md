# ADR-0009: Radix primitives, wrapped in our own Tailwind components

- **Status:** Accepted
- **Date:** 2026-10-09 (answers of the user to P26.1)

## Context
Phase 26 adds a read-only reference drawer beside the tables and asks for one set of controls. The audit (`docs/plan/phase-26-audit.md`) found one shared control (`components/ui/button.tsx`), three heights in use for the same kind of control, and popovers that the grid's scroll area clips. The web app is about 3,000 lines, styled with Tailwind 4, `class-variance-authority`, `clsx` and `tailwind-merge`, with a headless table (TanStack). FR-1 and NFR-8 apply: the tables stay responsive with 5,000 rows, and the entry row works by keyboard alone (Phase 12).

## Options
1. **Radix primitives in our Tailwind style.** Unstyled building blocks (`radix-ui` 1.7.0, React 19 ready, no Tailwind dependency) for the drawer (Dialog, non-modal) and the popover, wrapped in `components/ui/` as `Button` already is. The look and the grid stay as they are.
2. **No library.** Cheapest now, but focus handling, Escape, clipping and screen-reader support are hand-made, which is where today's problems come from.
3. **A full styled library (MUI, Mantine, Ant Design).** A rewrite of every screen and a second styling system next to Tailwind, built for forms and dashboards more than for a dense grid.

## Decision
Option 1. Add `radix-ui`, pinned exactly like the other dependencies. Use only Dialog (non-modal, for the drawer) and Popover, and only through wrappers in `web/src/components/ui/`. Raw `<input>`, `<select>` and `<button>` stay allowed only in those wrappers and in the table's cell editors. Design tokens (control height, row height, spacing, radius, text sizes, focus ring) live in `index.css`.

## Consequences
- One dependency to keep current. The table, the router and the data layer are untouched.
- Popovers render in a portal, so the grid cannot clip them.
- Every `aria-label` that tests and the wiki pictures rely on is kept when a screen moves to the new controls.
- The app's tabs are routes (links), so they are a plain component (`NavTab`), not Radix Tabs, which would need panels.
- A different look (a redesign) is a separate decision; this one only makes the current look consistent.
