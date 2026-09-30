# Pre-flight issues

## What it's for

The [Pre-flight](../tabs/preflight.md) tab lists problems in your data before any solving. Each issue has a **kind** (the grey word), a severity, a sentence and links to the rows involved. This page lists every kind, what it means and how to fix it.

- An **error** stops a run from starting. The run would be impossible or meaningless.
- A **warning** never stops a run. It is a hint.

Click the links on an issue to open the row it names.

## Errors

### `empty_start_domain`

**Message:** `6SENG005C-TUT-03: no allowed start fits duration 2`

**Meaning:** The activity's start pattern has no start where the whole activity fits in one day without touching a break.

**Fix:** Add a start that fits to the activity's [start pattern](../tables/StartPatterns.md), or shorten the activity's `duration`, or check that the pattern allows the right `days`. Remember that an activity may not cover a break period.

### `no_candidate`

**Messages:**
- `6COSC023C-LEC-01: no Room matching "tag:room_type=auditorium" with capacity ≥ 210`
- `6SENG005C-TUT-01: needs 2 Room but only 1 match "tag:room_type=lab" with capacity ≥ 60`

**Meaning:** No room (or not enough rooms) can be given to this activity. The message shows the room type it asked for, and the seats it needs: the sum of the sizes of the groups attending.

**Fix:** Check the spelling of the activity's `room_type` against the rooms' `room_type` (it is case-sensitive). Add a room of that type that is big enough, or split the activity into smaller groups. The largest room is a hard limit.

### `over_demand`

**Message:** `Teacher HAWE: needs 16 periods, 12 available`

**Meaning:** The activities a group, teacher or room is involved in add up to more periods than it has. "Available" is the periods that are not breaks, minus the ones marked `unavailable`.

**Fix:** Remove some of the resource's unavailable periods in [Availability](../tables/Availability.md), move some activities to another teacher or room, or shorten or drop activities. This is checked without solving, so the fix is certain to be needed.

### `conflicting_pins`

**Messages:**
- `Pins: 2 activities pinned to [2LA] -GP on Wed P01`
- `Pins: 2 activities pinned to L6 SE / G1 with overlapping times from Mon P01`

**Meaning:** Two or more pins put activities on the same group, teacher or room at the same time.

**Fix:** Open the [Pins](../tables/Pins.md) table (or unpin on the [Timetable](../tabs/timetable.md)) and change or delete one of them.

### `invalid_selector`

**Messages:**
- `C-GAPS: scope "teacher:": unknown clause "teacher:"`
- `X: scope "type:Teacher": clause "type:" does not select events`
- `6SENG005C-TUT-01#0: filter "...": …`

**Meaning:** A selector cannot be read, or picks the wrong kind of thing for where it is used.

**Fix:** See [Selectors](../constraints/selectors.md). The text after the last colon says what is wrong.

### `invalid_constraint`

**Messages:**
- `constraint "X" (max_gaps): max: Field required`
- `constraint "X" (max_gaps): per: Input should be 'day' or 'week'`
- `constraint "X" (max_gaps): max: Input should be a valid integer, unable to parse string as an integer`
- `constraint "X" (order): sequence names unknown event "A"`
- `constraint "X" (order): sequence: List should have at least 2 items after validation, not 1`
- `constraint "X" (travel_gap): level "Hut" is not a resource type`
- `constraint "X" (preferred_times): slot "Mon-P01" is not written as Day:Period`
- `constraint "X" (preferred_times): slot "Xyz:P01" names an unknown day or period`
- `constraint "X" (preferred_resources): filter "teacher:": unknown clause "teacher:"`

**Meaning:** The `params` of an active constraint are wrong: a setting is missing, has the wrong kind of value, or names something that does not exist. The import does not check this, so the problem shows here.

**Fix:** Correct `params` in the [Constraints](../tables/Constraints.md) table. Each type's page lists its parameters: see the [constraint list](../constraints/README.md).

### Data model rules

These come from the structure of the data. Import and the table editor normally stop them before you see them, but pre-flight reports them under these kinds if they occur. The message starts with the kind of row and its key, for example `resource "L6 SE / G1": …`.

| Kind | Example message | Meaning and fix |
|---|---|---|
| `duplicate_code` | `resource "AAM": duplicate code "AAM"` | Two rows share a code. Make them different |
| `unknown_reference` | `fixed "6SENG005C-LEC-01/NOBODY": unknown resource "NOBODY"` | A row refers to something that does not exist. The message names what kind of thing: a resource type, a parent, a period, a day, a start pattern, a reference, an event or a resource. Correct the code or add the row |
| `hierarchy_cycle` | `resource "L6 SE / G1": parent cycle: A → B → A` | Parents form a loop. Break it |
| `unknown_attribute` | `resource "GP": unknown attribute "x"` | A resource has an attribute its type does not define |
| `bad_attribute` | `resource "GP": attribute "abbreviation" is not str` | An attribute has the wrong kind of value |
| `unexpected_capacity` | `resource "AAM": type Teacher has no capacity` | A capacity was given to a type that has none. Only groups and rooms have one |
| `pooled_not_exclusive` | `pooled "…#0": type Campus is not exclusive` | An activity asks for a resource of a type that can be shared. Only exclusive types (groups, teachers, rooms) can be chosen |
| `demand_participant_not_exclusive` | `demand "6SENG005C-TUT": participant "L6 SE" is not of an exclusive type` | A demand (the groups a module's sessions are split between) names something that can be shared, such as a programme. Name the groups themselves. Only datasets built from configuration have demands |
| `demand_mixed_participants` | `demand "6SENG005C-TUT": participants are of different types: Room, StudentGroup` | The participants of one demand must all be of the same type. Split it into two |
| `edit_outside_demand` | `event "6SENG005C-TUT-03": "L6 SE / G99" is not a participant of demand "6SENG005C-TUT"` | An edited session keeps a group that the module does not teach. Undo the edit, or add the group to the module |
| `edit_too_large` | `event "6SENG005C-TUT-03": 4 participants, more than the limit of 3 of demand "6SENG005C-TUT"` | An edited session keeps more groups together than the session type allows. Undo the edit, or raise the limit |
| `mixed_dataset` | `event "X-LEC-01": a dataset with demands cannot also have events without a demand` | A dataset built from configuration also has activities typed by hand. Use one or the other |

If the data has one of these problems, **only** these issues are shown, because the other checks need sound data. Fix them and press **Check again**.

## Warnings

### `pooled_pressure`

**Message:** `Room tag:room_type=lab: 64 periods needed, 60 available`

**Meaning:** The activities that need this kind of room add up to more periods than all the matching rooms have. It is a warning, not an error, but a run is very unlikely to succeed.

**Fix:** Add rooms of that type, reduce the demand, or widen the rooms' availability.

### `unused_resource`

**Message:** `Room [1LA] -GP is never a candidate`

**Meaning:** The room is of a type activities ask for, but no activity can use it (its type or size never matches).

**Fix:** Probably a typo in the room's `room_type`, or a room that is too small. Fix it, or ignore the warning if the room is deliberately unused.

### `empty_scope`

**Message:** `C-GAPS: scope matches nothing`

**Meaning:** The selector of an active soft constraint picks nothing, so the rule has no effect.

**Fix:** Check the selector and the tags or codes it names. See [Selectors](../constraints/selectors.md).

## Related

- [Pre-flight tab](../tabs/preflight.md)
- [Import and editing errors](import-errors.md)
- [Run statuses](run-statuses.md)
