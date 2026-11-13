import { describe, expect, it } from "vitest"
import type { TvwBuild, TvwJob } from "./api"
import { BUILD_STEPS, buildStep, buildView, lastGood, shortHash, sizeText } from "./buildLogic"
import { tvwerkstattI18n } from "./i18n"

const job = (state: string, step = "build"): TvwJob => ({ job_id: "j", state, step, error_code: "", error_detail: "",
  started_by: "boss", created_at: "", updated_at: "" })
const b = (p: Partial<TvwBuild>): TvwBuild => ({ build_id: "b", part: "launcher", commit_id: "b953804", sha256: "",
  state: "done", created_at: "", ...p })

describe("TV-Werkstatt: Startbildschirm (Logik)", () => {
  it("buildView: läuft, gescheitert, gebaut, noch nie", () => {
    expect(buildView(null, [])).toBe("none")
    expect(buildView(job("running"), [])).toBe("running")
    expect(buildView(job("failed"), [b({})])).toBe("failed")
    expect(buildView(job("done", "done"), [b({})])).toBe("done")
    expect(buildView(null, [b({ state: "failed" })])).toBe("none")
  })

  it("lastGood nimmt den neuesten erfolgreichen Bau", () => {
    expect(lastGood([b({ build_id: "neu", state: "failed" }), b({ build_id: "alt" })])?.build_id).toBe("alt")
  })

  it("Schritte und Texte passen zusammen", () => {
    expect(buildStep("fetch")).toEqual({ n: 2, total: BUILD_STEPS.length })
    expect(buildStep("x").n).toBe(0)
    for (const lang of ["de", "en"] as const) {
      const steps = tvwerkstattI18n[lang].tvwerkstatt.bstep as Record<string, string>
      expect([...BUILD_STEPS, "done"].filter((k) => !steps[k]), lang).toEqual([])
    }
  })

  it("Prüfsumme kurz, Größe lesbar", () => {
    expect(shortHash("c6d21b45a3238d2b56e0d22a08bd0f2a52a97d71d10784d3264078ab84b92780")).toBe("c6d21b45…84b92780")
    expect(shortHash("")).toBe("")
    expect(sizeText(588009)).toBe("588 KB")
    expect(sizeText(1_500_000)).toBe("1,5 MB")
    expect(sizeText(0)).toBe("")
  })
})
