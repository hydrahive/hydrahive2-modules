// Abgleich der Zeichenfläche: Laden und Speichern. Änderungen von anderer Stelle: boardSyncRemote.test.ts.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { failure, graph, node, raw, setup, tick } from "./boardSyncFixture"
import type { BPNode } from "./types"

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
