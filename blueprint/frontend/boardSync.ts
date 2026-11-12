// Abgleich einer offenen Zeichenfläche mit dem Server, ohne React (direkt testbar).
//
// Regeln:
//  - Gespeichert wird erst, wenn das Board geladen und lesbar ist. Ein Ladefehler oder ein
//    unlesbares Board führt nie dazu, dass ein leeres Board gespeichert wird.
//  - Jedes Speichern nennt den Stand (revision), den die Zeichenfläche kennt. Hat inzwischen der
//    Agent oder ein anderes Fenster gezeichnet, lehnt der Server ab: Konflikt statt Überschreiben.
//  - Alle 5 Sekunden eine leichte Abfrage: Neue Fassung oder neuer Vorschlag erscheinen ohne Neuladen.
import { cleanGraph, graphSignature, parseGraph } from "./boardGraph"
import type { Board, Graph, SyncApi, SyncEvents, SyncStatus } from "./types"

export const SAVE_DELAY_MS = 700
export const POLL_MS = 5000

// In diesen Zuständen ist das Board geladen und lesbar.
const READY: readonly SyncStatus[] = ["saved", "saving", "save_error", "conflict"]
const isGone = (problem: unknown) => (problem as { status?: number } | null)?.status === 404
const isChanged = (problem: unknown) => (problem as { code?: string } | null)?.code === "board_changed"

export class BoardSync {
  status: SyncStatus = "loading"
  private readonly id: number
  private readonly api: SyncApi
  private readonly events: SyncEvents
  private readonly isVisible: () => boolean
  private saved = ""  // Inhalt, den der Server hat
  private draft = ""  // Inhalt der Zeichenfläche
  private revision = 0
  private proposalAt: string | null = null
  private timer: ReturnType<typeof setTimeout> | null = null
  private interval: ReturnType<typeof setInterval> | null = null
  private inFlight: Promise<void> | null = null
  private polling = false
  private alive = true

  constructor(id: number, api: SyncApi, events: SyncEvents, env: { isVisible?: () => boolean } = {}) {
    this.id = id
    this.api = api
    this.events = events
    this.isVisible = env.isVisible ?? (() => true)
  }

  private get ready() { return READY.includes(this.status) }
  private get dirty() { return this.draft !== this.saved }
  /** Abfragen lohnt nicht: zu, beschäftigt, nicht geladen, im Konflikt oder verdeckt. */
  private get idle() {
    return !this.alive || this.polling || !!this.inFlight || !this.ready || this.status === "conflict" || !this.isVisible()
  }

  private set(status: SyncStatus) {
    if (status === this.status) return
    this.status = status
    if (this.alive) this.events.onStatus(status)
  }

  private clearTimer() {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
  }

  /** Stand des Servers übernehmen. Ohne withGraph nur Vorschlag und Angaben, die Zeichenfläche bleibt. */
  private show(board: Board, withGraph: boolean) {
    this.proposalAt = board.proposal_at
    if (withGraph) {
      const parsed = parseGraph(board.graph_json)
      this.revision = board.revision
      this.clearTimer()
      if (parsed) {
        const graph = cleanGraph(parsed)
        this.saved = this.draft = JSON.stringify(graph)
        if (this.alive) this.events.onGraph(graph)
      }
      this.set(parsed ? "saved" : "unreadable")
    }
    if (this.alive) this.events.onBoard(board)
  }

  private async load(): Promise<void> {
    try {
      const board = await this.api.get(this.id)
      if (this.alive) this.show(board, true)
    } catch (problem) {
      this.set(isGone(problem) ? "gone" : "load_error")
    }
  }

  async start(): Promise<void> {
    this.set("loading")
    await this.load()
    if (this.alive && !this.interval) this.interval = setInterval(() => { void this.poll() }, POLL_MS)
  }

  /** Die Zeichenfläche meldet ihren Inhalt. Gespeichert wird nur, was sich vom Server unterscheidet. */
  edit(graph: Graph) {
    if (!this.ready) return
    this.draft = graphSignature(graph)
    if (this.status === "conflict") return
    this.clearTimer()
    if (!this.dirty) {
      if (!this.inFlight) this.set("saved")
      return
    }
    this.set("saving")
    this.timer = setTimeout(() => { this.timer = null; void this.flush() }, SAVE_DELAY_MS)
  }

  /** Speichert den Entwurf. Nie zwei Speicherungen gleichzeitig. keep: über eine neuere Fassung stellen. */
  private flush(keep = false): Promise<void> {
    if (this.inFlight) return this.inFlight
    if (!this.ready || (!keep && (this.status === "conflict" || !this.dirty))) return Promise.resolve()
    const sent = this.draft
    this.set("saving")
    this.inFlight = this.api
      .update(this.id, keep ? { graph_json: sent, keep_previous: true } : { graph_json: sent, base_revision: this.revision })
      .then((board) => {
        this.saved = sent
        this.revision = board.revision
        this.set(this.dirty ? "saving" : "saved")
        this.show(board, false)
      })
      .catch((problem: unknown) => {
        this.set(isGone(problem) ? "gone" : isChanged(problem) ? "conflict" : "save_error")
      })
      .finally(() => {
        this.inFlight = null
        // Während des Speicherns kam eine Änderung dazu und ihre Wartezeit ist schon um.
        if (this.status === "saving" && this.dirty && !this.timer) void this.flush()
      })
    return this.inFlight
  }

  /** Wartet, bis alles gespeichert ist. false, wenn das nicht geht (Fehler, Konflikt, nicht geladen). */
  async settle(): Promise<boolean> {
    this.clearTimer()
    await this.flush()
    if (this.status === "saving" && this.dirty) await this.flush()
    return this.status === "saved" && !this.dirty
  }

  retry(): Promise<void> {
    if (this.status === "load_error") return this.start()
    if (this.status !== "save_error") return Promise.resolve()
    this.clearTimer()
    return this.flush()
  }

  /** Konflikt: die eigene Fassung behalten. Die andere Fassung legt der Server zu den früheren. */
  keepMine(): Promise<void> {
    return this.status === "conflict" ? this.flush(true) : Promise.resolve()
  }

  /** Konflikt: die Fassung des Servers laden, der eigene Entwurf entfällt. */
  takeTheirs(): Promise<void> {
    return this.status === "conflict" ? this.load() : Promise.resolve()
  }

  /** Antwort auf Übernehmen, Verwerfen oder Wiederherstellen einsetzen. */
  adopt(board: Board) {
    this.show(board, board.revision !== this.revision)
  }

  async poll(): Promise<void> {
    if (this.idle) return
    this.polling = true
    try {
      const state = await this.api.state(this.id)
      const moved = state.revision !== this.revision
      if (!this.alive || this.inFlight || (!moved && state.proposal_at === this.proposalAt)) return
      if (moved && this.dirty) {
        this.clearTimer()
        this.set("conflict")
        return
      }
      const board = await this.api.get(this.id)
      // Wurde inzwischen selbst gezeichnet oder gespeichert, entscheidet die nächste Runde.
      if (!this.alive || this.inFlight || (board.revision !== this.revision && this.dirty)) return
      this.show(board, board.revision !== this.revision)
    } catch (problem) {
      if (isGone(problem)) {
        this.clearTimer()
        this.set("gone")
      }
    } finally {
      this.polling = false
    }
  }

  /** Fenster zu oder Board gewechselt: Ausstehendes noch abschicken, danach keine Meldungen mehr. */
  stop() {
    this.alive = false
    if (this.interval) clearInterval(this.interval)
    this.interval = null
    this.clearTimer()
    if (this.status === "saving") void this.flush()
  }
}
