# Command-line reference

The `tts` command runs the whole engine without a server: read a workbook, check it, solve it and verify the result. Run it from `backend/` as `uv run tts <command>` (see [`backend/README.md`](../backend/README.md) for setup). `uv run tts --help` and `uv run tts <command> --help` print the same information as this page.

| Command | What it does |
|---|---|
| [`tts import-fet`](#tts-import-fet) | Convert a FET "groups" HTML export into a workbook |
| [`tts export`](#tts-export) | Rewrite a workbook in canonical form, or convert between formats |
| [`tts preflight`](#tts-preflight) | Find what makes a timetable impossible, without solving |
| [`tts solve`](#tts-solve) | Pre-flight, solve, verify and write the timetable back |
| [`tts validate`](#tts-validate) | Check a workbook's existing assignments with the verifier |

A typical session runs them in this order: `import-fet` (once, to get a workbook), edit the workbook in Excel, `preflight` (quick check), `solve`, then `validate` if the assignments were edited by hand.

## Workbooks and file formats

A **workbook** is either an `.xlsx` file or a `.zip` of CSV files. The extension chooses the format, for input and for output. Anything else exits with code 2 and the message `use .xlsx or .zip`. The layout is the contract in [spec 03](spec/03-workbook-format.md).

- **Reading is all or nothing.** If anything is wrong, every problem is printed as `<Sheet>!R<row>C<col> [<column>]: <message>` (for example `Rooms!R2C4 [capacity]: expected integer ≥ 0, got "thirty"`), followed by `<command>: N problem(s) found; nothing was read`. The command exits with code 1 and writes nothing.
- **Formulas are never evaluated.** Only the values Excel saved are read.
- **Files over 20 MB are refused.**
- **Your own columns survive.** Columns whose names start with `x_` and sheets whose names start with `_` are kept or ignored, never treated as errors.

Error messages and violations go to standard error. Progress lines, warnings and summaries go to standard output.

## Exit codes at a glance

| Code | Meaning | Commands |
|---|---|---|
| 0 | Success | all |
| 1 | The input could not be read (a problem list is printed), or the command could not do its job (see each command) | all |
| 2 | Usage error: missing input file, unknown file extension, or (for `solve`) no timetable exists or none was found in time | all |
| 3 | The verifier found a hard violation | `solve`, `validate` |
| 4 | Pre-flight found an error | `solve`, `preflight` |

Code 2 means different things for `solve`; see below.

---

## `tts import-fet`

Convert a FET "groups" HTML export into a workbook.

```
tts import-fet <html> --out <file> [--with-assignments] [--no-defaults]
```

| Argument or option | Meaning |
|---|---|
| `<html>` | The FET groups HTML export. Must exist. |
| `--out`, `-o` | File to write: `.xlsx`, `.zip` (CSV) or `.json`. Required. |
| `--with-assignments` | Also write the export's own placements (an `Assignments` sheet). Off by default, so the workbook holds the configuration only. |
| `--no-defaults` | Leave out the preset's default soft constraints. By default the `Constraints` sheet gets them: `AC-GAPS` and `AC-TGAPS` (fewer gaps for groups and teachers), `AC-SAT` (no Saturday teaching) and `AC-TRAVEL` (inactive; see spec 04 §3). The committed `l6.xlsx` fixture is written with `--no-defaults`. |

The export has no group sizes, room capacities or room types, so those are **assumptions** (group size 30, Auditorium 250, other rooms 30 × the most groups seen in one event in that room, and so on). They are written to the workbook's `_meta` sheet under `assumptions`, and listed in the fixture's [README](../backend/tests/fixtures/l6/README.md). Replace them with real values before trusting a solve.

A `.json` output holds the dataset, the placements, the assumptions and any anomalies instead of a workbook. It is meant for tools and tests, and `tts export` can turn it into a workbook.

The command prints `Read N groups and M events; wrote <file>.`, then one `Anomaly:` line for each label that disagrees with its grid position (the grid position wins).

| Exit code | When |
|---|---|
| 0 | The file was written |
| 1 | The export could not be read (for example `no group tables found`), or the dataset could not be written to the workbook format. Nothing is written. |
| 2 | The input file is missing, or `--out` has an unknown extension |

```bash
uv run tts import-fet tests/fixtures/l6/fet-groups-export.html --out l6.local.xlsx
uv run tts import-fet tests/fixtures/l6/fet-groups-export.html --out l6-full.local.xlsx --with-assignments
uv run tts import-fet tests/fixtures/l6/fet-groups-export.html --out tests/fixtures/l6/l6.xlsx --no-defaults
```

The L6 export contains real teacher codes. Name generated files `*.local.xlsx`, which git ignores.

---

## `tts export`

Rewrite a workbook in canonical form, in either format.

```
tts export <source> --out <file> [--with-assignments]
```

| Argument or option | Meaning |
|---|---|
| `<source>` | A workbook (`.xlsx` or CSV `.zip`), or an import `.json` made by `tts import-fet`. Must exist. |
| `--out`, `-o` | File to write: `.xlsx` or `.zip` (CSV). Required. |
| `--with-assignments` | Only for an import `.json`: include the placements. A workbook keeps whatever assignments it already has. |

Use it to convert between Excel and CSV, or to tidy a hand-edited workbook: sheets go back to their standard order, dropdowns and frozen headers are restored, and `x_` columns are kept. The whole input is read and checked first, so a workbook with problems is reported and not converted. Converting there and back loses nothing.

| Exit code | When |
|---|---|
| 0 | The file was written (`Wrote <file>.`) |
| 1 | The workbook has problems, the `.json` is not an import file, or the dataset cannot be expressed in the workbook format |
| 2 | The input is missing, or the input or output has an unknown extension |

```bash
uv run tts export book.xlsx --out book.zip          # Excel to CSV
uv run tts export import.json --out book.xlsx --with-assignments
```

---

## `tts preflight`

Run the pre-flight checks on a workbook, without solving. It takes well under a second on L6.

```
tts preflight <workbook>
```

Each finding is printed as `ERROR <kind>: <message>` (standard error) or `WARNING <kind>: <message>`, followed by a summary line `Pre-flight: N error(s), M warning(s).`. Messages name entities by code, with the preset's words for types (for example `Teacher HAWE: needs 16 periods, 0 available`).

An **error** means no timetable can exist, so `solve` will not start. A **warning** is a likely mistake that does not block.

| Kind | Severity | Meaning |
|---|---|---|
| `unknown_reference`, `hierarchy_cycle`, `duplicate_code`, and other invariant kinds | error | The data is not sound (an unknown code, a parent cycle, …). When any of these is found, only these are reported. |
| `empty_start_domain` | error | An event has no allowed start that fits its duration (day end, breaks, start pattern). |
| `no_candidate` | error | No resource can serve a pooled requirement (type, filter and capacity), or fewer than the count needed. |
| `over_demand` | error | A resource is needed for more periods than it has (breaks and unavailable periods removed). |
| `conflicting_pins` | error | Two or more pinned events would occupy the same resource at overlapping times. |
| `invalid_selector` | error | A requirement's filter or a constraint's scope is not a valid selector. |
| `pooled_pressure` | warning | A kind of pooled resource is needed for more periods than all its candidates offer. |
| `unused_resource` | warning | A resource of a pooled type is never a candidate of any requirement. |
| `empty_scope` | warning | A soft constraint's scope matches nothing. |

A workbook with no findings can still be infeasible. Pre-flight only finds necessary conditions; the solver decides the rest.

| Exit code | When |
|---|---|
| 0 | No errors (warnings are allowed) |
| 1 | The workbook could not be read |
| 2 | The workbook file is missing or has an unknown extension |
| 4 | At least one error |

```bash
uv run tts preflight l6.local.xlsx
```

---

## `tts solve`

Solve a workbook and write it back with an `Assignments` sheet.

```
tts solve <workbook> --out <file> [--time-limit SECONDS] [--workers N] [--seed K]
```

| Argument or option | Default | Meaning |
|---|---|---|
| `<workbook>` | | A workbook (`.xlsx` or CSV `.zip`). Must exist. |
| `--out`, `-o` | required | Result file: `.xlsx` or `.zip` (CSV). |
| `--time-limit` | `120` | Seconds the search may take. |
| `--workers` | one per CPU | Search workers. |
| `--seed` | `0` | Random seed. With `--workers 1` and the same seed, the same input always gives the same timetable. Other seeds give other valid timetables. |

The steps, in order:

1. **Read** the workbook (all or nothing). Any `Assignments` sheet in it is ignored, and a note says so.
2. **Pre-flight.** Warnings are printed and the solve continues. An error stops here (exit 4).
3. **Solve** with OR-Tools CP-SAT for the hard rules. It prints `Solver: <status> in <s> s (<n> worker(s), seed <k>, <c> conflicts).`. Declared constraints the solver cannot compile yet are refused if hard (exit 1) and skipped with a `Warning:` if soft.
4. **Verify.** The independent verifier re-checks the result and prints `Verifier: N hard violation(s), M soft, K warning(s).`, then `Score: S (CODE s (p x w), …).`: the weighted sum of the soft penalties, largest part first (spec 04 §0). A result with a hard violation is a bug: it is printed as `Violation:` lines and **not written** (exit 3).
5. **Write** the workbook with the `Assignments` sheet, and print `Wrote <file>.`. The run is labelled `seed-<k>`, and your `_meta` and `x_` columns are kept.

| Exit code | When |
|---|---|
| 0 | A valid timetable was written |
| 1 | The workbook could not be read, or it declares a hard constraint the solver does not support yet |
| 2 | No timetable exists (`no result (infeasible): no timetable exists`), none was found within the time limit, or a usage error (missing input, unknown extension). When no timetable exists, an `Explanation:` line names the rules that conflict (see below) |
| 3 | The solver's result broke a hard rule and was not written |
| 4 | Pre-flight found an error; nothing was solved |

Nothing is written for any exit code other than 0.

**When no timetable exists**, `solve` works out a small set of rules that cannot all hold together and prints it, for example:

```
Explanation: Conflicting rules: Teacher THE unavailable Mon P01; pin of 6BUIS019C-LEC-01 to Mon P01
```

The rules it can name are availability rows (merged into day and period ranges), pins, an event's allowed start times, a pooled requirement (for example a room of some type), a resource's one-event-at-a-time rule (`no_overlap(<code>)`, with the load on it), and declared hard constraints. Dropping or changing any one of the listed rules makes that conflict go away (there may be others). The search takes at most 60 seconds; if it runs out of time, the message says the list may include rules that are not needed.

```bash
uv run tts solve l6.local.xlsx --out l6-solved.local.xlsx --time-limit 30
uv run tts solve l6.local.xlsx --out a.local.zip --workers 1 --seed 5   # reproducible, CSV output
```

The real L6 timetable (77 events) solves in about 0.1 s.

---

## `tts validate`

Check the assignments in a workbook with the independent verifier. Use it on a result from `solve`, on a timetable edited by hand, or on placements imported from FET (`import-fet --with-assignments`).

```
tts validate <workbook>
```

| Argument | Meaning |
|---|---|
| `<workbook>` | A workbook (`.xlsx` or CSV `.zip`) with an `Assignments` sheet. Must exist. |

Every finding is printed as `<SEVERITY> <constraint code>: <message>` (for example `HARD H1: …` for a double-booking), followed by `Verifier: N hard violation(s), M soft, K warning(s).` and `Score: S …` (the weighted soft penalties). Hard violations make the result invalid. Soft violations are preferences with a penalty, and warnings are informational (for example, a declared constraint type the verifier does not check yet).

The check covers the implicit hard rules H0–H5 (every event placed at an allowed start, no double-booking, availability, capacity, requirement match, pins) and every active declared constraint that has a verifier. It does not run pre-flight and does not solve.

| Exit code | When |
|---|---|
| 0 | No hard violation |
| 1 | The workbook could not be read, or it has no `Assignments` sheet |
| 2 | The file is missing or has an unknown extension |
| 3 | At least one hard violation |

```bash
uv run tts validate l6-solved.local.xlsx
```

---

## Planned commands

Later phases add commands and options as they land; this page is updated with each one. Not built yet: expanding templates into events (Phase 9), and running the API and the worker (Phase 6).
