// @vitest-environment happy-dom
import { act } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { click, key, render } from '../../ui/test-utils'
import { gridInterval, useGridCreate } from './useGridCreate'

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); document.body.innerHTML = '' })

function Grid({ create, childClick = () => {} }: { create: (start: number, length: number) => void; childClick?: () => void }) {
  const { onPointerDown, selection } = useGridCreate(create)
  return <div data-calendar-scroller><div data-grid onPointerDown={onPointerDown}>
    <button onClick={childClick}>Existing task</button>
    {selection && <output>{selection.start}:{selection.length}</output>}
  </div></div>
}
async function pointer(target: EventTarget, type: string, y: number, init: PointerEventInit = {}) {
  await act(async () => { target.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true,
    pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, clientX: 100, clientY: y, ...init })) })
}
async function setup() {
  const create = vi.fn()
  const childClick = vi.fn()
  const r = await render(<Grid create={create} childClick={childClick} />)
  const col = r.container.querySelector<HTMLElement>('[data-grid]')!
  const sc = r.container.querySelector<HTMLElement>('[data-calendar-scroller]')!
  // ScrollTop changes move the original column in viewport coordinates.
  sc.scrollTop = 200
  vi.spyOn(col, 'getBoundingClientRect').mockImplementation(() => ({ top: -sc.scrollTop } as DOMRect))
  vi.spyOn(sc, 'getBoundingClientRect').mockReturnValue({ top: 0, bottom: 1000 } as DOMRect)
  return { ...r, create, childClick, col, sc }
}

describe('interval boundaries', () => {
  it.each([
    [600, 528, 600, 60], [660, 480, 600, 60], [600, 502, 600, 15],
    [1425, 2000, 1425, 15], [600, -200, 0, 600], [0, 1152, 0, 1440],
  ])('anchor %i and offset %i yield %i for %i', (anchor, offset, start, length) => {
    expect(gridInterval(anchor, offset)).toEqual({ start, length })
  })
})

describe('interval gestures', () => {
  it.each([false, true])('previews and releases a mouse interval (reverse=%s) across children', async (reverse) => {
    const r = await setup()
    const from = reverse ? 328 : 280 // scrolled 11:00 / 10:00
    const to = reverse ? 280 : 328
    await pointer(r.col, 'pointerdown', from)
    await pointer(window, 'pointermove', to, { clientX: 900 })
    expect(r.container.querySelector('output')?.textContent).toBe('600:60')
    expect(r.create).not.toHaveBeenCalled()
    const child = r.col.querySelector('button')!
    // Release over an existing task; date belongs to the original column.
    await act(async () => {
      child.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 1, button: 0, clientY: to }))
      child.click()
    })
    expect(r.create).toHaveBeenCalledExactlyOnceWith(600, 60)
    expect(r.childClick).not.toHaveBeenCalled()
    expect(r.container.querySelector('output')).toBeNull()
    await r.unmount()
  })

  it('autoscrolls at the edge and updates the moving boundary using the column rect', async () => {
    const r = await setup()
    vi.spyOn(r.sc, 'getBoundingClientRect').mockReturnValue({ top: 0, bottom: 350 } as DOMRect)
    await pointer(r.col, 'pointerdown', 280)
    await pointer(window, 'pointermove', 340)
    expect(r.sc.scrollTop).toBe(212)
    expect(r.container.querySelector('output')?.textContent).toBe('600:90')
    await pointer(window, 'pointerup', 340)
    expect(r.create).toHaveBeenCalledExactlyOnceWith(600, 90)
    await r.unmount()
  })

  it('lifts touch after 350ms, blocks touch scroll only after lifting, and commits', async () => {
    vi.useFakeTimers()
    const r = await setup()
    await pointer(r.col, 'pointerdown', 280, { pointerType: 'touch' })
    await act(async () => { vi.advanceTimersByTime(349) })
    expect(r.container.querySelector('output')).toBeNull()
    await act(async () => { vi.advanceTimersByTime(1) })
    expect(r.container.querySelector('output')?.textContent).toBe('600:15')
    const swipe = new Event('touchmove', { bubbles: true, cancelable: true })
    document.dispatchEvent(swipe)
    expect(swipe.defaultPrevented).toBe(true)
    await pointer(window, 'pointermove', 328, { pointerType: 'touch' })
    await pointer(window, 'pointerup', 328, { pointerType: 'touch' })
    expect(r.create).toHaveBeenCalledExactlyOnceWith(600, 60)
    await r.unmount()
  })

  it('leaves a quick touch swipe to scrolling and cancels its hold timer', async () => {
    vi.useFakeTimers()
    const r = await setup()
    await pointer(r.col, 'pointerdown', 280, { pointerType: 'touch' })
    await pointer(window, 'pointermove', 289, { pointerType: 'touch' })
    await act(async () => { vi.advanceTimersByTime(400) })
    const swipe = new Event('touchmove', { cancelable: true })
    document.dispatchEvent(swipe)
    expect(swipe.defaultPrevented).toBe(false)
    await pointer(r.col, 'pointerup', 328, { pointerType: 'touch' })
    expect(r.create).not.toHaveBeenCalled()
    expect(r.container.querySelector('output')).toBeNull()
    await r.unmount()
  })

  it.each(['Escape', 'blur', 'pointercancel'])('cancels a lifted interval on %s', async (kind) => {
    const r = await setup()
    await pointer(r.col, 'pointerdown', 280)
    await pointer(window, 'pointermove', 328)
    if (kind === 'Escape') await key(document.body, 'Escape')
    else await act(async () => { window.dispatchEvent(new Event(kind)) })
    await pointer(r.col, 'pointerup', 328)
    expect(r.create).not.toHaveBeenCalled()
    expect(r.container.querySelector('output')).toBeNull()
    // A fresh click following cancellation must still work.
    await pointer(r.col.querySelector('button')!, 'pointerdown', 280)
    await click(r.col.querySelector('button')!)
    expect(r.childClick).toHaveBeenCalledOnce()
    await r.unmount()
  })
})
