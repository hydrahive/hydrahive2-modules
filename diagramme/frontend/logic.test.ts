import { describe, expect, it } from "vitest"
import { diagrammeI18n } from "./i18n"
import { errorKey, kindLabelKey, listQuery, sameUser, shortDate } from "./logic"

/** Alle Fehlercodes, die das Backend an die Oberfläche schickt (coded + KNOWN). */
function backendCodes(): string[] {
  const src = Object.values(import.meta.glob("../backend/*.py", { query: "?raw", import: "default", eager: true })).join("\n")
  return [...new Set([...src.matchAll(/"(diagram_[a-z_]+)"/g)].map((m) => m[1]))].sort()
}

describe("Diagramme: Logik der Sammlung (Spec §12.2)", () => {
  it("jeder Fehlercode des Backends hat einen Text (de/en)", () => {
    const codes = backendCodes()
    for (const c of ["diagram_not_found", "diagram_not_owner", "diagram_not_in_trash"]) expect(codes).toContain(c)
    for (const lang of ["de", "en"] as const) {
      const err = (diagrammeI18n[lang].diagramme as unknown as { err: Record<string, string> }).err
      expect(codes.filter((c) => !err[c]), lang).toEqual([])
    }
  })

  it("errorKey nimmt bekannte Codes, sonst einen allgemeinen Text", () => {
    expect(errorKey(Object.assign(new Error("x"), { code: "diagram_not_owner" }))).toBe("err.diagram_not_owner")
    expect(errorKey(new Error("Netz weg"))).toBe("err.general")
    expect(errorKey("kaputt")).toBe("err.general")
  })

  it("jede Art hat einen Namen in Worten, Unbekanntes einen neutralen", () => {
    for (const k of ["architecture", "workflow", "sequence", "dataflow", "lifecycle", "erd", "class", "tree", "timeline", "waterfall", "explainer"]) {
      expect(kindLabelKey(k)).toBe(`kind.${k}`)
      for (const lang of ["de", "en"] as const) {
        const kind = (diagrammeI18n[lang].diagramme as unknown as { kind: Record<string, string> }).kind
        expect(kind[k], `${lang} ${k}`).toBeTruthy()
      }
    }
    expect(kindLabelKey("../x")).toBe("kind.other")
  })

  it("listQuery baut die Abfrage, ohne leere Teile", () => {
    expect(listQuery({ q: "", project: "", trash: false })).toBe("/modules/diagramme/list?trash=0")
    expect(listQuery({ q: " Websuche ", project: "p-1", trash: true })).toBe("/modules/diagramme/list?trash=1&q=Websuche&project=p-1")
    expect(listQuery({ q: "a&b=c", project: "none", trash: false })).toBe("/modules/diagramme/list?trash=0&q=a%26b%3Dc&project=none")
  })

  it("shortDate zeigt Tag und Uhrzeit", () => {
    expect(shortDate("2026-10-20T16:03:23.043272Z")).toMatch(/^20\.10\.2026, \d{2}:03$/)
    expect(shortDate("")).toBe("")
  })

  it("sameUser: nur Ersteller oder Admin dürfen wegwerfen", () => {
    expect(sameUser({ username: "till" }, "till", "user")).toBe(true)
    expect(sameUser({ username: "bibi" }, "till", "user")).toBe(false)
    expect(sameUser({ username: "bibi" }, "till", "admin")).toBe(true)
  })
})
