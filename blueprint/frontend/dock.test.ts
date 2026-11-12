import { describe, expect, it } from "vitest"
import {
  addMissingTools, clampWidth, DOCK_DEFAULT, DOCK_MIN, openChat, readDock, startResize, withTools,
  type ResizeTarget,
} from "./dock"
import type { ChatInfo, ChatStart } from "./types"

describe("Chat neben dem Board: Breite und Zustand", () => {
  it("hält die Breite zwischen Mindestmaß und 45 % des Fensters", () => {
    expect(clampWidth(100, 1500)).toBe(DOCK_MIN)
    expect(clampWidth(500, 1500)).toBe(500)
    expect(clampWidth(5000, 1500)).toBe(675)
    expect(clampWidth(Number.NaN, 1500)).toBe(DOCK_DEFAULT)
  })

  it("das Mindestmaß lässt dem Eingabefeld des Chats Platz", () => {
    // Im Browser gemessen (12.11.2026): Links vom Eingabefeld stehen vier Knöpfe der Chatansicht. Bei 320 px
    // blieben dem Feld 94 px, bei 360 px sind es 134 px. Game Studio und Storyteller nehmen ebenfalls 360.
    expect(DOCK_MIN).toBe(360)
    expect(DOCK_DEFAULT).toBeGreaterThan(DOCK_MIN)
  })

  it("lässt der Zeichenfläche auf schmalen Fenstern Platz, unterschreitet das Mindestmaß aber nie", () => {
    expect(clampWidth(DOCK_DEFAULT, 800)).toBe(360)
    expect(clampWidth(DOCK_DEFAULT, 500)).toBe(DOCK_MIN)
  })

  it("liest den gemerkten Zustand und fällt bei Unlesbarem auf geschlossen zurück", () => {
    expect(readDock('{"open":true,"width":520}', 1500)).toEqual({ open: true, width: 520 })
    expect(readDock('{"open":"ja","width":"breit"}', 1500)).toEqual({ open: false, width: DOCK_DEFAULT })
    for (const raw of [null, "", "{kaputt", "null", "7"]) {
      expect(readDock(raw, 1500), String(raw)).toEqual({ open: false, width: DOCK_DEFAULT })
    }
  })

  it("ergänzt fehlende Werkzeuge, ohne vorhandene zu verlieren oder zu verdoppeln", () => {
    expect(withTools(["shell_exec", "blueprint_read"], ["blueprint_read", "blueprint_propose"]))
      .toEqual(["shell_exec", "blueprint_read", "blueprint_propose"])
    expect(withTools([], [])).toEqual([])
  })
})

describe("Chat neben dem Board: Öffnen", () => {
  const AGENT = { id: "agent-1", name: "Projekt-Agent" }
  const info = (over: Partial<ChatInfo> = {}): ChatInfo =>
    ({ agent: AGENT, reason: null, can_start: true, tools_missing: [], ...over })
  const session = (reused: boolean): ChatStart => ({ session_id: "s-1", reused, agent: AGENT, intro: "Board 7" })

  function source(chat: ChatInfo, start: ChatStart) {
    const calls: string[] = []
    return {
      calls,
      chatInfo: async (id: number) => { calls.push(`info:${id}`); return chat },
      startChat: async (id: number) => { calls.push(`start:${id}`); return start },
    }
  }

  it("legt keine Sitzung an, wenn der Nutzer nicht chatten darf", async () => {
    const blocked = info({ agent: null, reason: "read_only", can_start: false })
    const api = source(blocked, session(false))
    expect(await openChat(7, api)).toEqual({ info: blocked, started: null, showIntro: false })
    expect(api.calls).toEqual(["info:7"])
  })

  it("zeigt den Einstiegstext bei einer neuen Sitzung offen", async () => {
    const api = source(info(), session(false))
    expect(await openChat(7, api)).toEqual({ info: info(), started: session(false), showIntro: true })
    expect(api.calls).toEqual(["info:7", "start:7"])
  })

  it("lässt den Einstiegstext eingeklappt, wenn die Sitzung des Boards schon besteht", async () => {
    const opening = await openChat(7, source(info(), session(true)))
    expect(opening.started?.reused).toBe(true)
    expect(opening.showIntro).toBe(false)
  })

  it("meldet die Auskunft, bevor die Sitzung angelegt ist: Der Hinweis auf fehlende Werkzeuge wartet nicht", async () => {
    const api = source(info({ tools_missing: ["blueprint_propose"] }), session(false))
    const seen: string[] = []
    await openChat(7, api, (early) => seen.push(`${early.tools_missing.join()}@${api.calls.join("+")}`))
    expect(seen).toEqual(["blueprint_propose@info:7"])
  })

  it("reicht einen Fehler weiter, statt ihn zu schlucken", async () => {
    const api = { chatInfo: async () => info(), startChat: async () => { throw new Error("kaputt") } }
    await expect(openChat(7, api)).rejects.toThrow("kaputt")
  })
})

