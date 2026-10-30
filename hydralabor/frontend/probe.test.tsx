import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn() } }))
import { ProbeBoxView } from "./ProbeBox"
import { probeView, PROBE_JOBS, type ProbeState } from "./probeLogic"
import { errorKey } from "./logic"
import { hydralaborI18n } from "./i18n"

const noop = () => {}
const P = (o: Partial<ProbeState> = {}): ProbeState =>
  ({ built: false, running: false, user: "admin", password: "", port: 8443, open: false, ...o })
const view = (p: ProbeState, o: { job?: string; busy?: boolean; container?: boolean } = {}) =>
  renderToStaticMarkup(<ProbeBoxView p={p} job={o.job ?? ""} busy={o.busy ?? false} containerRunning={o.container ?? true}
    onBuild={noop} onStart={noop} onStop={noop} onOpen={noop} />)

describe("probeView", () => {
  it("nicht gebaut → bauen", () => { expect(probeView(P(), "")).toBe("unbuilt") })
  it("gebaut, aus → starten", () => { expect(probeView(P({ built: true }), "")).toBe("stopped") })
  it("läuft + nginx → offen", () => { expect(probeView(P({ built: true, running: true, open: true }), "")).toBe("open") })
  it("läuft ohne nginx → halb (stoppen, neu starten)", () => {
    expect(probeView(P({ built: true, running: true }), "")).toBe("stopped")
  })
  it("Auftrag der Probe läuft → busy", () => {
    for (const j of PROBE_JOBS) expect(probeView(P({ built: true }), j)).toBe("busy")
  })
  it("anderer Auftrag → kein busy", () => { expect(probeView(P(), "test")).toBe("unbuilt") })
})

describe("Kasten Probe", () => {
  it("nicht gebaut: Bauen-Knopf, kein Öffnen, kein Passwort", () => {
    const html = view(P())
    expect(html).toContain("probe.build")
    expect(html).not.toContain("probe.open")
    expect(html).not.toContain("probe.password")
  })

  it("gebaut: Starten + neu bauen, kein Öffnen", () => {
    const html = view(P({ built: true }))
    expect(html).toContain("probe.start")
    expect(html).toContain("probe.rebuild")
    expect(html).not.toContain("probe.open")
  })

  it("offen: Öffnen als Hauptknopf, Stoppen, Zugangsdaten", () => {
    const html = view(P({ built: true, running: true, open: true, password: "Abc_12345" }))
    expect(html).toMatch(/bg-emerald-600[^>]*>probe.open</)
    expect(html).toContain("probe.stop")
    expect(html).toContain("Abc_12345")
    expect(html).toContain("probe.login_hint")
  })

  it("Passwort wählbar zum Kopieren und mit Kopierknopf", () => {
    const html = view(P({ built: true, running: true, open: true, password: "Abc_12345" }))
    expect(html).toMatch(/select-all[^>]*>Abc_12345</)
    expect(html).toContain("probe.copy")
  })

  it("läuft gerade: Text zum Auftrag, alle Knöpfe gesperrt", () => {
    const html = view(P({ built: true }), { job: "probe_build" })
    expect(html).toContain("job.probe_build")
    expect(html).not.toMatch(/<button(?![^>]*disabled)/)
  })

  it("anderer Auftrag läuft: Knöpfe gesperrt", () => {
    const html = view(P({ built: true }), { job: "test" })
    expect(html).not.toMatch(/<button(?![^>]*disabled)/)
  })

  it("busy (Klick unterwegs): Knöpfe gesperrt", () => {
    expect(view(P({ built: true, running: true, open: true }), { busy: true })).not.toMatch(/<button(?![^>]*disabled)/)
  })

  it("Labor aus: Hinweis, keine Knöpfe frei", () => {
    const html = view(P(), { container: false })
    expect(html).toContain("probe.lab_off")
    expect(html).not.toMatch(/<button(?![^>]*disabled)/)
  })

  it("Erklärung immer da (eigene Anmeldung, Heimnetz)", () => {
    expect(view(P())).toContain("probe.intro")
  })

  it("Port wird genannt", () => {
    expect(view(P({ built: true, running: true, open: true }))).toContain('probe.where:{&quot;port&quot;:8443}')
  })
})

describe("Texte", () => {
  const de = hydralaborI18n.de.hydralabor as unknown as Record<string, Record<string, string>>
  const en = hydralaborI18n.en.hydralabor as unknown as Record<string, Record<string, string>>
  const keys = ["intro", "build", "rebuild", "start", "stop", "open", "copy", "login_hint", "where", "lab_off", "title",
    "user", "password"]
  it("Kasten de/en vollständig", () => {
    for (const k of keys) { expect(de.probe[k], k).toBeTruthy(); expect(en.probe[k], k).toBeTruthy() }
  })
  it("Aufträge de/en", () => {
    for (const j of PROBE_JOBS) { expect(de.job[j], j).toBeTruthy(); expect(en.job[j], j).toBeTruthy() }
  })
  it("Fehler bekannt und de/en", () => {
    for (const c of ["labor_probe_build_failed", "labor_probe_not_built", "labor_probe_start_failed",
      "labor_probe_nginx_failed", "labor_probe_no_address", "labor_probe_bad_host", "labor_probe_login_required"]) {
      expect(errorKey(c)).toBe(`err.${c}`)
      expect(de.err[c], c).toBeTruthy(); expect(en.err[c], c).toBeTruthy()
    }
  })
  it("keine Hinweise auf Terminal/Dateien", () => {
    const all = JSON.stringify([de.probe, en.probe])
    expect(all).not.toMatch(/terminal|nginx|\.conf|sudo|systemd|Datei|file/i)
  })
})
