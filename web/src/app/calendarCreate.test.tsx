// @vitest-environment happy-dom
import 'fake-indexeddb/auto'
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { db, setMeta } from '../lib/db'
import { GRID_PREFS_META_KEY } from '../lib/calendar'
import * as ops from '../lib/ops'
import { click, key, render, type, waitFor } from '../ui/test-utils'
import { CalendarView } from './CalendarView'
import { AddOnGridDialog } from './calendar/AddOnGridDialog'
import { useGridCreate } from './calendar/useGridCreate'
import { UNSCHEDULED_HEIGHT_KEY } from './calendar/UnscheduledHeader'
import { resetPanel } from './panel'

const originalMedia = window.matchMedia
beforeEach(async () => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 14, 12))
  await db.delete()
  await db.open()
  ops.resetDeviceId()
  resetPanel()
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 404 })))
  window.matchMedia = ((q: string) => ({ matches: true, media: q, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false,
  })) as typeof window.matchMedia
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
  window.matchMedia = originalMedia
  resetPanel()
  document.body.innerHTML = ''
})

async function pointer(target: EventTarget, kind: string, init: PointerEventInit = {}) {
  await act(async () => { target.dispatchEvent(new PointerEvent(kind, {
    bubbles: true, pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, clientX: 100, clientY: 500, ...init,
  })) })
}
async function tap(target: Element, y: number) {
  await pointer(target, 'pointerdown', { clientY: y })
  await pointer(target, 'pointerup', { clientY: y })
}
const dialog = () => document.querySelector<HTMLElement>('[data-testid="calendar-create"]')!
const input = (kind: string) => dialog().querySelector<HTMLInputElement>(kind)!
async function submit() {
  await act(async () => { dialog().querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) })
}
async function describeTask(text: string) {
  const textarea = dialog().querySelector('textarea')!
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, text)
    textarea.dispatchEvent(new Event('input', { bubbles: true }))
  })
}
async function choosePriority(p: number) {
  await click(dialog().querySelector('[data-grid-priority]')!)
  await waitFor(() => document.querySelectorAll('[role="menuitemcheckbox"]').length === 4)
  await click([...document.querySelectorAll('[role="menuitemcheckbox"]')].find((e) => e.textContent === `P${p}`)!)
}

