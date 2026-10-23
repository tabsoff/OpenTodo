import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { clamp, DAY_MINUTES, SLOT_MINUTES, slotFromOffset } from '../../lib/calendar'
import { registerShortcutScope } from '../shortcuts/dispatch'
import { PX_PER_MIN } from './grid'

export interface GridInterval { start: number; length: number }
interface Gesture {
  id: number; x: number; y: number; lastY: number; start: number
  mouse: boolean; lifted: boolean; column: HTMLElement
  timer?: ReturnType<typeof setTimeout>
}

/** The anchor is a start slot; the moving boundary may reach midnight at the day's end. */
export function gridInterval(anchor: number, offset: number): GridInterval {
  const end = clamp(Math.floor(offset / PX_PER_MIN / SLOT_MINUTES) * SLOT_MINUTES, 0, DAY_MINUTES)
  const start = Math.min(anchor, end)
  return { start, length: Math.max(SLOT_MINUTES, Math.abs(end - anchor)) }
}

/** Only gestures begun on background create; once lifted, the original day owns the interval. */
export function useGridCreate(onCreate: (start: number, length: number) => void) {
  const pending = useRef<Gesture | null>(null)
  const suppressClick = useRef(false)
  const action = useRef(onCreate)
  const [selection, setSelection] = useState<GridInterval | null>(null)
  action.current = onCreate
  useEffect(() => {
    const cancel = () => {
      const p = pending.current
      if (p?.timer) clearTimeout(p.timer)
      if (p?.lifted) suppressClick.current = true
      pending.current = null
      setSelection(null)
    }
    const interval = (p: Gesture) => gridInterval(p.start, p.lastY - p.column.getBoundingClientRect().top)
    const lift = (p: Gesture) => { p.lifted = true; setSelection(interval(p)) }
    const move = (e: PointerEvent) => {
      const p = pending.current
      if (!p || e.pointerId !== p.id) return
      const distance = Math.hypot(e.clientX - p.x, e.clientY - p.y)
      p.lastY = e.clientY
      if (!p.lifted) {
        if (!p.mouse) { if (distance > 8) cancel(); return }
        if (distance < 4) return
        lift(p)
      }
      e.preventDefault()
      const sc = p.column.closest<HTMLElement>('[data-calendar-scroller]')
      if (sc) {
        const rect = sc.getBoundingClientRect()
        if (e.clientY < rect.top + 48) sc.scrollTop -= 12
        else if (e.clientY > rect.bottom - 48) sc.scrollTop += 12
      }
      setSelection(interval(p))
    }
    const up = (e: PointerEvent) => {
      const p = pending.current
      if (p && e.pointerId !== p.id) return
      if (p) {
        p.lastY = e.clientY
        const validTap = e.target === p.column && Math.hypot(e.clientX - p.x, e.clientY - p.y) < (p.mouse ? 4 : 8)
        const selected = p.lifted ? interval(p) : { start: p.start, length: SLOT_MINUTES }
        const commit = e.button === 0 && (p.lifted || validTap)
        cancel()
        if (commit) action.current(selected.start, selected.length)
      }
      // The browser emits click after pointerup; don't let it activate a task passed over.
      if (suppressClick.current) setTimeout(() => { suppressClick.current = false }, 0)
    }
    const scroll = () => {
      const p = pending.current
      if (p?.lifted) setSelection(interval(p))
      else if (p) cancel()
    }
    const touchMove = (e: TouchEvent) => { if (pending.current?.lifted) e.preventDefault() }
    const click = (e: MouseEvent) => {
      if (!suppressClick.current) return
      e.preventDefault(); e.stopPropagation(); suppressClick.current = false
    }
    const down = () => { cancel(); suppressClick.current = false }
    const unregister = registerShortcutScope({ scope: 'calendar', capture: true, handlers: {
      'calendar.escape': () => { if (!pending.current) return false; cancel() },
    } })
    window.addEventListener('pointerdown', down, true)
    window.addEventListener('pointermove', move, { passive: false })
    window.addEventListener('pointerup', up)
    window.addEventListener('pointercancel', cancel)
    window.addEventListener('scroll', scroll, true)
    window.addEventListener('blur', cancel)
    window.addEventListener('click', click, true)
    document.addEventListener('touchmove', touchMove, { passive: false })
    return () => {
      if (pending.current?.timer) clearTimeout(pending.current.timer)
      unregister()
      window.removeEventListener('pointerdown', down, true)
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
      window.removeEventListener('pointercancel', cancel)
      window.removeEventListener('scroll', scroll, true)
      window.removeEventListener('blur', cancel)
      window.removeEventListener('click', click, true)
      document.removeEventListener('touchmove', touchMove)
    }
  }, [])
  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget || e.button !== 0 || !e.isPrimary || e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return
    const column = e.currentTarget
    const p: Gesture = { id: e.pointerId, x: e.clientX, y: e.clientY, lastY: e.clientY,
      start: slotFromOffset(e.clientY - column.getBoundingClientRect().top, PX_PER_MIN),
      mouse: e.pointerType === 'mouse', lifted: false, column }
    pending.current = p
    if (!p.mouse) p.timer = setTimeout(() => {
      if (pending.current !== p) return
      p.lifted = true
      setSelection(gridInterval(p.start, p.lastY - column.getBoundingClientRect().top))
    }, 350)
  }
  return { onPointerDown, selection }
}
