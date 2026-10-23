// @vitest-environment happy-dom
import 'fake-indexeddb/auto'
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DEFAULT_GRID_PREFS, GRID_PREFS_META_KEY, normalizeGridPrefs } from '../lib/calendar'
import { db, getMeta, setMeta } from '../lib/db'
import { createProject, createTask, resetDeviceId, updateTask } from '../lib/ops'
import { click, render, waitFor } from '../ui/test-utils'
import { CalendarSettingsSection } from './CalendarSettings'
import { CalendarView } from './CalendarView'
import { MonthView } from './MonthView'
import { PlanView } from './PlanView'
import { calendarTaskHue } from './calendar/taskColor'
import { resetPanel } from './panel'

const originalMedia = window.matchMedia
let wide = true
beforeEach(async () => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 14, 12))
  await db.delete(); await db.open(); resetDeviceId(); resetPanel()
  localStorage.clear()
  history.replaceState(null, '', '/day')
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 404 })))
  wide = true
  window.matchMedia = ((q: string) => ({ matches: wide, media: q, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false,
  })) as typeof window.matchMedia
})
afterEach(() => {
  vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals()
  window.matchMedia = originalMedia; resetPanel(); document.body.innerHTML = ''
})

describe('calendar task color policy', () => {
  it('defaults overlap markers on for old and invalid settings', () => {
    for (const value of [undefined, null, 'false', 0, true]) expect(normalizeGridPrefs({ showOverlapMarkers: value }).showOverlapMarkers).toBe(true)
    expect(normalizeGridPrefs({ showOverlapMarkers: false }).showOverlapMarkers).toBe(false)
  })

  it.each(['day', 'week'] as const)('hides overlap icons live in %s without changing layout, and persists the switch', async (mode) => {
    await createTask({ title: 'First overlapping task', due: { date: '2026-10-14', time: '10:00' }, estimate_minutes: 60 })
    await createTask({ title: 'Second overlapping task', due: { date: '2026-10-14', time: '10:15' }, estimate_minutes: 30 })
    let r = await render(<><CalendarSettingsSection /><CalendarView mode={mode} /></>)
    await waitFor(() => r.container.querySelectorAll('[data-overlap-marker]').length === 2)
    const styles = [...r.container.querySelectorAll('[data-block]')].map(e => e.getAttribute('style'))
    await click(r.container.querySelector('#calendar-overlap-markers')!)
    await waitFor(() => r.container.querySelectorAll('[data-overlap-marker]').length === 0)
    expect(r.container.querySelectorAll('[data-block][data-overlap]')).toHaveLength(2)
    expect([...r.container.querySelectorAll('[data-block]')].map(e => e.getAttribute('style'))).toEqual(styles)
    expect(r.container.querySelector('[data-block]')!.textContent).toContain('overlaps another item')
    await r.unmount()
    r = await render(<><CalendarSettingsSection /><CalendarView mode={mode} /></>)
    await waitFor(() => r.container.querySelectorAll('[data-block]').length === 2)
    expect(r.container.querySelector('#calendar-overlap-markers')?.getAttribute('aria-checked')).toBe('false')
    expect(r.container.querySelector('[data-overlap-marker]')).toBeNull()
    await click(r.container.querySelector('#calendar-overlap-markers')!)
    await waitFor(() => r.container.querySelectorAll('[data-overlap-marker]').length === 2)
    await r.unmount()
  })
  it('keeps list mode for old or unknown settings and normalizes priority mode', () => {
    for (const colorBy of [undefined, 'bad', null, 'project']) expect(normalizeGridPrefs({ colorBy }).colorBy).toBe('project')
    expect(normalizeGridPrefs({ colorBy: 'priority' }).colorBy).toBe('priority')
  })
  it.each([[1, 'red'], [2, 'orange'], [3, 'blue'], [4, 'slate']] as const)('maps P%i to %s without using list color', (p, hue) => {
    expect(calendarTaskHue(p, '#22c55e', 'priority')).toBe(hue)
    expect(calendarTaskHue(p, undefined, 'priority')).toBe(hue)
    expect(calendarTaskHue(p, '#22c55e', 'project')).toBe('green')
  })

  it.each(['day', 'week', 'month', 'plan', 'phone-week', 'phone-plan'] as const)('updates %s live when settings, priority and list change', async (view) => {
    wide = !view.startsWith('phone')
    const project = await createProject({ name: 'Green list', color: '#22c55e' })
    const task = await createTask({ title: 'Colored task', priority: 1, project_id: project,
      due: { date: '2026-10-14', time: '09:00' }, estimate_minutes: 30 })
    const prefix = view === 'month' ? 'data-month-task' : view.includes('plan') ? 'data-plan-task' : view === 'phone-week' ? 'data-agenda-task' : 'data-block'
    const node = () => r.container.querySelector(`[${prefix}="${task}"]`)
    const screen = view === 'month' ? <MonthView /> : view.includes('plan') ? <PlanView /> : <CalendarView mode={view.includes('week') ? 'week' : 'day'} />
    const r = await render(screen)
    await waitFor(() => node()?.getAttribute('data-hue') === 'green')
    await act(async () => { await setMeta(GRID_PREFS_META_KEY, { ...DEFAULT_GRID_PREFS, colorBy: 'priority' }) })
    await waitFor(() => node()?.getAttribute('data-hue') === 'red')
    await act(async () => { await updateTask(task, { priority: 2 }) })
    await waitFor(() => node()?.getAttribute('data-hue') === 'orange')
    await act(async () => { await updateTask(task, { project_id: null }) })
    await waitFor(() => node()?.getAttribute('data-hue') === 'orange')
    await act(async () => { await setMeta(GRID_PREFS_META_KEY, DEFAULT_GRID_PREFS) })
    await waitFor(() => node()?.getAttribute('data-hue') === calendarTaskHue(2, null, 'project'))
    await r.unmount()
  })

  it('persists the settings select and restores its value on remount', async () => {
    let r = await render(<CalendarSettingsSection />)
    const select = r.container.querySelector<HTMLSelectElement>('#calendar-task-colors')!
    expect(select.value).toBe('project')
    await act(async () => { select.value = 'priority'; select.dispatchEvent(new Event('change', { bubbles: true })) })
    await waitFor(async () => (await getMeta<{ colorBy: string }>(GRID_PREFS_META_KEY, { colorBy: '' })).colorBy === 'priority')
    await r.unmount()
    r = await render(<CalendarSettingsSection />)
    await waitFor(() => r.container.querySelector<HTMLSelectElement>('#calendar-task-colors')?.value === 'priority')
    await r.unmount()
  })

  it('colors date-only Inbox tasks and recurring projections, preserving event colors', async () => {
    await setMeta(GRID_PREFS_META_KEY, { ...DEFAULT_GRID_PREFS, colorBy: 'priority' })
    const inbox = await createTask({ title: 'Inbox task', priority: 3, due: { date: '2026-10-14' } })
    await createTask({ title: 'Repeat task', priority: 2, due: { date: '2026-10-14', time: '10:00' }, recurrence: 'every day' })
    await db.calendarSubscriptions.put({ id: 's', name: 'Events', color: '#22c55e', enabled: true, lastSuccessAt: Date.now() })
    await db.calendarEvents.put({ id: 'ev', subscriptionId: 's', uid: 'ev', summary: 'External', location: '',
      start: { date: '2026-10-14', time: '11:00' }, end: { date: '2026-10-14', time: '12:00' }, allDay: false, free: false })
    await setMeta('calendar.events.window', { from: '2026-10-01', to: '2026-11-01', fetchedAt: Date.now() })
    let r = await render(<CalendarView mode="day" />)
    await waitFor(() => r.container.querySelector(`[data-lane-task="${inbox}"]`)?.getAttribute('data-hue') === 'blue')
    await waitFor(() => r.container.querySelector('[data-event="ev"]')?.getAttribute('data-hue') === 'green')
    await r.unmount()
    r = await render(<PlanView />)
    await waitFor(() => !!r.container.querySelector('[data-plan-projected]'))
    expect([...r.container.querySelectorAll('[data-plan-projected]')].every(e => e.getAttribute('data-hue') === 'orange')).toBe(true)
    await r.unmount()
  })
})
