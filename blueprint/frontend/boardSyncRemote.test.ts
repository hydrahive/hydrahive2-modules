// Abgleich der Zeichenfläche: Änderungen von anderer Stelle, Abfrage, Übernehmen und Wiederherstellen.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { failure, graph, raw, setup, tick } from "./boardSyncFixture"

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

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

  it("apply speichert erst die eigene Fassung und setzt dann das Ergebnis ein", async () => {
    const { sync, api, seen, server } = setup()
    await sync.start()
    sync.edit(graph("a", "b"))
    const action = vi.fn(async () => {
      expect(server.graph_json).toBe(raw("a", "b"))  // gesichert wird, was der Nutzer zuletzt gezeichnet hat
      return { ...server, graph_json: raw("p1"), revision: server.revision + 1 }
    })
    await expect(sync.apply(action)).resolves.toBe(true)
    expect(api.update).toHaveBeenCalledTimes(1)
    expect(seen.graphs).toEqual(["a", "p1"])
  })

  it("apply tut nichts, wenn sich die eigene Fassung nicht speichern lässt", async () => {
    const { sync, fail, seen } = setup()
    await sync.start()
    fail.update = failure(500)
    sync.edit(graph("a", "b"))
    const action = vi.fn(async () => { throw new Error("darf nicht laufen") })
    await expect(sync.apply(action)).resolves.toBe(false)
    expect(action).not.toHaveBeenCalled()
    expect(seen.graphs).toEqual(["a"])
  })

  it("apply reicht den Fehler der Aktion weiter und lässt die Zeichenfläche stehen", async () => {
    const { sync, seen } = setup()
    await sync.start()
    const action = async () => { throw failure(409, "proposal_changed") }
    await expect(sync.apply(action)).rejects.toMatchObject({ code: "proposal_changed" })
    expect(seen.graphs).toEqual(["a"])
    expect(sync.status).toBe("saved")
  })

  it("ein unlesbares Board lässt sich durch Übernehmen oder Wiederherstellen retten", async () => {
    const { sync, api, seen, server } = setup({ graph_json: "{kaputt" })
    await sync.start()
    expect(sync.status).toBe("unreadable")
    await expect(sync.apply(async () => ({ ...server, graph_json: raw("p1"), revision: 4 }))).resolves.toBe(true)
    expect(api.update).not.toHaveBeenCalled()  // das unlesbare Board wird nicht vorher „gespeichert“
    expect(seen.graphs).toEqual(["p1"])
    expect(sync.status).toBe("saved")
  })
})
