import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}(${Object.entries(o).map(([a, b]) => `${a}=${b}`).join(",")})` : k,
}) }))
import type { TvwBuild, TvwJob } from "./api"
import { BuildPanel } from "./BuildPanel"

const job = (p: Partial<TvwJob>): TvwJob => ({ job_id: "j", state: "running", step: "build", error_code: "",
  error_detail: "", started_by: "boss", created_at: "", updated_at: "", ...p })
const GOOD: TvwBuild = { build_id: "b1", part: "launcher", commit_id: "b95380483c97", state: "done", created_at: "",
  sha256: "c6d21b45a3238d2b56e0d22a08bd0f2a52a97d71d10784d3264078ab84b92780", version: "3.4 (13)", size: 588009,
  log_tail: "BUILD SUCCESSFUL in 38s" }
const html = (j: TvwJob | null, builds: TvwBuild[], ready = true, busy = false) =>
  renderToStaticMarkup(<BuildPanel job={j} builds={builds} ready={ready} busy={busy} onBuild={() => {}} />)

describe("TV-Werkstatt: Bereich Startbildschirm", () => {
  it("nicht eingerichtet: Hinweis, kein Knopf", () => {
    const out = html(null, [], false)
    expect(out).toContain("build.need_setup")
    expect(out).not.toContain("build.start")
  })

  it("noch nie gebaut: Knopf bauen", () => {
    expect(html(null, [])).toContain("build.start")
  })

  it("baut gerade: Schritt n von m, kein Knopf", () => {
    const out = html(job({ step: "verify" }), [])
    expect(out).toContain("build.running(n=3,total=5)")
    expect(out).toContain("bstep.verify")
    expect(out).not.toContain("build.start")
  })

  it("gebaut: Version, Größe, Prüfsumme, Quelle, Protokoll, Neu bauen", () => {
    const out = html(job({ state: "done", step: "done" }), [GOOD])
    for (const s of ["build.done", "build.version(v=3.4 (13))", "588 KB", "build.hash(h=c6d21b45…84b92780)",
      "build.source(c=b953804)", "BUILD SUCCESSFUL in 38s", "build.again"]) expect(out).toContain(s)
  })

  it("gescheitert: Fehler, Schritt, Protokoll; der letzte gute Bau bleibt sichtbar", () => {
    const out = html(job({ state: "failed", step: "build", error_code: "tvw_build_failed",
      error_detail: "* What went wrong: boom" }), [GOOD])
    expect(out).toContain("err.tvw_build_failed")
    expect(out).toContain("What went wrong")
    expect(out).toContain("build.done")
    expect(out).toContain('role="alert"')
  })
})
