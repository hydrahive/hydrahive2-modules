// Speichern eines Buchs auf dem Server – ohne React, damit testbar (bookSync.test.ts).
// `local` = was der Nutzer sieht, `saved` = was der Server sicher hat. Gespeichert wird nur der
// Unterschied, jeweils mit der Version, auf der er aufbaut. Veraltete Version → Konflikt, und es
// wird nichts mehr gespeichert, bis der Nutzer entschieden hat (Spec 1b §3).
import { storyApi, StoryApiError, type ServerScene, type ServerStructure } from "./api"
import { findScene, updateScene, type Book, type Scene } from "./model"
import {
  applyStructure, headPatch, sceneFromServer, scenePatches, structureChanged,
  structureProblem, toStructure, type Versions,
} from "./serverBook"
import { applyResolution, conflictSnapshot, sceneMap, toConflict, type Conflict } from "./syncConflict"

export type SaveState = "saved" | "saving" | "failed" | "conflict"
export type { Conflict } from "./syncConflict"

/** `textRev` zählt Texte, die von außen ersetzt wurden (Konflikt neu geladen, Schnappschuss zurück):
 *  der Editor lädt dann neu, statt den alten Text weiter anzuzeigen. */
export interface SyncView { book: Book; saveState: SaveState; saveError: string; conflict: Conflict | null; textRev: number }
type Api = Pick<typeof storyApi, "patchBook" | "putScene" | "putStructure" | "addSnapshot">

export class BookSync {
  private local: Book
  private saved: Book
  private readonly versions: Versions
  private state: SaveState = "saved"
  private error = ""
  private conflict: Conflict | null = null
  private textRev = 0
  private running: Promise<void> | null = null
  private timer: ReturnType<typeof setTimeout> | null = null
  private readonly projectId: string
  private readonly onChange: (v: SyncView) => void
  private readonly api: Api
  private readonly delayMs: number

  constructor(projectId: string, initial: Book, versions: Versions, onChange: (v: SyncView) => void,
    api: Api = storyApi, delayMs = 1000) {
    this.projectId = projectId
    this.onChange = onChange
    this.api = api
    this.delayMs = delayMs
    this.local = initial
    this.saved = initial
    this.versions = { ...versions, scenes: { ...versions.scenes } }
  }

  get book(): Book { return this.local }
  get dirty(): boolean { return this.diff() }

  /** Neue Fassung aus der Oberfläche; Speichern 1 s nach der letzten Änderung. */
  edit(next: Book): void {
    this.local = next
    if (!this.conflict) {
      this.state = "saving"
      this.schedule()
    }
    this.emit()
  }

  /** Sofort speichern (Szene wechseln, Buch schließen). Wartet auf eine laufende Runde. */
  async flush(): Promise<void> {
    if (this.timer) { clearTimeout(this.timer); this.timer = null }
    while (this.running) await this.running
    if (this.conflict || !this.diff()) {
      if (this.state === "saving") this.setState("saved")
      return
    }
    this.running = this.saveRound().finally(() => { this.running = null })
    await this.running
    if (!this.conflict && this.state !== "failed" && this.diff()) await this.flush()
  }

  /** Szenentext von außen ersetzen (Schnappschuss zurückholen): wie eine Änderung, Editor lädt neu. */
  replaceText(sceneId: string, text: string, origin?: Scene["origin"]): void {
    this.textRev += 1
    this.edit(updateScene(this.local, sceneId, origin ? { text, origin } : { text }))
  }

  /** Szene, die der Server selbst geändert hat (z. B. Gedächtnis-Zusammenfassung): Version und
   *  Server-Felder übernehmen; ungespeicherte eigene Änderungen an anderen Feldern bleiben. */
  adoptScene(s: ServerScene): void {
    const fresh = sceneFromServer(s)
    const mine = findScene(this.local, s.id)?.scene
    const saved = findScene(this.saved, s.id)?.scene
    this.versions.scenes[s.id] = s.version
    this.saved = updateScene(this.saved, s.id, fresh)
    if (mine && saved) {
      const keep: Partial<Scene> = {}
      for (const k of ["title", "summary", "pov", "status", "origin", "text"] as const) {
        if (mine[k] !== saved[k]) (keep as Record<string, unknown>)[k] = mine[k]
      }
      this.local = updateScene(this.local, s.id, { ...fresh, ...keep })
    }
    this.emit()
  }

