## ADDED Requirements

### Requirement: Toggle task overlap markers

Calendar settings SHALL offer an Overlap markers switch, stored on this device as showOverlapMarkers in grid preferences. Missing or invalid settings SHALL default to true. Disabling it SHALL hide the yellow overlap icon on task blocks in Day/Week without changing layout, overlap detection, task colors, accessible overlap descriptions or the +N overflow controls. Switching SHALL update immediately and survive reload.

#### Scenario: Hide and restore markers
- **WHEN** the user turns Overlap markers off while tasks overlap
- **THEN** their yellow icons disappear while the blocks keep their positions and remain accessible
- **WHEN** the user turns the setting back on
- **THEN** overlapping blocks show their markers again

### Requirement: Choose calendar task color source

Calendar settings SHALL offer Task colors: By list (default) or By priority, stored on this device with the existing grid preferences as colorBy=project|priority. Missing or unknown values SHALL normalize to project. The selection SHALL apply live to Day/Week blocks and unscheduled tasks, phone Week agenda, Month task rows, and desktop/mobile Plan tasks and projected occurrences. Priority colors SHALL use the existing red/orange/blue/slate palette for P1/P2/P3/P4. List mode SHALL preserve current task accents and defaults. External events and non-calendar task lists SHALL keep their existing colors. Changing a task's priority or project SHALL update its calendar accent without reload. No task fields, server API or sync format SHALL change.

#### Scenario: Choose priority colors
- **WHEN** the user selects By priority in General > Calendar
- **THEN** all calendar tasks use their priority accent and the selection survives reload on this device

#### Scenario: Defaults and live updates
- **WHEN** old settings have no colorBy, or an unknown value
- **THEN** calendar task colors continue to use their list
- **WHEN** priority or list changes in the active color mode
- **THEN** the displayed accent updates immediately

### Requirement: Resize and scroll the unscheduled area

Day and desktop Week grids SHALL share a device-local preferred height for the unscheduled header, initially 144 px and limited to 80–480 px. Its effective height SHALL additionally leave 160 px for the time grid when the viewport permits, without overwriting the preferred height on viewport shrink. A horizontal separator SHALL resize with mouse/touch and keyboard (Up/Down 16 px, Home/End limits), exposing accessible name and current/min/max values. Dragged height SHALL persist only on release; Escape, pointercancel and window blur SHALL revert the unfinished resize. Day headings, add buttons and load indicators SHALL stay visible while each day's date-only tasks and all-day events scroll independently below them, containing overscroll. The time grid SHALL be a lower stacking context: its current-time line and dot, blocks and interval previews SHALL never paint over the opaque unscheduled header. Month and phone Week agenda SHALL retain their existing layouts.

#### Scenario: Overflow and independent day scrolling
- **WHEN** Friday has more unscheduled tasks than fit in the chosen height
- **THEN** Friday's list scrolls without moving the other lists, its heading or the time grid

#### Scenario: Resize and remember
- **WHEN** the user resizes the header and releases, then reloads or switches Day/Week
- **THEN** the preferred height is restored on this device
- **WHEN** Escape, pointercancel or blur cancels an active resize
- **THEN** the previous preference is retained

#### Scenario: Constrained viewport
- **WHEN** the calendar viewport shrinks and later grows
- **THEN** effective height respects the available space and the original preferred height returns

#### Scenario: Current-time line behind the header
- **WHEN** the time grid is scrolled beneath the unscheduled area
- **THEN** neither the current-time line nor its dot is visible over the header

### Requirement: Create a task on the time grid

Day and Week time grids SHALL open a compact task-creation form from a primary click or tap on free grid background. The selected column SHALL supply the date and the vertical coordinate relative to that column SHALL supply the time rounded down to a 15-minute slot, clamped to 00:00–23:45. The form SHALL show the date, focus the task name, and allow editing name, time and estimate, initially 15 minutes. A keyboard-accessible add button in each day header SHALL open the same form with the selected date and no initial time. Saving that form without a time SHALL create a date-only task in the Unscheduled lane; the user MAY explicitly set a time before saving. Creation SHALL use the existing operation log, appear locally immediately including offline, and converge without duplicate tasks when queued operations sync.

