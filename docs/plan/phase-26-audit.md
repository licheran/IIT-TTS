# Phase 26 audit: the web app's controls and layout (P26.1)

Done on 2026-10-09 against the configured L6 dataset (`l6-config.xlsx`, solved once), at viewport widths 1280 and 1024 px, in Chromium. The screens: Datasets, Import / export, Tables (Session, Teachers, Modules, Groups, Rooms, Session types, Activities, with the entry row, a list editor and the tag editor open), Pre-flight, Run (before and after), Timetable and Runs. The measurements are bounding-box heights of every visible `a`, `button`, `input`, `select` and `[role=tab]`.

## What is there

- About 3,000 lines of application code; one shared control, `components/ui/button.tsx`. Every other control is styled in place (28 raw `<input>`, `<select>`, `<button>` or dialog elements outside tests).
- `index.css` holds no design tokens. Nothing says what a control's height, a gap or a radius is.
- The overlay panels of `components/editors.tsx` (`MultiRefSelect`, `TagEditor`) are `absolute` boxes inside the table cell.

## Measured: control heights (px, all screens at 1280)

| Element | Heights found (count) |
|---|---|
| `button` | 28 (138), 32 (61), 36 (4), 79 (6) |
| `input` text | 32 (47), 33 (1), 36 (1) |
| `input` number | 32 (11), 36 (6) |
| `select` | 32 (2), 36 (6) |
| links and tabs | 20 (19), 28 (17), 30 (162), 32 (90), 36 (6) |

Three heights (28, 32, 36) are in use for the same kind of control, and the table's entry-row inputs (32) are taller than the rows they sit above (34 with their border, but visibly heavier because of the blue borders).

## Findings

| # | Finding | Where | Seen at | Fixed by |
|---|---|---|---|---|
| A1 | **The tag editor and list editors are clipped.** The popover is positioned inside the cell, so the grid's scroll area cuts it: "Cancel" is half hidden and "Done" is under the Delete column. | Tables (Rooms `tags`) | 1280, 1024 | P26.3 (popover primitive in a portal) |
| A2 | **The Delete buttons are cut off** at the right edge ("Delet"), and so is the entry row's Add button, because the grid is wider than the page and the last column has no room. | every table with many columns | 1280, 1024 | P26.5 |
| A3 | **Three sizes for one kind of control** (buttons 28/32/36, inputs and selects 32/36). Buttons beside selects on the Timetable bar differ in height. | everywhere | both | P26.2 (tokens, `Input`, `Select`, `Button` sizes) |
| A4 | **Two tab styles.** The section tabs (Tables, Import / export, ...) are dark pills; the table tabs are outlined pills with a blue active state. The 20 table tabs wrap into two ragged rows, and their order moves when a tab is added (Session shifted the second row). | Tables | both | P26.2 (`Tabs`), P26.5 (one row with scroll, or a menu) |
| A5 | **Very wide tables hide their last columns.** Session has nine columns and only five are visible at 1024; the user has to scroll the grid sideways and has no cue. | Tables | 1024 | P26.5 |
| A6 | **Entry row inputs are heavier than the data rows** (a full blue border on every field), so the first thing the eye meets is the empty row, not the data. | Tables | both | P26.2 |
| A7 | **Buttons of 79 px height** appear on screens with a stretched submit button (the form buttons that fill a grid cell). | Datasets, Import | 1280 | P26.2 |
| A8 | **A list cell without a reference list shows a plain text box** (`Teachers.modules`, with `module:KIND` items): the user has no help to find a module code, which is the problem the drawer solves. | Tables | both | P26.4 |
| A9 | **No grey "inherited" value** in a blank Session cell, so the row looks empty. The wiki says where the value comes from. | Tables (Session) | both | left blank on purpose (P24.6); revisit with the drawer |
| A10 | **The Timetable bar has four export buttons of equal weight** that wrap at 1024. | Timetable | 1024 | P26.5 |
| A11 | Page shifts: the Pre-flight tab shows "Checking…" and the count after it loads, which moves the table below it. | Pre-flight | both | P26.5 (reserve the space) |

Not a problem: no sideways scrolling of the whole page at either width (only inside the grid), and the Activities, Run and Runs screens are consistent with each other.

## Result (end of Phase 26)

| # | Outcome |
|---|---|
| A1 | Fixed: the popovers are `CellPopover` (Radix, in a portal), so the grid cannot clip them |
| A2 | Fixed: the Delete, Add and action cells stay in view at the right edge (`sticky`) |
| A3 | Fixed: two control heights (`h-control` 32 px, `h-control-sm` 28 px) from `index.css`; `components/ui/` holds `Button`, `Input`, `Select`, `Check`, `Field`, `Notice`, `Badge`, `NavTab`, `Drawer`, `CellPopover`; a test (`raw-controls.test.ts`) keeps raw controls and fixed heights out of the features |
| A4 | Fixed: both tab styles are `NavTab` at one height. The 20 table tabs still wrap onto two lines: accepted, because scrolling them sideways would hide tables |
| A5 | Partly: the action cells stay in view; a wide table still scrolls sideways inside its grid |
| A6 | Left as it is: the blue entry row is the one place the user types a new row, and the e2e keyboard flow depends on it |
| A7 | Fixed with A3: no stretched buttons remain |
| A8 | Fixed: `Teachers.modules` has the lookup (`ColumnDef.suggests`) |
| A9 | Left blank on purpose (see P24.6); the wiki says where the value comes from |
| A10 | Left: the bar wraps cleanly at 1024 px |
| A11 | Fixed: the Check again button keeps its width while it says "Checking…" |

## Libraries checked (registry, 2026-10-09)

| Package | Version | React 19 | Notes |
|---|---|---|---|
| `radix-ui` (and `@radix-ui/react-*`) | 1.7.0 | yes (`^19.0`) | Unstyled; no Tailwind dependency; Dialog (can be non-modal), Popover, Tabs, Select are what this phase needs |
| `react-aria-components` | 1.22.0 | yes | About 7 MB unpacked; more than this phase needs |
| `@base-ui/react` | 1.9.0 | yes | Unstyled; newer, smaller community |
| `vaul` | 1.1.2 | yes | A drawer only |

Recommendation: **Radix primitives** wrapped in `components/ui/` with our Tailwind classes (the pattern `button.tsx` already follows).
