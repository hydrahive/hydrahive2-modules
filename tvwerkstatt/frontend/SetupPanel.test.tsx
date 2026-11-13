// Bereich „Bauumgebung“ als statisches Markup (Muster TvWerkstattPage.test.tsx).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}(${Object.entries(o).map(([a, b]) => `${a}=${b}`).join(",")})` : k,
}) }))
import type { ContainerState, TvwJob } from "./api"
import { SetupPanel } from "./SetupPanel"

const A = { onSetup: vi.fn(), onStop: vi.fn(), onRemove: vi.fn() }
const job = (p: Partial<TvwJob>): TvwJob => ({ job_id: "j", state: "running", step: "packages", error_code: "",
  error_detail: "", started_by: "boss", created_at: "", updated_at: "", ...p })
const html = (j: TvwJob | null, c: ContainerState, busy = false) =>
  renderToStaticMarkup(<SetupPanel job={j} container={c} busy={busy} actions={A} />)

describe("TV-Werkstatt: Bereich Bauumgebung", () => {
  it("neu: Lizenz-Haken und Knopf Einrichten, Knopf erst nach Haken bedienbar", () => {
    const out = html(null, "missing")
    expect(out).toContain("setup.license")
    expect(out).toContain("setup.start")
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>setup\.start/)
    expect(out).not.toContain("setup.remove")
  })

  it("läuft: Schritt n von m, kein Knopf zum Einrichten oder Abbauen", () => {
    const out = html(job({ step: "tools" }), "running")
    expect(out).toContain("setup.running(n=5,total=9)")
    expect(out).toContain("step.tools")
    expect(out).toContain('role="status"')
    expect(out).not.toContain("setup.start")
    expect(out).not.toContain("setup.remove")
  })

  it("gescheitert: Fehlertext, Schritt, Ausgabe und Nochmal", () => {
    const out = html(job({ state: "failed", step: "sdk", error_code: "tvw_setup_failed",
      error_detail: "Warning: Failed to download" }), "running")
    expect(out).toContain("err.tvw_setup_failed")
    expect(out).toContain("setup.failed_at")
    expect(out).toContain("Warning: Failed to download")
    expect(out).toContain("setup.retry")
    expect(out).toContain("setup.stop")
    expect(out).toContain('role="alert"')
  })

  it("fertig und ruhend: Hinweis, Abbauen ja, Anhalten nein", () => {
    const out = html(job({ state: "done", step: "done" }), "stopped")
    expect(out).toContain("setup.ready")
    expect(out).toContain("setup.remove")
    expect(out).not.toContain("setup.stop")
    expect(out).not.toContain("setup.start")
  })

  it("während einer Aktion sind die Knöpfe gesperrt", () => {
    const out = html(job({ state: "done", step: "done" }), "running", true)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>setup\.stop/)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>setup\.remove/)
  })
})
