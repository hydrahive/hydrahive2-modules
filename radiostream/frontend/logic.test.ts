import { describe, expect, it } from "vitest"
import { radiostreamI18n } from "./i18n"
import { audioUrl, errorKey, fmtDuration, fmtTotal, isSmbUrl, matchCredential, scanLabel, tracksQuery, type Filter } from "./logic"

/** Alle Fehlercodes, die das Backend schickt (coded + KNOWN). */
function backendCodes(): string[] {
  const src = Object.values(import.meta.glob("../backend/*.py", { query: "?raw", import: "default", eager: true })).join("\n")
  return [...new Set([...src.matchAll(/"(radiostream_[a-z_]+)"/g)].map((m) => m[1]))].filter((c) => c !== "radiostream_scan").sort()
}

const F: Filter = { q: "", genre: "", decade: "", format: "", missing: false }

describe("Radiostream: Logik (Etappe 1)", () => {
  it("jeder Fehlercode des Backends hat einen Text (de/en)", () => {
    const codes = backendCodes()
    for (const c of ["radiostream_not_configured", "radiostream_auth_failed", "radiostream_admin_only"]) expect(codes).toContain(c)
    for (const lang of ["de", "en"] as const) {
      const err = (radiostreamI18n[lang].radiostream as unknown as { err: Record<string, string> }).err
      expect(codes.filter((c) => !err[c]), lang).toEqual([])
    }
  })

  it("errorKey: bekannte Codes, sonst allgemein", () => {
    expect(errorKey(Object.assign(new Error("x"), { code: "radiostream_auth_failed" }))).toBe("err.radiostream_auth_failed")
    expect(errorKey(Object.assign(new Error("x"), { code: "irgendwas" }))).toBe("err.general")
    expect(errorKey("kaputt")).toBe("err.general")
  })

  it("Texte ohne Terminal- oder Datei-Hinweise, beide Sprachen gleich vollständig", () => {
    const flat = (o: unknown, p = ""): string[] => typeof o === "string" ? [p] : Object.entries(o as object).flatMap(([k, v]) => flat(v, p ? `${p}.${k}` : k))
    expect(flat(radiostreamI18n.de).sort()).toEqual(flat(radiostreamI18n.en).sort())
    const txt = JSON.stringify(radiostreamI18n)
    expect(txt).not.toMatch(/terminal|sudo|\.json|\.py|apt-get/i)
  })

  it("Abfrage der Titelliste", () => {
    expect(tracksQuery(F, "")).toBe("/modules/radiostream/tracks?limit=200")
    expect(tracksQuery({ ...F, q: "  queen ", genre: "Rock", decade: "1990", format: "flac" }, "abc"))
      .toBe("/modules/radiostream/tracks?limit=200&q=queen&genre=Rock&year_from=1990&year_to=1999&format=flac&cursor=abc")
    expect(tracksQuery({ ...F, missing: true }, "")).toBe("/modules/radiostream/tracks?limit=200&state=missing")
  })

  it("Adresse der Musikquelle prüfen", () => {
    expect(isSmbUrl("smb://molkewolke.local/Plex_Musik/")).toBe(true)
    expect(isSmbUrl("smb://nas/Musik/Rock")).toBe(true)
    for (const bad of ["", "http://nas/x", "smb://", "smb://nas", "smb://nas/../x", "smb://na s/x"]) expect(isSmbUrl(bad), bad).toBe(false)
  })

  it("Zeiten lesbar", () => {
    expect(fmtDuration(0)).toBe("0:00")
    expect(fmtDuration(65.4)).toBe("1:05")
    expect(fmtDuration(3725)).toBe("1:02:05")
    expect(fmtDuration(null)).toBe("–")
    expect(fmtTotal(3600 * 24 * 3 + 3600 * 5 + 60 * 7)).toEqual({ days: 3, hours: 5 })
  })

  it("Stand des Einlesens in Worten", () => {
    expect(scanLabel({ running: true, done: 30, todo: 120, files_seen: 500, eta_s: 125 })).toEqual({ key: "scan.running", pct: 25, eta_min: 3 })
    expect(scanLabel({ running: true, done: 0, todo: 0, files_seen: 40, eta_s: null })).toEqual({ key: "scan.listing", pct: null, eta_min: null })
    expect(scanLabel({ running: false, done: 0, todo: 0, files_seen: 0, eta_s: null })).toEqual({ key: "scan.idle", pct: null, eta_min: null })
    // Abgebrochen (z. B. Neustart mittendrin): klar sagen statt „Bereit“ – Befund Hauptserver 29.10.2026
    expect(scanLabel({ running: false, done: 0, todo: 0, files_seen: 0, eta_s: null }, "radiostream_scan_interrupted"))
      .toEqual({ key: "scan.interrupted", pct: null, eta_min: null })
    expect(scanLabel({ running: true, done: 30, todo: 120, files_seen: 500, eta_s: 125 }, "radiostream_scan_interrupted"))
      .toEqual({ key: "scan.running", pct: 25, eta_min: 3 })
    expect(scanLabel({ running: false, done: 0, todo: 0, files_seen: 0, eta_s: null }, "radiostream_auth_failed"))
      .toEqual({ key: "scan.idle", pct: null, eta_min: null })
  })

  it("Vorhören mit Anmeldung über ?token= (der Player kann keinen Kopf senden)", () => {
    expect(audioUrl("t_abc", "tok en")).toBe("/api/modules/radiostream/tracks/t_abc/audio?token=tok%20en")
  })

  it("passenden Safe-Eintrag zur Adresse finden", () => {
    const c = [{ name: "nasbackup", url_pattern: "smb://192.168.178.2" }, { name: "plexmusik", url_pattern: "smb://molkewolke.local/Plex_Musik/" }]
    expect(matchCredential(c, "smb://molkewolke.local/Plex_Musik")).toBe("plexmusik")
    expect(matchCredential(c, "SMB://MolkeWolke.local/Plex_Musik/")).toBe("plexmusik")
    expect(matchCredential(c, "smb://anderer/x")).toBeNull()
    expect(matchCredential(c, "")).toBeNull()
  })
})
