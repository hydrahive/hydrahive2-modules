/** Rückgängig/Wiederholen für die Schnittfassung (Spec „Bauplan 4b“): höchstens 100 Schritte, nur im Browser. */
export const MAX_STEPS = 100

export class History<T> {
  private past: T[] = []
  private future: T[] = []
  private now: T

  constructor(start: T) {
    this.now = start
  }

  get current(): T { return this.now }
  get canUndo(): boolean { return this.past.length > 0 }
  get canRedo(): boolean { return this.future.length > 0 }

  /** Neuer Stand; Wiederholen entfällt. */
  push(next: T): void {
    this.past.push(this.now)
    if (this.past.length > MAX_STEPS) this.past.shift()
    this.now = next
    this.future = []
  }

  undo(): T {
    const prev = this.past.pop()
    if (prev !== undefined) { this.future.push(this.now); this.now = prev }
    return this.now
  }

  redo(): T {
    const next = this.future.pop()
    if (next !== undefined) { this.past.push(this.now); this.now = next }
    return this.now
  }

  /** Von außen geladen (Projektwechsel, Neuladen): ohne Verlauf neu beginnen. */
  reset(state: T): void {
    this.past = []
    this.future = []
    this.now = state
  }
}
