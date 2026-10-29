import { describe, expect, it } from "vitest"
import { BASE, ERROR_CODES, errorKey, isLocalAddress, stepVolume } from "./logic"

describe("Fernseher – Hilfsfunktionen", () => {
  it("bekannte Fehlercodes werden zu err.<code>, alles andere zu err.general", () => {
    expect(errorKey(Object.assign(new Error("x"), { code: "tv_needs_restart" }))).toBe("err.tv_needs_restart")
    expect(errorKey(Object.assign(new Error("x"), { code: "irgendwas" }))).toBe("err.general")
    expect(errorKey("kaputt")).toBe("err.general")
    expect(errorKey(null)).toBe("err.general")
  })

  it("kennt alle Codes des Backends", () => {
    expect([...ERROR_CODES].sort()).toEqual([
      "tv_address_not_local", "tv_app_unknown", "tv_auth_failed", "tv_channel_ambiguous", "tv_channel_unknown",
      "tv_needs_restart", "tv_not_configured", "tv_psk_missing", "tv_settings_invalid", "tv_unreachable",
      "tv_upstream_error", "tv_volume_invalid", "tv_volume_limit",
    ])
  })

  it("Heimnetz-Adresse vorab prüfen (wie das Backend, nur als Hinweis)", () => {
    for (const ok of ["192.168.178.186", "10.0.0.5", "172.20.1.1", "bravia", "tv.local", "tv.fritz.box"])
      expect(isLocalAddress(ok)).toBe(true)
    for (const bad of ["8.8.8.8", "example.com", "127.0.0.1", "localhost", "", "http://192.168.1.5", "192.168.1.5:80",
      "172.32.0.1", "192.168.1.256"])
      expect(isLocalAddress(bad)).toBe(false)
  })

  it("Lautstärke-Schritte als Befehl", () => {
    expect(stepVolume(+1)).toBe("+1")
    expect(stepVolume(-5)).toBe("-5")
    expect(stepVolume(0)).toBe("+0")
  })

  it("Grundpfad", () => expect(BASE).toBe("/modules/fernseher"))
})
