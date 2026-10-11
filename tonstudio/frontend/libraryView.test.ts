import { describe, expect, it } from "vitest"
import { displayName, groupLibrary } from "./libraryView"
import type { LibraryItem } from "./types"

const it_ = (p: Partial<LibraryItem>): LibraryItem => ({
  source_rel: p.name ?? "x", origin: "project", group: "generated", name: "x", duration: null, model: null,
  backend: null, prompt: null, created_at: null, ...p,
})

const items = [
  it_({ name: "Zebra", group: "media", duration: 60, created_at: "2026-06-25T10:00:00Z" }),
  it_({ name: "anton", group: "media", duration: 200, created_at: "2026-10-01T10:00:00Z" }),
  it_({ name: "Technosong", group: "atelier", model: "google/lyria-3-pro-preview", created_at: "2026-10-10T10:00:00Z" }),
  it_({ name: "Ratten", group: "tonstudio", origin: "generated", prompt: "Lied über kochende Ratten" }),
]

describe("groupLibrary", () => {
  it("gliedert in fester Reihenfolge und lässt leere Gruppen weg", () => {
    expect(groupLibrary(items, "new", "").map((x) => x.g)).toEqual(["tonstudio", "atelier", "media"])
  })
  it("sortiert nach Name ohne Groß/Klein", () => {
    const media = groupLibrary(items, "name", "").find((x) => x.g === "media")!
    expect(media.list.map((i) => i.name)).toEqual(["anton", "Zebra"])
  })
  it("sortiert neueste zuerst und längste zuerst", () => {
    const m = (s: "new" | "length") => groupLibrary(items, s, "").find((x) => x.g === "media")!.list.map((i) => i.name)
    expect(m("new")).toEqual(["anton", "Zebra"])
    expect(m("length")).toEqual(["anton", "Zebra"])
    const short = [it_({ name: "kurz", group: "media", duration: 10, created_at: "2026-10-09T00:00:00Z" }),
      it_({ name: "lang", group: "media", duration: 300, created_at: "2026-01-01T00:00:00Z" })]
    expect(groupLibrary(short, "length", "")[0].list.map((i) => i.name)).toEqual(["lang", "kurz"])
    expect(groupLibrary(short, "new", "")[0].list.map((i) => i.name)).toEqual(["kurz", "lang"])
  })
  it("filtert über Name, Prompt und Modell", () => {
    expect(groupLibrary(items, "new", "RATTEN").flatMap((x) => x.list.map((i) => i.name))).toEqual(["Ratten"])
    expect(groupLibrary(items, "new", "kochende").flatMap((x) => x.list.map((i) => i.name))).toEqual(["Ratten"])
    expect(groupLibrary(items, "new", "lyria").flatMap((x) => x.list.map((i) => i.name))).toEqual(["Technosong"])
    expect(groupLibrary(items, "new", "gibtsnicht")).toEqual([])
  })
})

describe("displayName", () => {
  const fb = (d: string) => `Song vom ${d}`
  it("zeigt bekannten Namen", () => {
    expect(displayName(it_({ name: "Taverne", named: true }), fb)).toBe("Taverne")
    expect(displayName(it_({ name: "Taverne" }), fb)).toBe("Taverne")
  })
  it("ersetzt UUID-Dateinamen durch Datum", () => {
    const n = displayName(it_({ name: "3927ba7597cd.mp3", named: false, created_at: "2026-06-25T20:03:00Z" }), fb)
    expect(n).toMatch(/^Song vom 25\.06\.2026, \d\d:03$/)
  })
  it("ohne Datum bleibt der Dateiname", () => {
    expect(displayName(it_({ name: "x.mp3", named: false, created_at: null }), fb)).toBe("x.mp3")
  })
})