describe("Chat neben dem Board: fehlende Werkzeuge ergänzen", () => {
  const AGENT = { id: "agent-1", name: "Projekt-Agent" }
  const missing: ChatInfo = { agent: AGENT, reason: null, can_start: true, tools_missing: ["blueprint_propose"] }
  const complete: ChatInfo = { ...missing, tools_missing: [] }
  const describeProblem = (problem: unknown) => `Grund: ${(problem as Error).message}`

  function source(fail: "" | "add" | "info" = "") {
    const calls: string[] = []
    return {
      calls,
      addTools: async (agentId: string, tools: string[]) => {
        calls.push(`add:${agentId}:${tools.join()}`)
        if (fail === "add") throw new Error("verwaltet")
      },
      chatInfo: async (id: number) => {
        calls.push(`info:${id}`)
        if (fail === "info") throw new Error("weg")
        return complete
      },
    }
  }

  it("ergänzt die fehlenden Werkzeuge am Agenten und fragt die Auskunft neu ab", async () => {
    const api = source()
    expect(await addMissingTools(7, missing, api, describeProblem)).toEqual({ info: complete, toolsError: null })
    expect(api.calls).toEqual(["add:agent-1:blueprint_propose", "info:7"])
  })

  it("nennt den Grund, wenn das Ergänzen scheitert, und lässt die Auskunft stehen", async () => {
    const api = source("add")
    expect(await addMissingTools(7, missing, api, describeProblem))
      .toEqual({ info: missing, toolsError: "Grund: verwaltet" })
    expect(api.calls).toEqual(["add:agent-1:blueprint_propose"])
  })

  it("nennt den Grund auch, wenn nur die neue Auskunft scheitert", async () => {
    expect(await addMissingTools(7, missing, source("info"), describeProblem))
      .toEqual({ info: missing, toolsError: "Grund: weg" })
  })

  it("ruft nichts auf, wenn es keinen Agenten gibt", async () => {
    const api = source()
    const blocked: ChatInfo = { agent: null, reason: "no_agent", can_start: false, tools_missing: [] }
    expect(await addMissingTools(7, blocked, api, describeProblem)).toEqual({ info: blocked, toolsError: null })
    expect(api.calls).toEqual([])
  })
})

describe("Chat neben dem Board: Breite ziehen", () => {
  type Listener = (event: { clientX: number; buttons: number }) => void

  /** Ersatz für das Fenster: merkt sich die angemeldeten Zuhörer und löst Ereignisse aus. */
  function fakeWindow(innerWidth = 1500) {
    const listeners = new Map<string, Set<Listener>>()
    const target = {
      innerWidth,
      addEventListener: (type: string, fn: Listener) => { listeners.set(type, (listeners.get(type) ?? new Set()).add(fn)) },
      removeEventListener: (type: string, fn: Listener) => { listeners.get(type)?.delete(fn) },
    }
    return {
      target: target as unknown as ResizeTarget,
      fire: (type: string, clientX = 0, buttons = 1) =>
        [...(listeners.get(type) ?? [])].forEach((fn) => fn({ clientX, buttons })),
      count: () => [...listeners.values()].reduce((sum, set) => sum + set.size, 0),
    }
  }

  function drag(startX = 1000, startWidth = 420) {
    const win = fakeWindow()
    const widths: number[] = []
    let prevented = 0
    startResize({ clientX: startX, preventDefault: () => { prevented += 1 } }, startWidth, win.target, (w) => widths.push(w))
    return { win, widths, prevented: () => prevented }
  }

  it("folgt der Maus: nach links breiter, nach rechts schmaler, innerhalb der Grenzen", () => {
    const { win, widths } = drag()
    win.fire("pointermove", 900)
    win.fire("pointermove", 1050)
    win.fire("pointermove", 100)
    win.fire("pointermove", 1400)
    expect(widths).toEqual([520, 370, 675, DOCK_MIN])
  })

  it("verhindert, dass der Zug Text markiert", () => {
    // Im Browser gesehen (12.11.2026): Ohne das markiert der Zug Text, und der nächste Zug zieht die Markierung.
    expect(drag().prevented()).toBe(1)
  })

  it("endet beim Loslassen und räumt seine Zuhörer ab", () => {
    const { win, widths } = drag()
    win.fire("pointermove", 900)
    win.fire("pointerup")
    win.fire("pointermove", 500)
    expect(widths).toEqual([520])
    expect(win.count()).toBe(0)
  })

  it("endet auch, wenn der Browser den Zug abbricht (pointercancel), statt der Maus weiter zu folgen", () => {
    const { win, widths } = drag()
    win.fire("pointercancel")
    win.fire("pointermove", 500)
    expect(widths).toEqual([])
    expect(win.count()).toBe(0)
  })

  it("endet, wenn sich die Maus ohne gedrückte Taste bewegt: Das Loslassen kam dann nicht an", () => {
    const { win, widths } = drag()
    win.fire("pointermove", 900)
    win.fire("pointermove", 500, 0)
    win.fire("pointermove", 400)
    expect(widths).toEqual([520])
    expect(win.count()).toBe(0)
  })
})
