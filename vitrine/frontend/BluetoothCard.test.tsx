import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

const del = vi.fn(async () => undefined)
const post = vi.fn(async () => ({ started: true }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post, put: vi.fn(), delete: del, postForm: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))

const { BluetoothList } = await import("./BluetoothList")
const { vitrineApi } = await import("./api")
import type { BtDevice, BtView } from "./api"

const RAPOO: BtDevice = { name: "RAPOO KB", addresses: ["B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"], kind: "keyboard", rssi: -56, bars: 4,
  paired: true, connected: true, more: false }
const MAUS: BtDevice = { name: "MX Anywhere", addresses: ["C0:11:22:33:44:55"], kind: "mouse", rssi: -70, bars: 3, paired: false,
  connected: false, more: false }
const FERN: BtDevice = { name: "Unbekanntes Gerät", addresses: ["66:DD:27:7F:DB:9A"], kind: "other", rssi: -95, bars: 1, paired: false,
  connected: false, more: true }
const view = (over: Partial<BtView> = {}): BtView => ({ available: true, adapter: { name: "hydrahive-master", powered: true },
  window_left: 0, devices: [RAPOO, MAUS, FERN], weak_signal: false, pairing: null, error: null, ...over })
const html = (v: BtView) => renderToStaticMarkup(<BluetoothList v={v} onScan={() => {}} onPair={() => {}} onRemove={() => {}} />)

describe("Bluetooth-Karte (S7)", () => {
  it("Entfernen nur bei gekoppelten Geräten, Adapter steht oben", () => {
    const h = html(view())
    expect(h.match(/data-bt-remove=/g)).toHaveLength(1)
    expect(h).toContain('data-bt-remove="B4:EE:25:ED:70:7F"')
    expect(h).toContain("hydrahive-master")
  })

  it("ohne offenes Fenster: kein Koppeln-Knopf an neuen Geräten, Knopf „Gerät koppeln“ aktiv", () => {
    const h = html(view())
    expect(h).not.toContain("data-bt-pair=")
    expect(h).toContain('data-bt-scan="1" class=')
    expect(h).not.toContain('data-bt-scan="1" disabled=""')
  })

  it("offenes Fenster: Restzeit, neue Geräte koppelbar, weitere Geräte zugeklappt", () => {
    const h = html(view({ window_left: 87 }))
    expect(h).toContain("bt_window_left:{&quot;s&quot;:87}")
    expect(h).toContain('data-bt-scan="1" disabled=""')
    expect(h).toContain('data-bt-pair="C0:11:22:33:44:55"')
    expect(h).not.toContain('data-bt-pair="B4:EE:25:ED:70:7F"')
    expect(h).toMatch(/<details[^>]*>(?:(?!<\/details>).)*66:DD:27:7F:DB:9A/s)
    expect(h.split("<details")[0]).not.toContain("66:DD:27:7F:DB:9A")
  })

  it("Code groß, schwaches Signal und Fehler als Hinweis", () => {
    const h = html(view({ window_left: 50, pairing: { address: "C0:11:22:33:44:55", passkey: "042137" }, weak_signal: true,
      error: "MX nicht gekoppelt: org.bluez.Error.AuthenticationFailed" }))
    expect(h).toContain("042137")
    expect(h).toContain("bt_weak")
    expect(h).toContain("AuthenticationFailed")
  })

  it("Dienst nicht verfügbar → Hinweis statt Liste", () => {
    const h = html(view({ available: false, devices: [] }))
    expect(h).toContain("bt_unavailable")
    expect(h).not.toContain("data-bt-scan")
  })

  it("Namen nur als Text, nie als HTML", () => {
    const h = html(view({ devices: [{ ...MAUS, name: "<img src=x onerror=alert(1)>" }] }))
    expect(h).not.toContain("<img")
  })

  it("API: Entfernen ruft DELETE mit Adresse, Koppeln POST pair", async () => {
    await vitrineApi.btRemove("B4:EE:25:ED:70:7F")
    expect(del).toHaveBeenCalledWith("/modules/vitrine/bluetooth/B4%3AEE%3A25%3AED%3A70%3A7F")
    await vitrineApi.btPair("C0:11:22:33:44:55")
    expect(post).toHaveBeenCalledWith("/modules/vitrine/bluetooth/pair", { address: "C0:11:22:33:44:55" })
    await vitrineApi.btScan()
    expect(post).toHaveBeenCalledWith("/modules/vitrine/bluetooth/scan", {})
  })
})
