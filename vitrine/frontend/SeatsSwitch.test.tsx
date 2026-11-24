import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import type { SeatAction, SeatsView } from "./api"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), postForm: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

const { SeatsPanel } = await import("./SeatsCard")
const { runResult, switchAction } = await import("./seats")
const { seatsI18n } = await import("./seatsI18n")

const SAVED = { assignment: { "gpu:pci:x": "seat1" as const }, saved_at: 1 }
const view = (over: Partial<SeatsView> = {}): SeatsView => ({
  devices: { gpus: [], sound: [], inputs: [] }, seats: ["seat0"], feasible: true, reasons: [], monitor_detected: true,
  inputs_unclear: false, assignment: {}, saved: SAVED, saved_error: null, applied: false, running: null, last_run: null, ...over,
})
const html = (v: SeatsView, confirming: SeatAction | null = null) =>
  renderToStaticMarkup(<SeatsPanel v={v} choice={{}} saving={false} msg={null} onPick={() => {}} onSave={() => {}} confirming={confirming} />)
const run = (action: SeatAction, exit: number) => ({ action, started: 1, finished: 2, exit, ok: exit === 0, lines: ["a", "Fehlertext"] })
const msg = (v: SeatsView) => runResult(v)?.msgKey ?? null

describe("Multiseat M2: Zweiten Arbeitsplatz ein-/ausschalten", () => {
  it("einschalten nur mit gespeicherter, gültiger Zuordnung und wenn aus", () => {
    expect(switchAction(view())).toBe("apply")
    expect(html(view())).toContain('data-action="apply"')
    expect(switchAction(view({ saved: null }))).toBeNull()
    expect(switchAction(view({ saved_error: "vitrine_seat_unknown_device" }))).toBeNull()
    const h = html(view({ saved_error: "vitrine_seat_plan_bt_seat1" }))
    expect(h).not.toContain('data-action="apply"')
    expect(h).toContain("vitrine_seat_plan_bt_seat1")
  })

  it("ausschalten nur wenn an – auch wenn der Rechner jetzt nicht mehr „machbar“ aussieht", () => {
    expect(switchAction(view({ applied: true }))).toBe("revert")
    const h = html(view({ applied: true, feasible: false, reasons: ["no_monitor"] }))
    expect(h).toContain('data-action="revert"')
    expect(h).not.toContain('data-action="apply"')
  })

  it("während eines Laufs kein Knopf, aber Laufanzeige", () => {
    for (const r of ["apply", "revert"] as const) {
      const h = html(view({ running: r, applied: r === "revert" }))
      expect(switchAction(view({ running: r }))).toBeNull()
      expect(h).toContain('data-state="running"')
      expect(h).toContain(`seats_running_${r}`)
      expect(h).not.toContain('data-action="apply"')
      expect(h).not.toContain('data-action="revert"')
    }
  })

  it("Bestätigung mit dem verbindlichen Text, Knopf ersetzt", () => {
    const h = html(view(), "apply")
    expect(h).toContain('data-part="confirm"')
    expect(h).toContain("seats_confirm_text")
    expect(h).toContain('data-action="confirm"')
    expect(h).not.toContain('data-action="apply"')
    expect(seatsI18n.de.seats_confirm_text).toBe(
      "Beide Bildschirme werden kurz schwarz. Klappt etwas nicht, nimmt die Vitrine die Umstellung nach spätestens 5 Minuten von selbst zurück.")
  })

  it("Ergebnis aus last_run: ok, zurückgenommen, abgelehnt, Fehler mit Zeilen", () => {
    expect(msg(view({ last_run: run("apply", 0) }))).toBe("seats_run_ok_apply")
    expect(msg(view({ last_run: run("apply", 1) }))).toBe("seats_run_reverted")
    expect(msg(view({ last_run: run("apply", 2) }))).toBe("seats_run_rejected")
    expect(msg(view({ last_run: run("revert", 3) }))).toBe("seats_run_fail_revert")
    expect(runResult(view({ last_run: run("revert", 3), running: "apply" }))).toBeNull()
    const h = html(view({ last_run: run("apply", 1) }))
    expect(h).toContain('data-result="fail"')
    expect(h).toContain("Fehlertext")
  })

  it("Texte: Bluetooth-Code wie vorgegeben, alle Schlüssel de/en", () => {
    expect(seatsI18n.de.vitrine_seat_plan_bt_seat1).toBe("Bluetooth-Geräte hängen am Funkchip des Rechners und bleiben bei der Vitrine.")
    expect(Object.keys(seatsI18n.de).sort()).toEqual(Object.keys(seatsI18n.en).sort())
    for (const k of ["seats_run_ok_apply", "seats_run_ok_revert", "seats_run_reverted", "seats_run_rejected",
      "seats_run_fail_apply", "seats_run_fail_revert", "seats_running_apply", "seats_running_revert"]) expect(seatsI18n.de).toHaveProperty(k)
  })
})
