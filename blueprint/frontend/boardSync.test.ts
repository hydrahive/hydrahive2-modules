import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { graphSignature } from "./boardGraph"
import { BoardSync } from "./boardSync"
import type { Board, BPNode, Graph, SyncApi, SyncStatus } from "./types"

const node = (id: string, label = id): BPNode =>
  ({ id, type: "flowNode", position: { x: 0, y: 0 }, data: { kind: "flow", subtype: "action", label, note: "" } }) as BPNode
const graph = (...ids: string[]): Graph => ({ nodes: ids.map((id) => node(id)), edges: [] })
const raw = (...ids: string[]) => graphSignature(graph(...ids))
const failure = (status: number, code?: string) => Object.assign(new Error(code ?? "kaputt"), { status, code })

function setup(start: Partial<Board> = {}) {
  const server: Board = {
    id: 7, name: "Board", project_id: null, created_at: "", updated_at: "", revision: 3, graph_json: raw("a"),
    proposal_json: null, proposal_note: null, proposal_at: null, ...start,
  }
  const fail: { get?: unknown; update?: unknown; state?: unknown } = {}
  const api = {
    get: vi.fn(async () => { if (fail.get) throw fail.get; return { ...server } }),
    state: vi.fn(async () => {
      if (fail.state) throw fail.state
      return { revision: server.revision, proposal_at: server.proposal_at }
    }),
    update: vi.fn(async (_id: number, patch: { graph_json?: string; base_revision?: number; keep_previous?: boolean }) => {
      if (fail.update) throw fail.update
      if (patch.base_revision !== undefined && patch.base_revision !== server.revision) throw failure(409, "board_changed")
      if (patch.graph_json !== undefined && patch.graph_json !== server.graph_json) {
        server.graph_json = patch.graph_json
        server.revision += 1
      }
      return { ...server }
    }),
  } satisfies SyncApi
  const seen = { graphs: [] as string[], status: [] as SyncStatus[], boards: [] as Board[] }
  let visible = true
  const sync = new BoardSync(7, api, {
    onGraph: (g) => seen.graphs.push(g.nodes.map((n) => n.id).join(",")),
    onStatus: (s) => seen.status.push(s),
    onBoard: (b) => seen.boards.push(b),
  }, { isVisible: () => visible })
  /** Der Agent oder ein anderes Fenster ändert die Fassung auf dem Server. */
  const elsewhere = (...ids: string[]) => { server.graph_json = raw(...ids); server.revision += 1 }
  return { server, api, fail, seen, sync, elsewhere, hide: (hidden: boolean) => { visible = !hidden } }
}

const tick = (ms: number) => vi.advanceTimersByTimeAsync(ms)

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe("Laden", () => {
  it("zeigt das Board und speichert nichts", async () => {
    const { sync, api, seen } = setup()
    await sync.start()
    expect(seen.graphs).toEqual(["a"])
    expect(sync.status).toBe("saved")
    sync.edit(graph("a"))  // die Zeichenfläche meldet den geladenen Stand zurück
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
  })

  it("speichert nie, bevor geladen ist", async () => {
    const { sync, api } = setup()
    const loading = sync.start()
    sync.edit(graph())  // die leere Zeichenfläche vor dem Laden
    await tick(3000)
    await loading
    expect(api.update).not.toHaveBeenCalled()
  })

  it("ein Ladefehler überschreibt das Board nicht mit einem leeren", async () => {
    const { sync, api, fail, seen, server } = setup()
    fail.get = failure(500)
    await sync.start()
    expect(sync.status).toBe("load_error")
    sync.edit(graph())
    sync.edit(graph("neu"))
    await tick(20000)
    expect(api.update).not.toHaveBeenCalled()
    expect(api.state).not.toHaveBeenCalled()
    expect(server.graph_json).toBe(raw("a"))
    fail.get = undefined
    await sync.retry()
    expect(sync.status).toBe("saved")
    expect(seen.graphs).toEqual(["a"])
  })

  it("ein unlesbares Board wird weder gezeigt noch gespeichert", async () => {
    const { sync, api, seen } = setup({ graph_json: "{kaputt" })
    await sync.start()
    expect(sync.status).toBe("unreadable")
    expect(seen.graphs).toEqual([])
    sync.edit(graph())
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
  })

  it("ein gelöschtes Board ist weg", async () => {
    const { sync, fail } = setup()
    fail.get = failure(404, "board_not_found")
    await sync.start()
    expect(sync.status).toBe("gone")
  })
})