describe('calendar grid capture', () => {
  it('shares header height across Day/Week with independent scroll regions above the time-grid layer', async () => {
    localStorage.setItem(UNSCHEDULED_HEIGHT_KEY, '224')
    const id = await ops.createTask({ title: 'Unscheduled task', due: { date: '2026-10-14' } })
    const r = await render(<CalendarView mode="week" />)
    await waitFor(() => !!r.container.querySelector(`[data-lane-task="${id}"]`))
    expect(r.container.querySelector<HTMLElement>('[data-unscheduled-header]')!.style.height).toBe('224px')
    expect(r.container.querySelectorAll('[data-unscheduled-scroll]')).toHaveLength(7)
    const sc = r.container.querySelector('[data-unscheduled-scroll="2026-10-14"]')!
    expect(sc.querySelector(`[data-lane-task="${id}"]`)).toBeTruthy()
    expect(sc.querySelector('[data-grid-create]')).toBeNull()
    expect(r.container.querySelector('[data-time-grid] [data-now-line]')).toBeTruthy()
    expect(r.container.querySelector('[data-time-grid]')!.className).toContain('isolate')
    await r.rerender(<CalendarView mode="day" />)
    expect(r.container.querySelector<HTMLElement>('[data-unscheduled-header]')!.style.height).toBe('224px')
    expect(r.container.querySelectorAll('[data-unscheduled-scroll]')).toHaveLength(1)
    await r.unmount()
  })
  it.each(['day', 'week'] as const)('passes a dragged interval to the editable form in %s', async (mode) => {
    const r = await render(<CalendarView mode={mode} />)
    await waitFor(() => !!r.container.querySelector('[data-drop-day="2026-10-14"]'))
    const col = r.container.querySelector<HTMLElement>('[data-drop-day="2026-10-14"]')!
    vi.spyOn(col, 'getBoundingClientRect').mockReturnValue({ top: -200 } as DOMRect)
    const sc = r.container.querySelector<HTMLElement>('[data-calendar-scroller]')!
    vi.spyOn(sc, 'getBoundingClientRect').mockReturnValue({ top: 0, bottom: 1000 } as DOMRect)
    await pointer(col, 'pointerdown', { clientY: 280 })
    await pointer(window, 'pointermove', { clientY: 328 })
    expect(col.querySelector('[data-create-preview]')?.textContent).toContain('1h')
    expect(dialog()).toBeNull()
    expect(await db.tasks.count()).toBe(0)
    const release = mode === 'week' ? r.container.querySelector('[data-drop-day="2026-10-15"]')! : window
    await pointer(release, 'pointerup', { clientY: 328 })
    expect(input('input[type="time"]').value).toBe('10:00')
    const fields = dialog().querySelectorAll<HTMLInputElement>('input')
    expect(fields[2].value).toBe('60m')
    await type(fields[0], 'Dragged task')
    await type(fields[2], '90m')
    await describeTask('Draft description\nSecond line')
    await choosePriority(1)
    await submit()
    await waitFor(() => !dialog())
    expect(await db.tasks.toArray()).toMatchObject([{ title: 'Dragged task',
      due: { date: '2026-10-14', time: '10:00' }, estimate_minutes: 90, priority: 1,
      description: 'Draft description\nSecond line' }])
    await r.unmount()
  })
  it.each(['day', 'week'] as const)('creates a 15 minute Inbox task in %s at the clicked date and scrolled time', async (mode) => {
    const r = await render(<CalendarView mode={mode} />)
    const date = mode === 'day' ? '2026-10-14' : '2026-10-15'
    await waitFor(() => !!r.container.querySelector(`[data-drop-day="${date}"]`))
    const col = r.container.querySelector<HTMLElement>(`[data-drop-day="${date}"]`)!
    // The viewport is scrolled: 14:38 is 702.4 pixels into this column.
    vi.spyOn(col, 'getBoundingClientRect').mockReturnValue({ top: -400 } as DOMRect)
    await tap(col, 302.4)
    expect(input('input[type="time"]').value).toBe('14:30')
    const fields = dialog().querySelectorAll<HTMLInputElement>('input')
    expect(fields[2].value).toBe('15m')
    expect(document.activeElement).toBe(fields[0])
    await type(fields[0], '  Literal tomorrow 10:00  ')
    await submit()
    await waitFor(() => !dialog())
    const tasks = await db.tasks.toArray()
    expect(tasks).toHaveLength(1)
    expect(tasks[0]).toMatchObject({ title: 'Literal tomorrow 10:00', due: { date, time: '14:30' }, estimate_minutes: 15, project_id: null, priority: 4, description: '' })
    await waitFor(() => !!r.container.querySelector(`[data-block="${tasks[0].id}"]`))
    expect(await db.outbox.count()).toBeGreaterThan(0)
    await r.unmount()
  })

  it('clamps the final interval to 23:45, accepts edited fields, and cancels without writing', async () => {
    const r = await render(<CalendarView mode="day" />)
    await waitFor(() => !!r.container.querySelector('[data-drop-day]'))
    const col = r.container.querySelector<HTMLElement>('[data-drop-day]')!
    vi.spyOn(col, 'getBoundingClientRect').mockReturnValue({ top: 0 } as DOMRect)
    await tap(col, 1151)
    expect(input('input[type="time"]').value).toBe('23:45')
    await type(input('input'), 'Discard me')
    await key(document.activeElement!, 'Escape')
    expect(dialog()).toBeNull()
    expect(await db.tasks.count()).toBe(0)
    await tap(col, 1151)
    await click([...dialog().querySelectorAll('button')].find((b) => b.textContent === 'Cancel')!)
    expect(dialog()).toBeNull()
    await tap(col, 1151)
    const fields = dialog().querySelectorAll<HTMLInputElement>('input')
    await type(fields[0], 'Edited capture')
    await type(fields[1], '20:10')
    await type(fields[2], '1h30')
    await submit()
    await waitFor(() => !dialog())
    expect((await db.tasks.toArray())[0]).toMatchObject({ due: { date: '2026-10-14', time: '20:10' }, estimate_minutes: 90 })
    await r.unmount()
  })

  it.each(['day', 'week'] as const)('creates an unscheduled date-only task from the accessible header in %s', async (mode) => {
    await setMeta(GRID_PREFS_META_KEY, { startHour: 9, endHour: 18, dayLength: 480 })
    const r = await render(<CalendarView mode={mode} />)
    const date = mode === 'week' ? '2026-10-16' : '2026-10-14'
    await waitFor(() => r.container.querySelectorAll('[data-grid-create]').length === (mode === 'week' ? 7 : 1))
    await waitFor(() => r.container.querySelector<HTMLElement>('[data-drop-day] > div')?.style.height === '432px')
    const button = r.container.querySelector<HTMLButtonElement>(`[data-grid-create="${date}"]`)!
    expect(button.getAttribute('aria-label')).toContain(date)
    expect(button.disabled).toBe(false)
    await click(button)
    expect(input('input[type="time"]').value).toBe('')
    expect(input('input[type="time"]').required).toBe(false)
    await type(input('input'), 'Date only')
    await submit()
    await waitFor(() => !dialog())
    const task = (await db.tasks.toArray())[0]
    expect(task.due).toEqual({ date })
    expect(task.estimate_minutes).toBe(15)
    await waitFor(() => !!r.container.querySelector(`[data-drop-lane="${date}"] [data-lane-task="${task.id}"]`))
    expect(r.container.querySelector(`[data-block="${task.id}"]`)).toBeNull()
    await r.unmount()
  })

  it('lets the user explicitly schedule a task opened without time', async () => {
    const close = vi.fn()
    const r = await render(<AddOnGridDialog date="2026-10-14" start={null} onClose={close} />)
    await type(input('input'), 'Explicit time')
    await type(input('input[type="time"]'), '09:45')
    await submit()
    await waitFor(() => close.mock.calls.length === 1)
    expect((await db.tasks.toArray())[0].due).toEqual({ date: '2026-10-14', time: '09:45' })
    await r.unmount()
  })
})

