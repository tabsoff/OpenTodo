// @vitest-environment happy-dom
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { key, render } from '../../ui/test-utils'
import { UNSCHEDULED_HEIGHT_KEY, UnscheduledHeader } from './UnscheduledHeader'

let resize: () => void
beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: () => void) { resize = callback }
    observe() {} disconnect() {}
  })
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); document.body.innerHTML = '' })
async function setup() {
  const r = await render(<div data-calendar-scroller><UnscheduledHeader><div>Tasks</div></UnscheduledHeader></div>)
  const separator = r.container.querySelector<HTMLElement>('[role="separator"]')!
  // happy-dom has no pointer capture layout; events are dispatched to window as in the browser.
  separator.setPointerCapture = vi.fn()
  return { ...r, separator, header: r.container.querySelector<HTMLElement>('[data-unscheduled-header]')! }
}
async function pointer(target: EventTarget, type: string, y: number, pointerType = 'mouse') {
  await act(async () => { target.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true,
    pointerId: 1, button: 0, isPrimary: true, pointerType, clientY: y })) })
}

describe('unscheduled header preference', () => {
  it('exposes a keyboard separator and remembers bounded values on remount', async () => {
    let r = await setup()
    expect(r.header.style.height).toBe('144px')
    expect(r.separator.getAttribute('aria-label')).toBe('Resize unscheduled area')
    expect(r.separator.getAttribute('aria-orientation')).toBe('horizontal')
    expect(r.separator.tabIndex).toBe(0)
    await key(r.separator, 'ArrowDown')
    expect(r.header.style.height).toBe('160px')
    await key(r.separator, 'ArrowUp')
    expect(r.header.style.height).toBe('144px')
    await key(r.separator, 'Home')
    expect(r.header.style.height).toBe('80px')
    await key(r.separator, 'ArrowUp')
    expect(r.header.style.height).toBe('80px')
    await key(r.separator, 'End')
    expect(r.header.style.height).toBe('480px')
    await key(r.separator, 'ArrowDown')
    expect(r.separator.getAttribute('aria-valuenow')).toBe('480')
    await r.unmount()
    r = await setup()
    expect(r.header.style.height).toBe('480px')
    await r.unmount()
  })

  it('constrains effective height on a small viewport without changing the preference', async () => {
    localStorage.setItem(UNSCHEDULED_HEIGHT_KEY, '400')
    const r = await setup()
    const sc = r.container.querySelector<HTMLElement>('[data-calendar-scroller]')!
    Object.defineProperty(sc, 'clientHeight', { configurable: true, value: 400 })
    await act(async () => resize())
    expect(r.header.style.height).toBe('240px')
    expect(r.separator.getAttribute('aria-valuemax')).toBe('240')
    expect(localStorage.getItem(UNSCHEDULED_HEIGHT_KEY)).toBe('400')
    Object.defineProperty(sc, 'clientHeight', { configurable: true, value: 800 })
    await act(async () => resize())
    expect(r.header.style.height).toBe('400px')
    await r.unmount()
  })

  it.each(['mouse', 'touch'])('resizes with %s, saving only on release', async (kind) => {
    const r = await setup()
    await pointer(r.separator, 'pointerdown', 200, kind)
    await pointer(window, 'pointermove', 280, kind)
    expect(r.header.style.height).toBe('224px')
    expect(localStorage.getItem(UNSCHEDULED_HEIGHT_KEY)).toBeNull()
    await pointer(window, 'pointerup', 280, kind)
    expect(localStorage.getItem(UNSCHEDULED_HEIGHT_KEY)).toBe('224')
    await r.unmount()
  })

  it.each(['Escape', 'pointercancel', 'blur'])('reverts a draft after %s without saving', async (kind) => {
    localStorage.setItem(UNSCHEDULED_HEIGHT_KEY, '160')
    const r = await setup()
    await pointer(r.separator, 'pointerdown', 200)
    await pointer(window, 'pointermove', 400)
    expect(r.header.style.height).toBe('360px')
    if (kind === 'Escape') await key(r.separator, 'Escape')
    else await act(async () => { window.dispatchEvent(new Event(kind)) })
    await pointer(window, 'pointerup', 400)
    expect(r.header.style.height).toBe('160px')
    expect(localStorage.getItem(UNSCHEDULED_HEIGHT_KEY)).toBe('160')
    await r.unmount()
  })

  it('falls back for corrupt settings and still resizes if storage is unavailable', async () => {
    localStorage.setItem(UNSCHEDULED_HEIGHT_KEY, 'broken')
    const r = await setup()
    expect(r.header.style.height).toBe('144px')
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Unavailable') })
    await key(r.separator, 'ArrowDown')
    expect(r.header.style.height).toBe('160px')
    await r.unmount()
  })
})
