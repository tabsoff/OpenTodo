# Proposal

## Why

The calendar grid can place existing tasks but cannot create a task directly at an empty time. Enable quick local-first capture without leaving Day or Week.

## What Changes

- Single-click/tap an empty grid slot to open a compact creation form, with its date and quarter-hour time selected and a 15-minute estimate.
- Drag in either direction to select a quarter-hour interval, with touch hold, edge scrolling and cancellation. The existing creation form supports priority and multiline description.
- Add a keyboard-accessible day-header add button for date-only tasks, without an implicit start time.
- Resize the shared Day/Week unscheduled area, with independent day scrolling and time-grid overlays kept below it.
- Choose list or priority colors across calendar views and optionally hide Day/Week overlap markers through device-local settings.
- Prepare a localhost-only Windows development preview with synthetic data and start/stop helpers; preview changes before any PR or deployment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `time-blocking`: create tasks from free space in Day and Week grids, including offline capture, keyboard access, interval selection, resizable unscheduled lanes and calendar appearance preferences.

## Impact

Frontend calendar components and tests, translations, operator preview scripts. Advances the existing time-blocking/calendar capability; no new ROADMAP product area. No API, schema, op format, mandatory application environment variables or application dependencies. Month/phone layouts and recurrence rules are unchanged; their task color accents follow the new preference. The owner approved the local result; PR and CI may now proceed. Production deployment requires separate approval.