describe('safe submission', () => {
  it('rejects blank titles and invalid duration, retaining all fields on a save failure', async () => {
    const create = vi.spyOn(ops, 'createTask').mockRejectedValue(new Error('Disk unavailable'))
    const close = vi.fn()
    const r = await render(<AddOnGridDialog date="2026-10-14" start={600} onClose={close} />)
    await submit()
    expect(create).not.toHaveBeenCalled()
    const fields = dialog().querySelectorAll<HTMLInputElement>('input')
    await type(fields[0], 'Keep this title')
    await describeTask('First line\nSecond line')
    await choosePriority(2)
    await type(fields[2], '0')
    await submit()
    expect(create).not.toHaveBeenCalled()
    expect(dialog().textContent).toContain('Use minutes or hours')
    await type(fields[2], '45m')
    await type(fields[1], '')
    await submit()
    expect(create).not.toHaveBeenCalled()
    expect(dialog().textContent).toContain('Enter a valid time.')
    await type(fields[1], '10:00')
    await submit()
    expect(dialog().textContent).toContain('Disk unavailable')
    expect(fields[0].value).toBe('Keep this title')
    expect(fields[1].value).toBe('10:00')
    expect(fields[2].value).toBe('45m')
    expect(dialog().querySelector('textarea')!.value).toBe('First line\nSecond line')
    expect(dialog().querySelector('[data-grid-priority]')?.getAttribute('data-grid-priority')).toBe('2')
    expect(close).not.toHaveBeenCalled()
    create.mockResolvedValueOnce('saved-id')
    await submit()
    expect(close).toHaveBeenCalledOnce()
    expect(create).toHaveBeenLastCalledWith(expect.objectContaining({ priority: 2, description: 'First line\nSecond line' }))
    await r.unmount()
  })

  it('allows only one in-flight save even for repeated form submissions', async () => {
    let resolve!: (id: string) => void
    const create = vi.spyOn(ops, 'createTask').mockImplementation(() => new Promise<string>((done) => { resolve = done }))
    const close = vi.fn()
    const r = await render(<AddOnGridDialog date="2026-10-14" start={600} onClose={close} />)
    await type(input('input'), 'Only once')
    await submit()
    await submit()
    await key(document.activeElement!, 'Escape')
    expect(create).toHaveBeenCalledOnce()
    expect(close).not.toHaveBeenCalled()
    expect(input('input').disabled).toBe(true)
    expect(dialog().querySelector('textarea')!.disabled).toBe(true)
    expect(dialog().querySelector<HTMLButtonElement>('[data-grid-priority]')!.disabled).toBe(true)
    await act(async () => { resolve('id') })
    expect(close).toHaveBeenCalledOnce()
    await r.unmount()
  })
})

