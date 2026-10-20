import { describe, expect, it } from "vitest"
import { citationText, groupLaws, normLines, shortDate, syncSummary, type LawItem } from "./legalFormat"

const law = (key: string, group: string | null): LawItem =>
  ({ key, abbr: key.toUpperCase(), title: key, stand: "", fetched_at: "2026-10-20T03:30:00Z", pinned: !!group, norms: 1, group })

describe("groupLaws", () => {
  it("hält die Reihenfolge der Rubriken und hängt Nachgeladenes an", () => {
    const out = groupLaws([law("stgb", "Strafrecht"), law("bgb", "Zivil"), law("tierschg", null)], ["Zivil", "Familie", "Strafrecht"])
    expect(out.map((g) => g.group)).toEqual(["Zivil", "Strafrecht", "Weitere"])
    expect(out[2].laws.map((l) => l.key)).toEqual(["tierschg"])
  })
})

describe("citationText", () => {
  it("schreibt Paragraf und Artikel wie im Backend", () => {
    expect(citationText("§ 536c", "BGB")).toBe("§ 536c BGB")
    expect(citationText("Art 3", "GG")).toBe("Art. 3 GG")
  })
})

describe("normLines", () => {
  it("trennt Absätze und Listenpunkte", () => {
    const lines = normLines("(1) Erster Absatz.\n(2) Zweiter, nicht berechtigt,\n1. die Rechte,\n2. Schadensersatz\n\n")
    expect(lines).toEqual([
      { kind: "para", text: "(1) Erster Absatz." },
      { kind: "para", text: "(2) Zweiter, nicht berechtigt," },
      { kind: "item", text: "1. die Rechte," },
      { kind: "item", text: "2. Schadensersatz" },
    ])
  })
})

describe("shortDate / syncSummary", () => {
  it("formatiert deutsch", () => {
    expect(shortDate("2026-10-20T03:30:00Z")).toBe("20.10.2026")
    expect(shortDate("")).toBe("")
  })
  it("beschreibt den Abgleich", () => {
    expect(syncSummary(null, false)).toContain("Noch kein Abgleich")
    expect(syncSummary(null, true)).toBe("Abgleich läuft …")
    expect(syncSummary({ state: "done", total: 54, changed: 3, errors: [{}], finished_at: "2026-10-21T03:31:00Z" }, false))
      .toBe("Letzter Abgleich 21.10.2026: 54 Gesetze, 3 geändert, 1 Fehler.")
  })
})
