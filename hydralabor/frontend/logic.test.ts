import { describe, expect, it } from "vitest"
import { hydralaborI18n } from "./i18n"
import { CREATE_STEPS, errorKey, limitsError, progressOf, testLine, type LabState } from "./logic"

/** Alle Fehlercodes, die das Backend schickt. */
function backendCodes(): string[] {
  const src = Object.values(import.meta.glob("../backend/*.py", { query: "?raw", import: "default", eager: true })).join("\n")
  return [...new Set([...src.matchAll(/"(labor_[a-z_]+)"/g)].map((m) => m[1]))].sort()
}

const S: LabState = {
  step: "start", running: "", progress: "", error_code: "", error_step: "", model: "", cpu: 2, ram_mb: 4096, disk_gb: 20,
  last_net_ok: "", last_test: {}, project_id: "", agent_id: "", container_running: false,
}

describe("Hydra-Labor: Logik", () => {
  it("jeder Fehlercode des Backends hat einen Text (de/en)", () => {
    const codes = backendCodes()
    for (const c of ["labor_net_open", "labor_busy", "labor_not_ready", "labor_interrupted"]) expect(codes).toContain(c)
    for (const lang of ["de", "en"] as const) {
      const err = hydralaborI18n[lang].hydralabor.err as Record<string, string>
      expect(codes.filter((c) => !err[c]), lang).toEqual([])
    }
  })

  it("Texte ohne Fachbegriffe, beide Sprachen gleich vollständig", () => {
    const flat = (o: unknown, p = ""): string[] => typeof o === "string" ? [p] : Object.entries(o as object).flatMap(([k, v]) => flat(v, p ? `${p}.${k}` : k))
    expect(flat(hydralaborI18n.de).sort()).toEqual(flat(hydralaborI18n.en).sort())
    const texts = (o: unknown): string[] => typeof o === "string" ? [o] : Object.values(o as object).flatMap(texts)
    for (const txt of texts(hydralaborI18n.de)) expect(txt).not.toMatch(/incus|ACL|snapshot|sudo|terminal|\.py|apt-get|bridge|\bNAT\b/i)
  })

  it("errorKey: Code aus Antwort oder Zustand, sonst allgemein", () => {
    expect(errorKey(Object.assign(new Error("x"), { code: "labor_busy" }))).toBe("err.labor_busy")
    expect(errorKey("labor_net_open")).toBe("err.labor_net_open")
    expect(errorKey(Object.assign(new Error("x"), { code: "admin_only" }))).toBe("err.admin_only")
    expect(errorKey(Object.assign(new Error("x"), { code: "irgendwas" }))).toBe("err.general")
    expect(errorKey(undefined)).toBe("err.general")
  })

  it("Fortschritt beim Anlegen: Schritt und Prozent", () => {
    expect(CREATE_STEPS[0]).toBe("network")
    expect(CREATE_STEPS.at(-1)).toBe("project")
    expect(progressOf({ ...S, running: "create", progress: "network" })).toEqual({ index: 0, pct: 0 })
    const last = progressOf({ ...S, running: "create", progress: "project" })
    expect(last.index).toBe(CREATE_STEPS.length - 1)
    expect(last.pct).toBeGreaterThan(80)
    expect(progressOf({ ...S, running: "create", progress: "frontend" }).index).toBe(CREATE_STEPS.indexOf("frontend"))
    expect(progressOf({ ...S, running: "create", progress: "" })).toEqual({ index: 0, pct: 0 })
    expect(progressOf({ ...S, running: "", progress: "" })).toEqual({ index: -1, pct: 0 })
  })

  it("Grenzen prüfen wie das Backend", () => {
    expect(limitsError({ cpu: 2, ram_mb: 4096, disk_gb: 20 })).toBe("")
    expect(limitsError({ cpu: 1, ram_mb: 1024, disk_gb: 10 })).toBe("")
    expect(limitsError({ cpu: 64, ram_mb: 262144, disk_gb: 2000 })).toBe("")
    for (const bad of [{ cpu: 0, ram_mb: 4096, disk_gb: 20 }, { cpu: 65, ram_mb: 4096, disk_gb: 20 },
      { cpu: 2, ram_mb: 1023, disk_gb: 20 }, { cpu: 2, ram_mb: 4096, disk_gb: 9 }, { cpu: 2.5, ram_mb: 4096, disk_gb: 20 },
      { cpu: 2, ram_mb: 4096, disk_gb: 2001 }, { cpu: 2, ram_mb: 262145, disk_gb: 20 }])
      expect(limitsError(bad), JSON.stringify(bad)).toBe("err.labor_limits_invalid")
  })

  it("Testlauf in einer Zeile", () => {
    expect(testLine({})).toBeNull()
    expect(testLine({ ok: true, passed: 5241, failed: 0, summary: "5241 passed in 274s", failures: [], at: "x" }))
      .toEqual({ key: "test.green", passed: 5241, failed: 0 })
    expect(testLine({ ok: false, passed: 5239, failed: 2, summary: "2 failed", failures: ["a"], at: "x" }))
      .toEqual({ key: "test.red", passed: 5239, failed: 2 })
    expect(testLine({ ok: false, passed: 0, failed: 0, summary: "", failures: [], at: "x" }))
      .toEqual({ key: "test.broken", passed: 0, failed: 0 })
  })
})
