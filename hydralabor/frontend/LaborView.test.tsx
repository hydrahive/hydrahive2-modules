import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn() } }))
import { LabPanel } from "./LabPanel"
import { RemoveDialogView } from "./RemoveDialog"
import { WizardView } from "./Wizard"
import { canRemove, type Checks, type LabState } from "./logic"

const S: LabState = {
  step: "start", running: "", progress: "", error_code: "", error_step: "", model: "", cpu: 2, ram_mb: 4096, disk_gb: 20,
  last_net_ok: "", last_test: {}, project_id: "", agent_id: "", container_running: false,
}
const OK: Checks = { ok: true, checks: [{ id: "incus", ok: true, code: "", have: null, need: null },
  { id: "storage", ok: true, code: "", have: 500, need: 30 }] }
const noop = () => {}
const wiz = (p: Partial<Parameters<typeof WizardView>[0]>) => renderToStaticMarkup(<WizardView s={S} checks={null}
  models={[{ id: "a/m1", label: "M1", provider: "a" }]} model="" limits={{ cpu: 2, ram_mb: 4096, disk_gb: 20 }}
  busy={false} msg={null} onCheck={noop} onModel={noop} onLimits={noop} onCreate={noop} {...p} />)

describe("Assistent", () => {
  it("Start: Voraussetzungen prüfen, Anlegen noch gesperrt", () => {
    const html = wiz({})
    expect(html).toContain("wizard.check")
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>wizard.create</)
  })

  it("Voraussetzungen grün + Modell gewählt → Anlegen frei, Grenzen sichtbar", () => {
    const html = wiz({ checks: OK, model: "a/m1" })
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>wizard.create</)
    for (const k of ["check.incus", "check.storage", "wizard.cpu", "wizard.ram", "wizard.disk", "M1"]) expect(html).toContain(k)
  })

  it("ohne Modell kein Anlegen, auch wenn alles grün ist", () => {
    expect(wiz({ checks: OK, model: "" })).toMatch(/<button[^>]*disabled=""[^>]*>wizard.create</)
  })

  it("Voraussetzung rot: Grund steht da, Anlegen gesperrt", () => {
    const bad: Checks = { ok: false, checks: [{ id: "memory", ok: false, code: "labor_memory_low", have: 2000, need: 4096 }] }
    const html = wiz({ checks: bad, model: "a/m1" })
    expect(html).toContain("err.labor_memory_low")
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>wizard.create</)
  })

  it("läuft: Fortschritt mit Schritt, kein Anlegen-Knopf", () => {
    const html = wiz({ s: { ...S, running: "create", progress: "python" }, checks: OK, model: "a/m1" })
    expect(html).toContain("progress.python")
    expect(html).toContain('role="progressbar"')
    expect(html).not.toContain(">wizard.create<")
  })

  it("gescheitert: Fehler mit Schritt, erneut versuchen", () => {
    const html = wiz({ s: { ...S, error_code: "labor_setup_failed", error_step: "node" }, checks: OK, model: "a/m1" })
    expect(html).toContain("err.labor_setup_failed")
    expect(html).toContain("progress.node")
    expect(html).toContain("wizard.retry")
  })
})

const READY: LabState = { ...S, step: "ready", container_running: true, last_net_ok: "2026-10-30T15:00:00Z",
  project_id: "p1", agent_id: "a1" }
const panel = (s: Partial<LabState>) => renderToStaticMarkup(<LabPanel s={{ ...READY, ...s }} busy={false} msg={null}
  onJob={noop} onPower={noop} onAskReset={noop} onAskRemove={noop} />)

describe("Labor-Seite", () => {
  it("fertig: Chat, Testlauf, Netz prüfen, Zurücksetzen, Entfernen, Stoppen", () => {
    const html = panel({})
    for (const k of ["lab.chat", "lab.test", "lab.probe", "lab.reset", "lab.remove", "lab.stop", "lab.running", "lab.net_ok"])
      expect(html).toContain(k)
    expect(html).toContain('href="/projects/p1"')
    expect(html).not.toContain("lab.start<")
  })

  it("aus: Starten statt Stoppen", () => {
    const html = panel({ container_running: false })
    expect(html).toContain("lab.start")
    expect(html).toContain("lab.stopped")
  })

  it("Auftrag läuft: Knöpfe gesperrt, Hinweis", () => {
    const html = panel({ running: "test" })
    expect(html).toContain("job.test")
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>lab.reset</)
  })

  it("Netz offen: deutliche Warnung", () => {
    const html = panel({ error_code: "labor_net_open", container_running: false })
    expect(html).toContain("err.labor_net_open")
    expect(html).toContain('role="alert"')
  })

  it("Testlauf-Ergebnis mit roten Tests", () => {
    const html = panel({ last_test: { ok: false, passed: 5239, failed: 2, summary: "2 failed", failures: ["core/tests/a.py::t"], at: "2026-10-30T15:00:00Z" } })
    expect(html).toContain("test.red")
    expect(html).toContain("core/tests/a.py::t")
  })
})

describe("Labor entfernen", () => {
  it("nur mit genau LABOR", () => {
    expect(canRemove("LABOR")).toBe(true)
    for (const w of ["", "labor", "LABOR ", "LAB"]) expect(canRemove(w), w).toBe(false)
  })

  it("echter Dialog mit Überschrift, Knopf erst bei LABOR frei", () => {
    const html = renderToStaticMarkup(<RemoveDialogView word="" busy={false} onWord={noop} onConfirm={noop} onCancel={noop} titleId="t1" />)
    expect(html).toContain('role="dialog"')
    expect(html).toContain('aria-labelledby="t1"')
    expect(html).toContain('id="t1"')
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>remove.confirm</)
    const ok = renderToStaticMarkup(<RemoveDialogView word="LABOR" busy={false} onWord={noop} onConfirm={noop} onCancel={noop} titleId="t1" />)
    expect(ok).not.toMatch(/<button[^>]*disabled=""[^>]*>remove.confirm</)
  })
})
