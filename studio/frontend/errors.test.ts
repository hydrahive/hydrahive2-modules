import { describe, expect, it } from "vitest"
import { studioI18n } from "./i18n"
import { errorCode, errorText } from "./planLogic"

/** Alle Fehlercodes, die das Backend an die Oberfläche schickt (PlanError, Rejected, coded, busy_code). */
function backendCodes(): string[] {
  const src = Object.values(import.meta.glob("../backend/*.py", { query: "?raw", import: "default", eager: true })).join("\n")
  const re = /(?:PlanError|Rejected|coded|__init__)\((?:\d+,\s*)?"(studio_[a-z_]+)"|busy_code="(studio_[a-z_]+)"/g
  return [...new Set([...src.matchAll(re)].map((m) => m[1] ?? m[2]))].sort()
}

describe("Fehlermeldungen: jeder Code des Backends wird verständlich angezeigt", () => {
  it("findet die Codes (Stichprobe aus mehreren Etappen)", () => {
    const codes = backendCodes()
    for (const c of ["studio_not_found", "studio_music_running", "studio_upload_too_many", "studio_subtitles_running", "studio_render_bad_preset",
      "studio_timeline_invalid", "studio_subtitles_invalid", "studio_media_not_found"]) expect(codes).toContain(c)
    expect(codes.length).toBeGreaterThan(40)
  })

  it("de/en: es gibt einen Text unter err.<code>", () => {
    for (const lang of ["de", "en"] as const) {
      const err = (studioI18n[lang].studio as unknown as { err: Record<string, string> }).err
      expect(backendCodes().filter((c) => !err[c]), lang).toEqual([])
    }
  })

  it("errorCode erkennt jeden Code, errorText zeigt den Text statt des rohen Codes", () => {
    const t = (k: string) => `T:${k}`
    for (const c of backendCodes()) {
      const e = Object.assign(new Error(c), { code: c })                              // Kern-Client: unbekannter Code → Meldung = Code
      expect(errorCode(e), c).toBe(c)
      expect(errorText(t, e), c).toBe(`T:err.${c}`)
    }
    expect(errorCode(Object.assign(new Error("x"), { code: "fremd_code" }))).toBeNull()
    expect(errorText(t, new Error("Netz weg"))).toBe("Netz weg")
  })
})
