/** Automatisch speichern (Spec „Bauplan 4b“, auch Untertitel 6a): 0,8 s nach der letzten Änderung, mit `revision`.
 *  Ein Konflikt (anderer Tab) hält das Speichern an – es wird nie still überschrieben. Ohne DOM, damit testbar. */
import type { Timeline } from "./timelineApi"

interface Revisioned { revision: number }

export const SAVE_DELAY_MS = 800
export type SaveState = "saved" | "dirty" | "saving" | "error" | "conflict"

export class AutoSaver<T extends Revisioned = Timeline> {
  private rev = 0
  private pending: T | null = null
  private timer: ReturnType<typeof setTimeout> | null = null
  private running: Promise<void> | null = null
  private stopped = false

  private save: (t: T) => Promise<Revisioned>
  private onState: (s: SaveState) => void
  private conflictCode: string

  constructor(save: (t: T) => Promise<Revisioned>, onState: (s: SaveState) => void, conflictCode = "studio_timeline_conflict") {
    this.save = save
    this.onState = onState
    this.conflictCode = conflictCode
  }

  /** Frisch vom Server geladen: Ausgangs-revision, nichts offen. */
  loaded(tl: Revisioned): void {
    this.cancel()
    this.rev = tl.revision
    this.pending = null
    this.stopped = false
    this.onState("saved")
  }

  change(tl: T): void {
    if (this.stopped) return
    this.pending = tl
    this.onState("dirty")
    if (this.timer) clearTimeout(this.timer)
    this.timer = setTimeout(() => { this.timer = null; void this.flush() }, SAVE_DELAY_MS)
  }

  /** Sofort speichern (z. B. beim Verlassen des Reiters). */
  async flush(): Promise<void> {
    if (this.timer) { clearTimeout(this.timer); this.timer = null }
    if (this.running) await this.running
    if (!this.pending || this.stopped) return
    const tl = { ...this.pending, revision: this.rev }
    this.pending = null
    this.onState("saving")
    this.running = this.save(tl).then(
      (r) => { this.rev = r.revision; this.onState(this.pending ? "dirty" : "saved") },
      (e: unknown) => {
        const code = (e as { code?: string })?.code ?? (e instanceof Error ? e.message : "")
        if (code === this.conflictCode) { this.stopped = true; this.onState("conflict") }
        else { this.pending = this.pending ?? tl; this.onState("error") }   // nächster Versuch mit der nächsten Änderung
      },
    ).finally(() => { this.running = null })
    await this.running                                               // während des Speicherns geändert: change() hat schon neu geplant
  }

  cancel(): void {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
  }
}
