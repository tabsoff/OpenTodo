# Design

## Context

DayColumn already exposes absolute day coordinates and the drag math floors to quarter-hour slots. CalendarView owns a date-only AddOnDayDialog also used by Month/phone agenda. Existing createTask writes a local operation batch and wakes sync.

## Goals / Non-Goals

Implement the approved click and drag interval creation flow on the grid; preserve the existing date-only add flow and drag layer. Local preview only until user approval. No task model/API changes.

## Decisions

- Keep date-only AddOnDayDialog intact. Add a separate compact AddOnGridDialog owned by CalendarView, pass an onCreate(date, startMinutes) callback through CalendarGrid to day headers/columns.
- Track only primary gestures beginning on actual column background. Cancel eligibility on pointer movement, cancellation or ancestor scrolling; require the click to belong to that same completed gesture. Existing drag capture continues swallowing post-drag clicks. Use existing slot math and DOM bounding rect so scrolled coordinates remain correct.
- Use existing Dialog, Field/Input, Button and duration parser, with a synchronous in-flight ref to block repeated submissions. Literal task names do not reinterpret dates from natural-language input. Keep errors and inputs on failure. Save date/time as the existing floating due convention and estimate_minutes as the existing validated integer.
- Add one icon button to the existing day-header row without adding a chrome row. The header + now opens a date-only draft (start=null), leaving time optional; only an explicitly entered time is included in due. Grid click/drag keep their numeric start and required time. Use theme tokens, no extra visible task properties, sidebar destinations or scrollers; standard button/Enter/Escape interactions introduce no global shortcut.
- Install portable pinned Go under the workspace, use current compatible Node, separate ignored preview data and npm/Vite hot reload. Start API on 127.0.0.1:8080 and Vite localhost:5173, refuse occupied ports, record child PIDs and provide a stop helper that verifies process ownership before stopping. Launch background helpers hidden on Windows.
- No new production dependencies or image assets; bundle impact is a small lazy/calendar UI addition, runtime memory remains unchanged except the temporary form. No schema migration or backend change.

## Risks / Trade-offs

The approved follow-up retains the compact creation form: a standard nested Menu selects P1–P4 with the existing priority palette on its flag trigger, and a standard Textarea captures the optional description as multiline text. These are form-local drafts, passed as existing priority/description inputs in the same createTask call. No rich-text editor or task row is created before submit; native textarea Enter inserts a line break and the overlay stack handles menu-first Escape. No additional dependencies or API/schema changes.

- Accidental creation after a scroll/drag → test the entire pointer sequence, scroll and cancel handling, plus existing drag regressions.
- Form closes during asynchronous save → ignore dismissal while saving; leave errors visible.
- Local and production data confused → use a separate localhost origin, synthetic owner/data and explicit preview instructions. Do not import production accounts/data or contact VPS.

## Migration Plan

Overlap marker visibility is an additive device-only GridPrefs boolean, `showOverlapMarkers`, defaulting to true unless explicitly false. The standard settings switch uses the existing live preference path. Only the yellow TaskBlock marker is conditional: overlap detection, layout, accessible descriptions and overflow controls are preserved. No task/API/schema changes.

Calendar color source is an additive device-only GridPrefs field, `colorBy: project|priority`, normalized to project for old/invalid metadata. A single calendar-only taskColor helper maps priority to existing red/orange/blue/slate hues or delegates list colors to hueFor; all Day/Week/Month/Plan task renderers use it. Plan projections stay dimmed/read-only and keep their neutral border in default list mode, gaining the priority border in priority mode. Settings use the existing select/copy catalog and existing meta save/live-query path. External events and regular task lists are unchanged. No API/task-schema/dependency change; only settings copy and rendering grow the bundle slightly.

Resizable header follow-up: wrap the shared Day/Week header in a local preference component (`opentodo.calendar.unscheduledHeight`), initial 144 px, hard limits 80–480 px and effective maximum `max(80, min(480, scroller.clientHeight - 160))`. ResizeObserver updates only the effective constraint; pointer drag drafts persist at release and revert on Escape/cancel/blur, while keyboard arrows adjust 16 px and Home/End select limits. Fixed day heading rows sit above separate flex/overflow-y-auto/overscroll-contain regions for all-day events and the full-height lane drop targets. These per-day scroll regions are explicitly requested by the owner, superseding the earlier no-extra-scrollers budget for this area. Keep the sticky opaque header at z-20 and isolate the entire time-grid row at z-0, containing its now-line/dot and previews below the header. No backend or task schema changes and no new dependencies.

Interval selection extends the existing background gesture hook rather than the task drag layer: pending mouse motion lifts at 4 px, touch/pen at 350 ms (pre-hold movement over 8 px cancels). Store the initial day/start and derive the moving endpoint from the original column rect after each pointer/scroll event, flooring to quarter hours with a 24:00 upper endpoint. Render a separate token-based noninteractive selection block with a visible interval/duration label. Active selection uses the same 48 px edge zone and 12 px scroll step as task dragging. The existing shortcut capture frame cancels it on Escape; pointercancel/blur discard it, and capture-phase click suppression prevents release over an existing item from opening that item. The next pointerdown resets suppression. The compact form accepts an optional initial length (default 15) and saves normally. No API/schema/dependency changes.

Create a local feature branch, implement and run targeted calendar tests/typecheck/build. Start local preview with a synthetic owner, exercise browser behavior and offline/reconnect sync. Show the localhost URL and start/stop instructions. PR/full release checks and staging/production wait for user approval of the local result.
