# Local verification — 2026-10-23

No push, PR, GitHub CI or VPS deployment. Work remains on local branch `calendar-grid-quick-create` for user review.

## Automated checks

- TypeScript app + service worker: `npm run typecheck` passed.
- Targeted Vitest: `calendarCreate`, `calendarView`, `calendar`, `calendarDays`, `duration`: **82 tests passed**. New interaction coverage includes Day/Week, scrolled coordinates, 00:00, 23:45, editable fields, blank/invalid fields, cancel/Escape, save failure/retry, synchronous double-submit protection, primary touch, and movement/scroll/cancel/child/non-primary gesture guards.
- Frontend build passed; existing large-bundle advisory remains. Changed-file ESLint passed.
- OpenSpec strict validation for this change passed.
- All shipped translation catalogs complete (4236 messages); translation extractor/check tests passed. The Windows preview exposed path separator assumptions in extraction; paths now normalize to forward slashes and the shortcut registry is included on Windows as on Unix. A regression test covers portable catalog paths and exclusion of story folders.
- `ui-check` reports two findings in unchanged comments in `ShortcutHelp.tsx:83` and `task-detail/ZoneControl.tsx:26`; none in changed UI files. These unrelated findings are retained for the full pre-release checks.

## Browser and preview checks

- Synthetic owner and separate SQLite data in sibling `../local-preview`. API only 127.0.0.1:8080; Vite only localhost:5173. No production credentials or data.
- Day grid click produced 14:30 / 15 minutes; Enter saved immediately to Inbox. Desktop Week click targeted the intended column/date and 10:45 slot; duration edit saved correctly. Header keyboard activation focused the name and used 06:00 (the default configured start).
- Moved an existing task 10:45 → 11:45, resized 30 → 60 minutes and opened its task panel by double-click: no capture dialog appeared.
- Stopped only the preview API while keeping the loaded UI available. Created a task with no connection to the sync server. After API restart and sync, an independent authenticated REST session found exactly one task with the same ID, date/time and estimate. Reload, repeated sync and a second complete preview restart retained exactly three demo tasks, with no duplicate of the offline task. This browser check simulates loss of the server connection; it does not disconnect the whole computer from the Internet.
- Temporary marker added to the open dialog appeared through Vite hot reload without page reload/server restart, then was removed.
- Start is idempotent; stop preserves data. An unrelated listener deliberately occupied port8080: start refused without stopping it. Cold API build through the start script also passed. Stop verifies executable path and start time, avoiding unrelated reused PIDs.

## Follow-up: priority and description

- The compact form now includes a standard P1–P4 flag menu (default P4) and an optional standard multiline Textarea. Both values are submitted once with the task; no API/schema/dependency changes.
- Typecheck and frontend build passed, as did changed-file ESLint, strict OpenSpec validation and catalog completeness. Targeted calendar tests now total **87 passed**. Added coverage checks all four priorities, empty defaults, exact multiline/whitespace preservation, drafts retained on error and retry, disabled controls during save, keyboard menu navigation and menu-first Escape.
- Browser verified Enter inserts a description newline without creating, title Enter submits, and Escape closes only the priority menu while preserving all draft fields. Checked the form on both narrow and desktop widths; temporary desktop viewport override was reset afterward.
- With only the isolated local API stopped, created a demo task with P2 and a two-line description. It appeared locally. After API restart and sync, its regular task panel showed P2, 15 minutes and both description lines. An independent authenticated API session found exactly one task with its original ID and the exact multiline description. Existing preview tasks were preserved.
- Main entry bundle increased from 1,113.80 kB / 324.73 kB gzip to 1,114.67 kB / 324.95 kB gzip for this follow-up (approximately 0.87 kB / 0.22 kB gzip); the existing large-chunk advisory remains.
- Updated user documentation and left an unsaved example in the running localhost preview for review. Nothing pushed or deployed.

## Follow-up: interval selection

- Mouse drag and touch/pen hold now select a quarter-hour interval in the original day, in either direction, with minimum 15 minutes and an endpoint up to 24:00. A translucent preview labels start/end/duration. Release opens the existing form with the selected length; ordinary click and header button retain 15 minutes.
- Typecheck, changed-file ESLint, frontend build, strict OpenSpec validation and catalog completeness passed. Targeted calendar tests total **102 passed** across six files, covering interval boundaries, reverse selection, preview without premature writes, release over a child/sibling day, edge scroll geometry, 350 ms touch hold, pre-hold touch scrolling, Escape/blur/pointercancel, post-cancel clicks and existing creation/priority/description behavior.
- Browser Day selection 12:00→13:30 populated 90m. Desktop Week reverse selection 14:00→13:00 populated 13:00/60m on the intended date. Existing task move, resize and double-click still worked without opening the creation form.
- Created a 12:00/90m demo interval while the isolated local API was stopped. After reconnect, an independent authenticated REST session found exactly one task with its original ID and the expected start/estimate. Existing local preview data was retained. This simulates server disconnection, not disconnection of the whole computer.
- Touch/pen gestures and preview timing were tested through DOM pointer/touch events, not a physical phone. Physical-device touch validation remains useful during user review.
- Main entry bundle is 1,116.69 kB / 325.56 kB gzip (about +2.02 kB / +0.61 kB gzip from the priority/description follow-up); existing large-chunk advisory remains. No push, PR or VPS deployment.

