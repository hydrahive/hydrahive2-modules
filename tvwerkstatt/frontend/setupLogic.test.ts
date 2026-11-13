import { describe, expect, it } from "vitest"
import type { TvwJob } from "./api"
import { tvwerkstattI18n } from "./i18n"
import { pollMs, SETUP_STEPS, setupView, stepIndex } from "./setupLogic"

const job = (state: string, step = "packages"): TvwJob => ({ job_id: "j", state, step, error_code: "", error_detail: "",
  started_by: "boss", created_at: "", updated_at: "" })

describe("TV-Werkstatt: Bauumgebung (Logik)", () => {
  it("setupView: läuft, gescheitert, fertig, neu", () => {
    expect(setupView(null, "missing")).toBe("new")
    expect(setupView(job("running"), "running")).toBe("running")
    expect(setupView(job("failed"), "running")).toBe("failed")
    expect(setupView(job("done", "done"), "stopped")).toBe("ready")
    expect(setupView(job("done", "done"), "missing")).toBe("new")          // abgebaut → wieder einrichten anbieten
  })

  it("stepIndex zählt ab 1, Unbekanntes ergibt 0", () => {
    expect(stepIndex("network")).toEqual({ n: 1, total: SETUP_STEPS.length })
    expect(stepIndex("stop")).toEqual({ n: SETUP_STEPS.length, total: SETUP_STEPS.length })
    expect(stepIndex("quatsch").n).toBe(0)
  })

  it("nur während eines Auftrags nachsehen", () => {
    expect(pollMs("running")).toBe(2000)
    for (const v of ["failed", "ready", "new"] as const) expect(pollMs(v)).toBeNull()
  })

  it("jeder Schritt (und fertig) hat einen Text in beiden Sprachen", () => {
    for (const lang of ["de", "en"] as const) {
      const steps = tvwerkstattI18n[lang].tvwerkstatt.step as Record<string, string>
      expect([...SETUP_STEPS, "done"].filter((k) => !steps[k]), lang).toEqual([])
    }
  })

  it("Schritte stimmen mit dem Backend überein", () => {
    const files = import.meta.glob("../backend/*.py", { query: "?raw", import: "default", eager: true })
    const src = Object.values(files).join("\n")
    for (const key of ["user", "packages", "tools", "sdk"]) expect(src).toContain(`Step("${key}"`)
    for (const key of ["network", "container", "keystore", "probe", "stop"]) expect(src).toMatch(new RegExp(`"${key}"`))
  })
})
