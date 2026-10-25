import { describe, expect, it } from "vitest"
import { DEFAULTS, canSave, errorKey, formFrom, isDirty, toneOf } from "./connectionLogic"
import type { Connection } from "./types"

const SAVED: Connection = {
  configured: true, has_password: true, enabled: true, status: "registered", status_at: null,
  created_at: "", updated_at: "", pbx: "fritzbox", display_name: "Büro", registrar: "192.168.178.1",
  registrar_port: 5060, username: "hydra-telefon", own_number: "030 1", local_sip_port: 5070,
  rtp_port_min: 7078, rtp_port_max: 7109, register_interval: 300,
}

describe("Formular", () => {
  it("leer: FRITZ!Box-Standardwerte", () => {
    expect(formFrom(null)).toEqual(DEFAULTS)
    expect(formFrom({ configured: false, status: "not_configured" })).toEqual(DEFAULTS)
    expect(DEFAULTS.registrar).toBe("fritz.box")
  })
  it("gespeichert: Felder übernommen, Kennwort leer", () => {
    const f = formFrom(SAVED)
    expect(f.registrar).toBe("192.168.178.1")
    expect(f.display_name).toBe("Büro")
    expect(f.password).toBe("")
    expect(f).not.toHaveProperty("status")
  })
})

describe("Speichern erlaubt", () => {
  const ok = { ...DEFAULTS, username: "hydra-telefon", password: "Sehr-Geheim-42" }
  it("neu: Kennwort Pflicht", () => {
    expect(canSave(ok, false)).toBe(true)
    expect(canSave({ ...ok, password: "" }, false)).toBe(false)
  })
  it("gespeichert: Kennwort darf leer bleiben", () => {
    expect(canSave({ ...ok, password: "" }, true)).toBe(true)
  })
  it("FRITZ!Box: mindestens 8 Zeichen", () => {
    expect(canSave({ ...ok, username: "kurz" }, false)).toBe(false)
    expect(canSave({ ...ok, password: "kurz" }, false)).toBe(false)
  })
  it("andere Anlage: kurze Werte erlaubt", () => {
    expect(canSave({ ...ok, pbx: "sip", username: "1001", password: "1234" }, false)).toBe(true)
  })
  it("Adresse Pflicht", () => {
    expect(canSave({ ...ok, registrar: " " }, false)).toBe(false)
  })
})

describe("geändert", () => {
  it("unverändert / Feld / Kennwort", () => {
    expect(isDirty(formFrom(SAVED), SAVED)).toBe(false)
    expect(isDirty({ ...formFrom(SAVED), own_number: "030 2" }, SAVED)).toBe(true)
    expect(isDirty({ ...formFrom(SAVED), password: "neu-neu-neu" }, SAVED)).toBe(true)
  })
})

describe("Status-Farbe", () => {
  it.each([
    ["registered", "ok"], ["connecting", "busy"], ["unreachable", "warn"], ["rejected", "warn"],
    ["disconnected", "idle"], ["not_configured", "idle"], ["auth_failed", "error"], ["blocked", "error"],
    ["port_in_use", "error"], ["not_found", "error"], ["secret_invalid", "error"],
  ] as const)("%s → %s", (s, tone) => expect(toneOf(s)).toBe(tone))
})

describe("Fehlercodes", () => {
  it("bekannte bleiben, Rest unknown", () => {
    expect(errorKey("blocked")).toBe("blocked")
    expect(errorKey("port_taken")).toBe("port_taken")
    expect(errorKey("irgendwas")).toBe("unknown")
    expect(errorKey(undefined)).toBe("unknown")
  })
})