## Follow-up: resizable unscheduled header

- Added a shared Day/Week height preference, default 144 px, bounds 80–480 px and viewport-aware effective limit leaving 160 px for the grid when possible. Header controls stay fixed; all-day events and tasks scroll independently per day with contained overscroll. Time-grid isolation puts all its blocks/previews and current-time line/dot below the opaque header.
- **113 targeted tests passed** across seven calendar files. Typecheck, changed-file ESLint, frontend build, strict OpenSpec validation and complete catalogs (4237 messages) passed. New tests cover mouse/touch resize, release-only persistence, keyboard values, cancellation, corrupt/unavailable storage, viewport shrink/grow without losing preference, shared Day/Week height and independent scrollport structure. Physical-device touch is still a user-review check; pointer/touch behavior was exercised with DOM events.
- Desktop browser: Friday's overflow scrolled to 223 px while all other days remained at zero and grid scroll remained 280 px. Mouse divider drag changed height 144→224 px; keyboard adjustment and reload preserved 224 px. Scrolling the time grid placed its current-time line at y=199 inside the header's y=84–308 range; it stayed visually covered by the header.
- Created a separate date-only demo task through +, moved it to 12:00, resized 15→30 minutes and moved it back to the upper lane; its regular task panel opened correctly. A fresh grid drag after the layout change still populated 12:45/30m. Existing user test data was retained. No PR, CI, push or VPS publication.

## Earlier fix: header + creates an unscheduled task

The header + now passes an explicit date-only draft (`start=null`), showing an empty optional time field and omitting `due.time` unless entered by the user. Grid click/drag continue to supply a numeric time and require it. Targeted calendar tests total **104 passed**, covering date-only creation in both Day/Week despite a configured 09:00 start, Unscheduled-lane placement with no timed block, and explicit time entry. Typecheck, changed-file ESLint, local build and strict OpenSpec validation passed. Browser verified the Monday header + had an empty time and saved the demo task in its Unscheduled lane with zero timed blocks. No publication.

The local preview is ready for the user. Full mandatory release checks, PR and staging follow approval of the local behavior. Production requires a separate owner decision.

## Follow-up: calendar color source

- Added Task colors (By list / By priority) in General > Calendar, stored in device-only grid preferences with missing/unknown values normalized to project. All calendar task renderers share one helper, including Day/Week lanes/blocks, phone Week, Month, Plan/phone Plan and future projections. Priority hues use red/orange/blue/slate. External-event and non-calendar list colors are unchanged; default list mode retains existing accents, including neutral projected rows.
- Typecheck, changed-file ESLint, frontend build, catalog completeness (4241 messages), settings-copy checks and strict OpenSpec validation passed. **168 targeted tests passed** across 12 files, including every view variant, all priorities and Inbox, old/invalid settings, live setting/priority/project changes, persisted selection and recurring projections. The broader Plan test suite assumes UTC; reran it with process-local TZ=UTC after its pre-existing Tokyo-time assertion differed on this computer's Moscow timezone. No OS timezone change.
- Browser verified the settings select initially used By list, switching to By priority updated actual task border colors, and returning to settings after navigation restored By priority. Light mode rendered red/orange/grey priority borders with light-theme tokens, and dark/system mode used its corresponding palette. Restored the original System appearance choice after theme checks. The synthetic preview's calendar color setting is left at By priority for user review. No production accounts/data, PR, push, CI or VPS deployment.
## Follow-up: optional overlap markers

- Added the device-local Overlap markers switch, default on for missing/invalid old settings. Turning it off hides only the yellow Day/Week task icon, retaining overlap detection, layout, accessible descriptions and stack controls.
- Typecheck, changed-file ESLint, frontend build and complete catalogs (4243 messages) passed. 63 tests across five calendar/settings files passed with process-local TZ=UTC; new cases cover normalization and live hide/restore, persisted state and unchanged overlap layout in Day and Week. No task data or backend changes and no publication.
- Browser confirmed Overlap markers remains off after reloading General settings. Saved screenshot outputs/OpenTodo-overlap-setting.png in the workspace. The switch has one accessible name; its final adjustment was rechecked with all 16 calendar color/marker tests, typecheck and build. Strict OpenSpec validation and whitespace checks passed.

## PR preparation after local approval

- Owner approved the local result. Updated proposal/changelog to cover the complete calendar change and regenerated embedded help after shortening guides to the repository word limit. Corrected a priority-label localization lint issue and CRLF comment handling in the UI checker.
- Final calendar regression run: 94 tests across six files passed (TZ=UTC). Full frontend lint, documentation check (Node 22 experimental type stripping), catalog completeness, strict OpenSpec and whitespace checks passed. Translation script tests: 19 passed.
- Full Windows frontend run: 336 files passed, 25 failed; 3654 tests passed, 50 failed. Failures include Windows path-based checks and Russian Intl date output where fixtures expect English. Repository script tests on Windows: 56 passed, 9 failed on CRLF-sensitive workflow/compose assertions after adding Git shell to process PATH. Do not treat these runs as a green release gate; the PR must pass the complete Linux GitHub CI before merge. No production deployment.
