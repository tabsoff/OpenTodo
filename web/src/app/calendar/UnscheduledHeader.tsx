import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { clamp } from '../../lib/calendar'
import { t } from '../../lib/i18n'
import { registerShortcutScope } from '../shortcuts/dispatch'

export const UNSCHEDULED_HEIGHT_KEY = 'opentodo.calendar.unscheduledHeight'
const MIN = 80
const MAX = 480
function readHeight() {
  try {
    const raw = localStorage.getItem(UNSCHEDULED_HEIGHT_KEY)
    const value = raw === null ? 144 : Number(raw)
    return Number.isFinite(value) ? clamp(value, MIN, MAX) : 144
  } catch { return 144 }
}
function saveHeight(value: number) {
  try { localStorage.setItem(UNSCHEDULED_HEIGHT_KEY, String(value)) } catch { /* Device preference; resizing still works. */ }
}

/** One shared header height; individual day contents scroll below their fixed heading. */
export function UnscheduledHeader({ children }: { children: ReactNode }) {
  const header = useRef<HTMLDivElement>(null)
  const [preferred, setPreferred] = useState(readHeight)
  const [maximum, setMaximum] = useState(MAX)
  const [draft, setDraft] = useState<number | null>(null)
  const drag = useRef<{ id: number; y: number; height: number; value: number } | null>(null)
  const limit = useRef(maximum)
  limit.current = maximum
  const height = clamp(draft ?? preferred, MIN, maximum)

  useLayoutEffect(() => {
    const scroller = header.current?.closest<HTMLElement>('[data-calendar-scroller]')
    if (!scroller) return
    const measure = () => setMaximum(scroller.clientHeight > 0 ? Math.max(MIN, Math.min(MAX, scroller.clientHeight - 160)) : MAX)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(scroller)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const cancel = () => { drag.current = null; setDraft(null) }
    const move = (e: PointerEvent) => {
      const p = drag.current
      if (!p || p.id !== e.pointerId) return
      e.preventDefault()
      p.value = clamp(Math.round(p.height + e.clientY - p.y), MIN, limit.current)
      setDraft(p.value)
    }
    const up = (e: PointerEvent) => {
      const p = drag.current
      if (!p || p.id !== e.pointerId) return
      if (p.value !== p.height) { setPreferred(p.value); saveHeight(p.value) }
      cancel()
    }
    const unregister = registerShortcutScope({ scope: 'calendar', capture: true, handlers: {
      'calendar.escape': () => { if (!drag.current) return false; cancel() },
    } })
    window.addEventListener('pointermove', move, { passive: false })
    window.addEventListener('pointerup', up)
    window.addEventListener('pointercancel', cancel)
    window.addEventListener('blur', cancel)
    return () => {
      unregister()
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
      window.removeEventListener('pointercancel', cancel)
      window.removeEventListener('blur', cancel)
    }
  }, [])

  return (
    <div ref={header} data-unscheduled-header className="sticky top-0 z-20 flex flex-col bg-surface" style={{ height }}>
      <div className="flex min-h-0 flex-1">{children}</div>
      <div role="separator" aria-label={t('Resize unscheduled area')} aria-orientation="horizontal" tabIndex={0}
        aria-valuemin={MIN} aria-valuemax={maximum} aria-valuenow={height}
        className="relative z-10 flex h-2 shrink-0 cursor-row-resize touch-none items-center justify-center border-y border-default bg-surface hover:bg-sunken focus-visible:outline-2 focus-visible:outline-focus"
        onPointerDown={(e) => {
          if (e.button !== 0 || !e.isPrimary) return
          e.preventDefault(); e.stopPropagation(); e.currentTarget.focus()
          e.currentTarget.setPointerCapture?.(e.pointerId)
          drag.current = { id: e.pointerId, y: e.clientY, height, value: height }
        }}
        onKeyDown={(e) => {
          if (drag.current) return
          const next = e.key === 'ArrowUp' ? height - 16 : e.key === 'ArrowDown' ? height + 16
            : e.key === 'Home' ? MIN : e.key === 'End' ? maximum : null
          if (next === null) return
          e.preventDefault(); e.stopPropagation()
          const value = clamp(next, MIN, maximum)
          setPreferred(value); saveHeight(value)
        }}>
        <span aria-hidden className="h-0.5 w-10 rounded-full bg-(--ot-border)" />
      </div>
    </div>
  )
}
