import { describe, expect, it } from "vitest"
import { tvwerkstattI18n } from "./i18n"
import { deviceLine, errorKey } from "./logic"

/** Alle Fehlercodes, die das Backend schickt. */
function backendCodes(): string[] {
  const files = import.meta.glob("../backend/*.py", { query: "?raw", import: "default", eager: true })
  const src = Object.values(files).join("\n")
  return [...new Set([...src.matchAll(/"(tvw_[a-z_]+)"/g)].map((m) => m[1]))].sort()
}

describe("TV-Werkstatt: Logik", () => {
  it("jeder Fehlercode des Backends hat einen Text (de/en)", () => {
    const codes = backendCodes()
    expect(codes).toContain("tvw_no_incus")
    for (const lang of ["de", "en"] as const) {
      const err = tvwerkstattI18n[lang].tvwerkstatt.err as Record<string, string>
      expect(codes.filter((c) => !err[c]), lang).toEqual([])
    }
  })

  it("beide Sprachen gleich vollständig, keine Fachbegriffe des Servers", () => {
    const flat = (o: unknown, p = ""): string[] => typeof o === "string" ? [p]
      : Object.entries(o as object).flatMap(([k, v]) => flat(v, p ? `${p}.${k}` : k))
    expect(flat(tvwerkstattI18n.de).sort()).toEqual(flat(tvwerkstattI18n.en).sort())
    const texts = (o: unknown): string[] => typeof o === "string" ? [o] : Object.values(o as object).flatMap(texts)
    for (const txt of texts(tvwerkstattI18n.de)) expect(txt).not.toMatch(/incus|ACL|sudo|\.py|apt-get|gradle|\bNAT\b/i)
  })

  it("errorKey: Code aus Antwort oder Zustand, sonst allgemein", () => {
    expect(errorKey(Object.assign(new Error("x"), { code: "tvw_no_incus" }))).toBe("err.tvw_no_incus")
    expect(errorKey("tvw_no_incus")).toBe("err.tvw_no_incus")
    expect(errorKey({ detail: { code: "tvw_no_incus" } })).toBe("err.tvw_no_incus")
    expect(errorKey(Object.assign(new Error("x"), { code: "irgendwas" }))).toBe("err.general")
    expect(errorKey(undefined)).toBe("err.general")
  })

  it("deviceLine: Modell und System, fehlende Angaben lassen sich weg", () => {
    expect(deviceLine({ model: "KD-60XF8305", android: "9" })).toBe("KD-60XF8305 · Android 9")
    expect(deviceLine({ model: "", android: "14" })).toBe("Android 14")
    expect(deviceLine({ model: "KD-60XF8305", android: "" })).toBe("KD-60XF8305")
    expect(deviceLine({ model: "", android: "" })).toBe("")
  })
})
