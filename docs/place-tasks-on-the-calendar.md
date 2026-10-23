---
title: Place tasks on the calendar
summary: Drag tasks onto time slots or move them with the keyboard, change how long a block lasts, and read each day's planned hours against its capacity.
audience: user
section: Guides
specs: [time-blocking]
screens: []
order: 62
---
# Place tasks on the calendar

<picture><source srcset="images/day-dark.webp" media="(prefers-color-scheme: dark)"><img src="images/day-light.webp" alt="The Day calendar with the day's tasks as blocks between morning and evening."></picture>

Once tasks have [estimates](time-blocking.md#estimate-how-long-a-task-takes), the Day and Week calendar is where you decide when to do them. Opening the calendar and the Month view are covered in [Day, Week and Month](calendar-views.md).

## Create a task on the grid

Click a free slot in **Day** or desktop **Week**. The form uses that day and rounds time down to 15 minutes. Enter a name, adjust time or estimate, then press <kbd>Enter</kbd> or **Add a task**. The initial estimate is 15 minutes; tasks go into **Inbox**.

The flag selects **P1–P4** (initially **P4**). **Description** accepts optional multiline notes. <kbd>Enter</kbd> in the name saves; in the description it adds a line. Both fields appear in the regular task panel.

The keyboard-accessible header **+** opens a date-only draft; saving without a time keeps it Unscheduled. <kbd>Esc</kbd> closes the priority menu first, then the form; **Cancel** discards it. Errors retain your input. Offline creation syncs on reconnection.

## Place a task on the calendar

Drag over free grid background in either direction to select a duration. A preview shows the interval; release opens the form. Boundaries use 15-minute steps within the original day, with a 15-minute minimum. On touchscreens, hold 350 ms before dragging; quick swipes scroll. Edges auto-scroll. Escape, touch cancellation or window blur cancels.

Drag a task from the Unscheduled lane onto a time slot. Its due date and time become that slot. The grid works in 15-minute steps.

To plan from your lists, open the side list with **Plan from a list** and drag tasks from there onto the calendar.

To change how long something takes, drag the bottom edge of its block. Dropping a block back on the Unscheduled lane keeps the date and removes the time.

### With the keyboard

Every move works without a mouse.

1. In Today, a project or any list, select a task and press <kbd>s</kbd>. The Day view opens with the task ready to place.
2. Move it with the arrow keys: <kbd>↑</kbd> / <kbd>↓</kbd> by 15 minutes, <kbd>←</kbd> / <kbd>→</kbd> by a day.
3. Press <kbd>Enter</kbd> to place it, or <kbd>Esc</kbd> to cancel.

On the calendar itself, <kbd>j</kbd> / <kbd>k</kbd> select tasks, the arrows move the selected one, <kbd>Shift</kbd>+<kbd>↑</kbd> / <kbd>Shift</kbd>+<kbd>↓</kbd> shorten or lengthen it, and <kbd>u</kbd> takes it off the grid while keeping its date.

## See whether the day fits

Drag the divider below **Unscheduled** to resize Day/Week's upper area. Each day scrolls independently below fixed headings. Device-local height defaults to 144 px (80–480 px, limited by window height). Focus the divider: Up/Down adjust 16 px; Home/End select limits. Escape cancels a pointer resize. Time-grid overlays stay below this area.

Each day's header adds up the estimates of its open tasks and compares them with your day length, for example `4h 15m / 8h`. When you've planned more than the day holds, the header is marked as over capacity. That's your cue to move something.

Tasks that overlap in time are shown side by side, with a marker, so nothing hides behind something else.

Completing a task removes its block and lowers the day's total.

Your day length and the hours the grid shows are set per device in **Settings → General → Calendar**; see [Adjust the grid](time-blocking.md#adjust-the-grid).
