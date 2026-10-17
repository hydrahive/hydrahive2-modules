/** Automatisch speichern der Schnittfassung (Spec „Bauplan 4b“): 0,8 s nach der letzten Änderung, mit `revision`.
 *  Ein Konflikt (anderer Tab) hält das Speichern an – es wird nie still überschrieben. Ohne DOM, damit testbar. */
import type { Timeline } from "./timelineApi"

export const SAVE_DELAY_MS = 800
export type SaveState = "saved" | "dirty" | "saving" | "error" | "conflict"

export class AutoSaver {
  private rev = 0
  private pending: Timeline | null = null
  private timer: ReturnType<typeof setTimeout> | null = null
  private running: Promise<void> | null = null
  private stopped = false
  private failed = false

  constructor(private save: (t: Timeline) => Promise<Timeline>, private onState: (s: SaveState) => void) {}

  /** Frisch vom Server geladen: Ausgangs-revision, nichts offen. */
  loaded(tl: Timeline): void {
    this.cancel()
    this.rev = tl.revision
    this.pending = null
    this.stopped = false
    this.onState("saved")
  }

  change(tl: Timeline): void {
    if (this.stopped) return
    this.failed = false
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
      (r) => { this.rev = r.revision; this.failed = false; this.onState(this.pending ? "dirty" : "saved") },
      (e: unknown) => {
        const code = (e as { code?: string })?.code ?? (e instanceof Error ? e.message : "")
        if (code === "studio_timeline_conflict") { this.stopped = true; this.onState("conflict") }
        else { this.pending = this.pending ?? tl; this.failed = true; this.onState("error") }   // nächster Versuch mit der nächsten Änderung
      },
    ).finally(() => { this.running = null })
    await this.running
    if (this.pending && !this.stopped && !this.failed && !this.timer) this.change(this.pending)   // während des Speicherns geändert
  }

  cancel(): void {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
  }
}
