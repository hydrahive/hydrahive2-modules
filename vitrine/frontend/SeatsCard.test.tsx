import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import type { SeatsView } from "./api"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), postForm: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

const { SeatsPanel } = await import("./SeatsCard")
const { choiceErrors, complete, initialChoice, seatRows } = await import("./seats")
const { seatsI18n } = await import("./seatsI18n")

const AMD = "gpu:pci:0000:0d:00.0", EVDI = "gpu:evdi:evdi.0", NV = "gpu:pci:0000:01:00.0"
const view = (over: Partial<SeatsView> = {}): SeatsView => ({
  devices: {
    gpus: [
      { id: AMD, card: "card0", pci: "0000:0d:00.0", driver: "amdgpu", evdi: false, vendor: "AMD", boot_vga: false, outputs: [] },
      { id: EVDI, card: "card1", pci: null, driver: "evdi", evdi: true, vendor: "evdi", boot_vga: false, outputs: [{ name: "DVI-I-1", connected: true }] },
      { id: NV, card: "card2", pci: "0000:01:00.0", driver: "nvidia", evdi: false, vendor: "NVIDIA", boot_vga: true, outputs: [{ name: "HDMI-A-1", connected: true }] },
    ],
    sound: [{ id: "sound:pci:0000:01:00.1", card: "card0", pci: "0000:01:00.1", name: "NVidia" }],
    inputs: [{ id: "input:usb:1-5", name: "RAPOO", kinds: ["keyboard", "mouse"], usb: "1-5", branch: "1-5", bt: null }],
  },
  seats: ["seat0"], feasible: true, reasons: [], monitor_detected: true, inputs_unclear: true,
  assignment: { [AMD]: "seat0", [EVDI]: "seat0", [NV]: "seat1", "sound:pci:0000:01:00.1": "seat1", "input:usb:1-5": null },
  saved: null, applied: false, ...over,
})
const html = (v: SeatsView, choice = initialChoice(v)) =>
  renderToStaticMarkup(<SeatsPanel v={v} choice={choice} saving={false} msg={null} onPick={() => {}} onSave={() => {}} />)

describe("Karte „Zweiter Arbeitsplatz“ (Multiseat M1)", () => {
  it("Hinweis „Zweiter Bildschirm erkannt“ nur bei monitor_detected", () => {
    expect(html(view())).toContain('data-hint="monitor"')
    expect(html(view({ monitor_detected: false }))).not.toContain('data-hint="monitor"')
  })

  it("Vorschlag als Liste mit lesbaren Namen und Auswahl je Gerät", () => {
    const h = html(view())
    for (const id of [AMD, EVDI, NV, "input:usb:1-5"]) expect(h).toContain(`data-device="${id}"`)
    expect(h).toContain("NVIDIA 0000:01:00.0")
    expect(h).toContain("HDMI-A-1")
    expect(h).toContain("USB-Display (EVDI)")
  })

  it("Eingabe unklar: Feld bleibt leer, „Übernehmen“ gesperrt bis zugeordnet", () => {
    const v = view()
    const c = initialChoice(v)
    expect(c["input:usb:1-5"]).toBeNull()
    expect(choiceErrors(v, c)).toContain("seats_err_open")
    expect(html(v)).toMatch(/disabled=""[^>]*data-action="apply"/)
    const ok = { ...c, "input:usb:1-5": "seat1" as const }
    expect(choiceErrors(v, ok)).toEqual([])
    expect(complete(ok)["input:usb:1-5"]).toBe("seat1")
  })

  it("Prüfung wie im Backend: USB-Display bleibt Vitrine, je Arbeitsplatz eine Grafikkarte", () => {
    const v = view()
    const c = { ...initialChoice(v), "input:usb:1-5": "seat1" as const }
    expect(choiceErrors(v, { ...c, [EVDI]: "seat1" })).toContain("seats_err_evdi")
    expect(choiceErrors(v, { ...c, [NV]: "seat0" })).toContain("seats_err_gpu")
  })

  it("gespeicherte Zuordnung geht vor dem Vorschlag", () => {
    const v = view({ saved: { assignment: { [AMD]: "seat0", [EVDI]: "seat0", [NV]: "seat1", "sound:pci:0000:01:00.1": "seat0", "input:usb:1-5": "seat1" }, saved_at: 1 } })
    expect(initialChoice(v)["sound:pci:0000:01:00.1"]).toBe("seat0")
    expect(initialChoice(v)["input:usb:1-5"]).toBe("seat1")
  })

  it("nicht machbar: Gründe statt Auswahl, kein „Übernehmen“", () => {
    const h = html(view({ feasible: false, reasons: ["one_gpu"], assignment: {} }))
    expect(h).toContain('data-part="not-feasible"')
    expect(h).toContain("seats_reason_one_gpu")
    expect(h).not.toContain('data-action="apply"')
  })

  it("ehrlicher Hinweis „Umschalten kommt im nächsten Schritt“ immer sichtbar", () => {
    expect(html(view())).toContain('data-hint="later"')
    expect(seatsI18n.de.seats_later).toContain("Umschalten kommt im nächsten Schritt")
    expect(seatsI18n.de.seats_monitor_hint).toBe("Zweiter Bildschirm erkannt – als eigenen Arbeitsplatz einrichten?")
  })

  it("Texte de/en mit gleichen Schlüsseln, Gründe des Backends alle übersetzt", () => {
    expect(Object.keys(seatsI18n.de).sort()).toEqual(Object.keys(seatsI18n.en).sort())
    for (const r of ["no_evdi", "one_gpu", "no_monitor", "gpu_unclear"]) expect(seatsI18n.de).toHaveProperty(`seats_reason_${r}`)
    expect(seatRows(view())).toHaveLength(5)
  })
})