describe("Speichern", () => {
  it("fasst Änderungen zusammen und nennt den bekannten Stand", async () => {
    const { sync, api, server } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    expect(sync.status).toBe("saving")
    await tick(400)
    sync.edit(graph("a", "b", "c"))
    await tick(699)
    expect(api.update).not.toHaveBeenCalled()
    await tick(1)
    expect(api.update).toHaveBeenCalledTimes(1)
    expect(api.update).toHaveBeenCalledWith(7, { graph_json: raw("a", "b", "c"), base_revision: 3 })
    expect(sync.status).toBe("saved")
    expect(server.revision).toBe(4)
    sync.edit(graph("a"))
    await tick(700)
    expect(api.update).toHaveBeenLastCalledWith(7, { graph_json: raw("a"), base_revision: 4 })
  })

  it("Auswahl und Ziehen sind keine Änderung", async () => {
    const { sync, api } = setup()
    await sync.start()
    sync.edit({ nodes: [{ ...node("a"), selected: true, measured: { width: 210, height: 60 } } as BPNode], edges: [] })
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
    expect(sync.status).toBe("saved")
  })

  it("zurück zum gespeicherten Stand braucht kein Speichern", async () => {
    const { sync, api } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    sync.edit(graph("a"))
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
    expect(sync.status).toBe("saved")
  })

  it("eine Änderung während des Speicherns geht danach hinterher", async () => {
    const { sync, api } = setup()
    await sync.start()
    let release = () => {}
    api.update.mockImplementationOnce(async () => {
      await new Promise<void>((resolve) => { release = resolve })
      return { ...(await api.get()), revision: 4, graph_json: raw("a", "b") }
    })
    sync.edit(graph("a", "b"))
    await tick(700)
    sync.edit(graph("a", "b", "c"))
    await tick(5000)
    expect(api.update).toHaveBeenCalledTimes(1)  // nie zwei Speicherungen gleichzeitig
    release()
    await tick(700)
    expect(api.update).toHaveBeenCalledTimes(2)
    expect(api.update).toHaveBeenLastCalledWith(7, { graph_json: raw("a", "b", "c"), base_revision: 4 })
  })

  it("ein Fehler bleibt sichtbar und lässt sich wiederholen", async () => {
    const { sync, api, fail } = setup()
    await sync.start()
    fail.update = failure(500)
    sync.edit(graph("a", "b"))
    await tick(700)
    expect(sync.status).toBe("save_error")
    fail.update = undefined
    await sync.retry()
    expect(sync.status).toBe("saved")
    expect(api.update).toHaveBeenCalledTimes(2)
  })

  it("settle wartet auf das Speichern und sagt, ob alles gespeichert ist", async () => {
    const { sync, api, fail } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    await expect(sync.settle()).resolves.toBe(true)
    expect(api.update).toHaveBeenCalledTimes(1)
    fail.update = failure(500)
    sync.edit(graph("a"))
    await expect(sync.settle()).resolves.toBe(false)
  })

  it("beim Schließen geht eine ausstehende Änderung noch raus", async () => {
    const { sync, api, server } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    sync.stop()
    await tick(0)
    expect(api.update).toHaveBeenCalledTimes(1)
    expect(server.graph_json).toBe(raw("a", "b"))
    await tick(20000)
    expect(api.state).not.toHaveBeenCalled()
    expect(vi.getTimerCount()).toBe(0)  // kein Zeitgeber bleibt zurück
  })

  it("die Antwort des Speicherns meldet einen neuen Vorschlag sofort", async () => {
    const { sync, seen, server } = setup()
    await sync.start()
    server.proposal_json = raw("p1")
    server.proposal_at = "2026-11-12T16:00:00Z"
    sync.edit(graph("a", "b"))
    await tick(700)
    expect(seen.boards.at(-1)?.proposal_json).toBe(raw("p1"))
    expect(seen.graphs).toEqual(["a"])  // die Zeichenfläche bleibt, wie sie ist
  })
})

describe("Änderung von anderer Stelle", () => {
  it("überschreibt beim Speichern nichts Unbekanntes", async () => {
    const { sync, api, server, elsewhere } = setup()
    await sync.start()
    elsewhere("agent1", "agent2")
    sync.edit(graph("a", "b"))
    await tick(700)
    expect(sync.status).toBe("conflict")
    expect(server.graph_json).toBe(raw("agent1", "agent2"))
    sync.edit(graph("a", "b", "c"))
    await tick(20000)
    expect(api.update).toHaveBeenCalledTimes(1)  // im Konflikt wird nicht weiter gespeichert
  })

  it("„Meine behalten“ speichert mit Sicherung der anderen Fassung", async () => {
    const { sync, api, server, elsewhere } = setup()
    await sync.start()
    elsewhere("agent")
    sync.edit(graph("a", "b"))
    await tick(700)
    await sync.keepMine()
    expect(api.update).toHaveBeenLastCalledWith(7, { graph_json: raw("a", "b"), keep_previous: true })
    expect(sync.status).toBe("saved")
    expect(server.graph_json).toBe(raw("a", "b"))
    sync.edit(graph("a"))
    await tick(700)
    expect(api.update).toHaveBeenLastCalledWith(7, { graph_json: raw("a"), base_revision: server.revision - 1 })
  })

  it("„Neue laden“ zeigt die andere Fassung und verwirft den Entwurf", async () => {
    const { sync, api, seen, elsewhere } = setup()
    await sync.start()
    elsewhere("agent")
    sync.edit(graph("a", "b"))
    await tick(700)
    await sync.takeTheirs()
    expect(seen.graphs).toEqual(["a", "agent"])
    expect(sync.status).toBe("saved")
    await tick(3000)
    expect(api.update).toHaveBeenCalledTimes(1)
  })
})