The form SHALL also offer an optional multiline description and a priority flag menu for P1–P4, initially P4. Both values SHALL remain local to the form until creation and SHALL be saved in the same task operation batch. Enter in the title SHALL submit; Enter in the description SHALL insert a newline. Escape SHALL dismiss an open priority menu before dismissing the creation form.

#### Scenario: Priority and description
- **WHEN** the user chooses P2, writes a multiline description and creates the task
- **THEN** the task stores P2 and the description with its line breaks, and the regular task panel shows those values

#### Scenario: Optional defaults
- **WHEN** the user creates a task without setting priority or description
- **THEN** the task has priority P4 and an empty description

#### Scenario: Nested menu keyboard dismissal
- **WHEN** the priority menu is open and the user presses Escape
- **THEN** only the menu closes, focus returns to the flag, and a second Escape cancels the form without creating a task

The grid SHALL also support interval creation by dragging from free background. Mouse movement of at least 4 pixels SHALL start selection; touch or pen SHALL start after a 350 ms hold, while movement greater than 8 pixels before the hold cancels creation and permits scrolling. The original day SHALL remain fixed. Both boundaries SHALL floor to 15-minute steps, with the earlier boundary as start, a minimum 15-minute duration, and limits of 00:00–24:00. A translucent preview SHALL show start, end and duration. Release SHALL open the existing creation form with the selected start and estimate; it SHALL not create a task before submit. Escape, pointer cancellation or window blur SHALL discard selection. Active selection SHALL support the existing edge autoscroll behavior and SHALL not activate tasks or events passed over.

#### Scenario: Drag an interval in either direction
- **WHEN** a user drags from 10:00 to 11:00 or from 11:00 to 10:00 on free background
- **THEN** the preview and creation form target 10:00 for 60 minutes on the original day

#### Scenario: Touch hold versus scroll
- **WHEN** a finger moves more than 8 pixels before 350 ms
- **THEN** scrolling continues and no creation form opens
- **WHEN** a finger holds for 350 ms then drags and releases
- **THEN** an interval is previewed and passed to the creation form

#### Scenario: Day boundary and cancellation
- **WHEN** selection reaches the end of its original day or moves horizontally to another day
- **THEN** the endpoint is limited to 24:00 on the original day
- **WHEN** Escape, pointercancel or blur interrupts selection
- **THEN** no task or creation form appears

#### Scenario: Click a scrolled week
- **WHEN** the user clicks Tuesday at 14:38 in a scrolled Week grid
- **THEN** the form targets Tuesday 14:30 with a 15-minute estimate and saving a name creates one Inbox task at that time

#### Scenario: Last slot
- **WHEN** the user clicks the bottom of a day column
- **THEN** the selected time is 23:45 and the initial estimate is 15 minutes

#### Scenario: Keyboard creation
- **WHEN** the user activates the day-header add button using the keyboard
- **THEN** the form targets that date without a time, focuses the name and supports Enter to save and Escape to cancel

#### Scenario: Cancel or invalid input
- **WHEN** the user cancels or submits an empty name, invalid time or invalid estimate
- **THEN** no task is created

#### Scenario: Save error and repeated submission
- **WHEN** saving is pending or fails
- **THEN** repeated submission creates no second task, and a failure keeps the form and entered values visible with an error

#### Scenario: Existing interactions
- **WHEN** the user opens or drags a task, resizes it, opens an event or overflow list, scrolls or cancels a pointer gesture
- **THEN** no creation form is opened by that interaction

#### Scenario: Offline then reconnect
- **WHEN** a task is created on the grid offline and connectivity returns
- **THEN** the task appears locally before reconnect and its existing queued creation syncs to the server and another local test session once, with the same date/time and estimate