describe('priority and description capture', () => {
  it.each([1, 2, 3, 4])('saves P%i and a multiline description in the created task', async (p) => {
    const close = vi.fn()
    const r = await render(<AddOnGridDialog date="2026-10-14" start={600} onClose={close} />)
    expect(dialog().querySelector('[data-grid-priority]')?.getAttribute('aria-label')).toBe('Priority: P4')
    await type(input('input'), 'Plan the weekend')
    await describeTask('  Bring a notebook\nCheck the weather  ')
    await choosePriority(p)
    expect(document.querySelector('[role="menu"]')).toBeNull()
    expect(dialog().querySelector('[data-grid-priority]')?.getAttribute('aria-label')).toBe(`Priority: P${p}`)
    await submit()
    await waitFor(() => close.mock.calls.length === 1)
    expect(close).toHaveBeenCalledOnce()
    expect(await db.tasks.toArray()).toMatchObject([{ title: 'Plan the weekend', priority: p,
      description: '  Bring a notebook\nCheck the weather  ', due: { date: '2026-10-14', time: '10:00' }, estimate_minutes: 15 }])
    await r.unmount()
  })

  it('navigates priorities with arrows and dismisses the menu before the draft', async () => {
    const close = vi.fn()
    const r = await render(<AddOnGridDialog date="2026-10-14" start={600} onClose={close} />)
    await click(dialog().querySelector('[data-grid-priority]')!)
    await waitFor(() => document.querySelectorAll('[role="menuitemcheckbox"]').length === 4)
    const options = [...document.querySelectorAll<HTMLButtonElement>('[role="menuitemcheckbox"]')]
    await waitFor(() => document.activeElement === options[0])
    await key(document.activeElement!, 'ArrowDown')
    expect(document.activeElement).toBe(options[1])
    await key(document.activeElement!, 'Escape')
    expect(document.querySelector('[role="menu"]')).toBeNull()
    expect(close).not.toHaveBeenCalled()
    await waitFor(() => document.activeElement === dialog().querySelector('[data-grid-priority]'))
    await key(document.activeElement!, 'Escape')
    expect(close).toHaveBeenCalledOnce()
    expect(await db.tasks.count()).toBe(0)
    await r.unmount()
  })
})

describe('background gesture isolation', () => {
  function Grid({ create }: { create: (start: number) => void }) {
    const { onPointerDown: down } = useGridCreate(create)
    return <div data-grid onPointerDown={down}><button>Task, event or overflow</button></div>
  }
  it('captures midnight and a primary touch tap using the same slot math', async () => {
    const create = vi.fn()
    const r = await render(<Grid create={create} />)
    const col = r.container.querySelector('[data-grid]')!
    vi.spyOn(col, 'getBoundingClientRect').mockReturnValue({ top: 200 } as DOMRect)
    await pointer(col, 'pointerdown', { pointerType: 'touch', clientY: 201 })
    await pointer(col, 'pointerup', { pointerType: 'touch', clientY: 201 })
    expect(create).toHaveBeenCalledExactlyOnceWith(0, 15)
    await r.unmount()
  })
  it.each(['scroll', 'cancel', 'blur', 'child', 'right', 'secondary'])("does not capture after %s", async (gesture) => {
    const create = vi.fn()
    const r = await render(<Grid create={create} />)
    const col = r.container.querySelector('[data-grid]')!
    const child = col.querySelector('button')!
    await pointer(gesture === 'child' ? child : col, 'pointerdown', {
      button: gesture === 'right' ? 2 : 0, isPrimary: gesture !== 'secondary',
    })
    if (gesture === 'move') await pointer(window, 'pointermove', { clientY: 520 })
    if (gesture === 'cancel') await pointer(window, 'pointercancel')
    if (gesture === 'scroll' || gesture === 'blur') await act(async () => { window.dispatchEvent(new Event(gesture)) })
    await pointer(col, 'pointerup')
    expect(create).not.toHaveBeenCalled()
    await r.unmount()
  })
})