describe("Abfrage", () => {
  it("fragt alle 5 Sekunden leicht nach und lädt nur bei Neuem", async () => {
    const { sync, api } = setup()
    await sync.start()
    await tick(4999)
    expect(api.state).not.toHaveBeenCalled()
    await tick(1)
    expect(api.state).toHaveBeenCalledTimes(1)
    await tick(10000)
    expect(api.state).toHaveBeenCalledTimes(3)
    expect(api.get).toHaveBeenCalledTimes(1)  // nur das Laden am Anfang
  })

  it("zeigt den direkt gezeichneten Entwurf des Agenten ohne Neuladen", async () => {
    const { sync, api, seen, elsewhere } = setup({ graph_json: raw(), revision: 0 })
    await sync.start()
    elsewhere("agent1", "agent2")
    await tick(5000)
    expect(seen.graphs).toEqual(["", "agent1,agent2"])
    expect(sync.status).toBe("saved")
    sync.edit(graph("agent1", "agent2"))
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
  })

  it("lässt ungespeicherte Änderungen stehen und meldet den Konflikt", async () => {
    const { sync, api, seen, elsewhere } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    elsewhere("agent")
    await tick(0)
    await sync.poll()
    expect(sync.status).toBe("conflict")
    expect(seen.graphs).toEqual(["a"])
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
  })

  it("meldet einen neuen Vorschlag, ohne die Zeichenfläche anzufassen", async () => {
    const { sync, seen, server } = setup()
    await sync.start()
    server.proposal_json = raw("p1", "p2")
    server.proposal_at = "2026-11-12T16:00:00Z"
    await tick(5000)
    expect(seen.boards.at(-1)?.proposal_json).toBe(raw("p1", "p2"))
    expect(seen.graphs).toEqual(["a"])
    server.proposal_json = null
    server.proposal_at = null
    await tick(5000)
    expect(seen.boards.at(-1)?.proposal_json).toBeNull()
  })

  it("hält das eigene Speichern nicht für eine fremde Änderung", async () => {
    const { sync, api, seen } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    await tick(700)
    await tick(5000)
    expect(sync.status).toBe("saved")
    expect(seen.graphs).toEqual(["a"])
    expect(api.get).toHaveBeenCalledTimes(1)
  })

  it("ruht im verdeckten Fenster und bei Fehlern passiert nichts", async () => {
    const { sync, api, fail, hide } = setup()
    await sync.start()
    hide(true)
    await tick(15000)
    expect(api.state).not.toHaveBeenCalled()
    hide(false)
    fail.state = failure(502)
    await tick(5000)
    expect(api.state).toHaveBeenCalledTimes(1)
    expect(sync.status).toBe("saved")
  })

  it("endet, wenn das Board gelöscht wurde", async () => {
    const { sync, api, fail } = setup()
    await sync.start()
    fail.state = failure(404, "board_not_found")
    await tick(5000)
    expect(sync.status).toBe("gone")
    await tick(20000)
    expect(api.state).toHaveBeenCalledTimes(1)
    sync.edit(graph("x"))
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
  })

  it("ein gelöschtes Board wird auch mit offenem Entwurf nicht mehr gespeichert", async () => {
    const { sync, api, fail } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    fail.state = failure(404, "board_not_found")
    await sync.poll()
    expect(sync.status).toBe("gone")
    await expect(sync.settle()).resolves.toBe(false)
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
  })
})

describe("Übernehmen und Wiederherstellen", () => {
  it("adopt zeigt die neue Fassung und speichert sie nicht zurück", async () => {
    const { sync, api, seen, server } = setup()
    await sync.start()
    const accepted = { ...server, graph_json: raw("p1", "p2"), revision: 4 }
    sync.adopt(accepted)
    expect(seen.graphs).toEqual(["a", "p1,p2"])
    expect(seen.boards.at(-1)).toEqual(accepted)
    sync.edit(graph("p1", "p2"))
    await tick(3000)
    expect(api.update).not.toHaveBeenCalled()
    Object.assign(server, accepted)
    sync.edit(graph("p1"))
    await tick(700)
    expect(api.update).toHaveBeenLastCalledWith(7, { graph_json: raw("p1"), base_revision: 4 })
  })
})
