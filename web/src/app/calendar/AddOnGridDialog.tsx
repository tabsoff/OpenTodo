import { useRef, useState, type FormEvent } from 'react'
import { formatTime, parseTime } from '../../lib/calendar'
import { formatShort } from '../../lib/dates'
import { parseDuration } from '../../lib/duration'
import { t } from '../../lib/i18n'
import { createTask } from '../../lib/ops'
import type { Priority } from '../../lib/types'
import { Button, Dialog, Field, Icon, Input, Menu, MenuItem, Textarea } from '../../ui'
import { actionErrorMessage } from '../actionError'

const PRIORITY_COLOR: Record<Priority, string> = {
  1: 'text-(--ot-hue-red-text)', 2: 'text-(--ot-hue-orange-text)',
  3: 'text-(--ot-hue-blue-text)', 4: 'text-muted',
}

/** Capture a literal title at the chosen grid time, without parsing date tokens. */
export function AddOnGridDialog({ date, start, length = 15, onClose }: { date: string; start: number | null; length?: number; onClose: () => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>(4)
  const [time, setTime] = useState(start === null ? '' : formatTime(start))
  const [duration, setDuration] = useState(`${length}m`)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [durationError, setDurationError] = useState<string | null>(null)
  const saving = useRef(false)
  const close = () => { if (!saving.current) onClose() }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (saving.current || !title.trim()) return
    const minutes = parseDuration(duration)
    if (minutes === null) {
      setDurationError(t('Use minutes or hours, for example 20, 45m, 1h30 (up to one week).'))
      return
    }
    if ((time || start !== null) && parseTime(time) === null) {
      setError(t('Enter a valid time.'))
      return
    }
    saving.current = true
    setBusy(true)
    setError(null)
    try {
      await createTask({ title: title.trim(), description, priority, due: time ? { date, time } : { date }, estimate_minutes: minutes })
      onClose()
    } catch (err) {
      setError(actionErrorMessage(err))
    } finally {
      saving.current = false
      setBusy(false)
    }
  }

  return (
    <Dialog title={t('Add a task on {adding}', { adding: formatShort(date) })} onClose={close} size="md" testId="calendar-create">
      <form onSubmit={(e) => { void submit(e) }} className="space-y-4">
        <div className="flex items-end gap-2">
          <Field label={t('Task name')} className="min-w-0 flex-1">
            <Input autoFocus required value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy} />
          </Field>
          <Menu kind="menu" label={[t('Priority'), `P${priority}`].join(': ')} title={t('Priority')}
            trigger={<><Icon name="flag" className={PRIORITY_COLOR[priority]} /><span className="text-meta">P{priority}</span></>}
            triggerClassName="ui-btn ui-btn--ghost ui-btn--sm touch-target mb-0.5"
            triggerProps={{ disabled: busy, 'data-grid-priority': priority.toString() }}>
            {([1, 2, 3, 4] as const).map((p) => (
              <MenuItem key={p} label={`P${p}`} icon="flag" checked={priority === p} disabled={busy} onSelect={() => setPriority(p)} />
            ))}
          </Menu>
        </div>
        <Field label={t('Description')}>
          <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} disabled={busy} />
        </Field>
        <div className="flex flex-wrap gap-4">
          <Field label={t('Time')}>
            <Input type="time" required={start !== null} value={time} onChange={(e) => { setTime(e.target.value); setError(null) }} disabled={busy} />
          </Field>
          <Field label={t('Estimate')} error={durationError}>
            <Input value={duration} onChange={(e) => { setDuration(e.target.value); setDurationError(null) }} disabled={busy} className="w-32" />
          </Field>
        </div>
        {error && <p role="alert" className="text-meta text-danger">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={close} disabled={busy}>{t('Cancel')}</Button>
          <Button type="submit" busy={busy} disabled={!title.trim()}>{t('Add a task')}</Button>
        </div>
      </form>
    </Dialog>
  )
}