  /** Server hat die Struktur selbst geändert (Szene/Kapitel angelegt oder gelöscht). */
  adoptStructure(st: ServerStructure, added?: ServerScene): void {
    this.versions.structure = st.version
    if (added) this.versions.scenes[added.id] = added.version
    const merge = (b: Book) => {
      const known = sceneMap(b)
      if (added) known.set(added.id, sceneFromServer(added))
      return { ...b, parts: applyStructure(st, (id) => known.get(id)), entities: st.entities }
    }
    this.saved = merge(this.saved)
    this.local = merge(this.local)
    this.emit()
  }

  /** reload: Server-Stand übernehmen, eigene Fassung als Schnappschuss.
   *  keep: eigene Fassung behalten, fremde vorher als Schnappschuss, dann speichern. */
  async resolve(how: "reload" | "keep"): Promise<string | null> {
    const c = this.conflict
    if (!c) return null
    const snap = conflictSnapshot(c, how)
    if (snap) await this.api.addSnapshot(this.projectId, this.local.id, snap.sceneId, snap.text)
    const r = applyResolution(c, how, this.saved, this.local, this.versions)
    this.saved = r.saved
    this.local = r.local
    if (r.reloadText) this.textRev += 1
    this.conflict = null
    this.setState("saved")
    await this.flush()
    return snap?.sceneId ?? null
  }

  dispose(): void { if (this.timer) clearTimeout(this.timer) }

  // ---- intern ----------------------------------------------------------------------------

  private diff(): boolean {
    return Object.keys(headPatch(this.local, this.saved)).length > 0
      || scenePatches(this.local, this.saved).length > 0
      || structureChanged(this.local, this.saved)
  }

  private schedule(): void {
    if (this.timer) clearTimeout(this.timer)
    this.timer = setTimeout(() => { this.timer = null; void this.flush() }, this.delayMs)
  }

  private async saveRound(): Promise<void> {
    this.setState("saving")
    try {
      await this.saveHead()
      await this.saveScenes()
      await this.saveStructure()
      this.error = ""
      this.setState(this.diff() ? "saving" : "saved")
    } catch (e) {
      if (e instanceof StoryApiError && e.status === 409 && e.code === "version_conflict") {
        this.conflict = toConflict(e.current, this.local)
        this.setState("conflict")
      } else {
        this.error = e instanceof StoryApiError ? e.code : String(e)
        this.setState("failed")
      }
    }
  }

  private async saveHead(): Promise<void> {
    const head = headPatch(this.local, this.saved)
    if (!Object.keys(head).length) return
    if ("title" in head && !this.local.title.trim()) throw new StoryApiError(400, "title_required")
    const h = await this.api.patchBook(this.projectId, this.local.id, this.versions.book, head)
    this.versions.book = h.version
    this.saved = { ...this.saved, ...head, ghost: { ...this.saved.ghost, ...(head.ghost ?? {}) }, updatedAt: h.updated_at }
  }

  private async saveScenes(): Promise<void> {
    for (const { id, patch } of scenePatches(this.local, this.saved)) {
      const s = await this.api.putScene(this.projectId, this.local.id, id, this.versions.scenes[id], patch)
      this.versions.scenes[id] = s.version
      this.saved = updateScene(this.saved, id, patch)
    }
  }

  private async saveStructure(): Promise<void> {
    const now = this.local
    if (!structureChanged(now, this.saved)) return
    const problem = structureProblem(now)
    if (problem) throw new StoryApiError(400, problem)
    const st = await this.api.putStructure(this.projectId, now.id, this.versions.structure, toStructure(now))
    this.versions.structure = st.version
    this.saved = { ...this.saved, parts: applyStructure(st, (id) => sceneMap(this.saved).get(id) ?? sceneMap(now).get(id)), entities: now.entities }
  }

  private setState(s: SaveState): void { this.state = s; this.emit() }

  private emit(): void {
    this.onChange({ book: this.local, saveState: this.state, saveError: this.error, conflict: this.conflict, textRev: this.textRev })
  }
}
