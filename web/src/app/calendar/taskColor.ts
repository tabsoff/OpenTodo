import type { GridPrefs } from '../../lib/calendar'
import { hueFor } from '../../ui'
import type { HueName } from '../../ui/tokens/palette'

const PRIORITY_HUE: Record<number, HueName> = { 1: 'red', 2: 'orange', 3: 'blue', 4: 'slate' }

/** Calendar-only display policy: never changes stored project/task colors. */
export function calendarTaskHue(priority: number, projectColor: string | null | undefined, colorBy: GridPrefs['colorBy']): HueName {
  return colorBy === 'priority' ? PRIORITY_HUE[priority] ?? 'slate' : hueFor(projectColor ?? null)
}
