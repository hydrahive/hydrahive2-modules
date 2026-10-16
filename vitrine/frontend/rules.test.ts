import { describe, expect, it } from "vitest"
import { clamp, describeRule, fromTemplate, newRule, ruleErrors, sizeLabel, type Rule } from "./rules"

const t = (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k)

describe("Vitrine-Regeln", () => {
  it("beschreibt jede Art lesbar", () => {
    expect(describeRule({ kind: "range", from: "12-24", to: "12-26" } as Rule, t)).toBe("24.12. – 26.12.")
    expect(describeRule({ kind: "time", from: "18:00", to: "23:00" } as Rule, t)).toBe("18:00 – 23:00")
    expect(describeRule({ kind: "season", season: "autumn" } as Rule, t)).toBe("season.autumn")
    expect(describeRule({ kind: "advent" } as Rule, t)).toBe("kind.advent")
    expect(describeRule({ kind: "easter", offset_from: -2, offset_to: 1 } as Rule, t)).toBe('easter_range:{"from":-2,"to":1}')
  })

  it("prüft im Browser wie der Server", () => {
    expect(ruleErrors({ ...newRule("range"), name: "x", from: "13-40", to: "01-01" })).toContain("from")
    expect(ruleErrors({ ...newRule("time"), name: "x", from: "24:00", to: "06:00" })).toContain("from")
    expect(ruleErrors({ ...newRule("easter"), name: "x", offset_from: 2, offset_to: -1 })).toContain("offset")
    expect(ruleErrors({ ...newRule("season"), name: "" })).toContain("name")
    expect(ruleErrors({ ...newRule("range"), name: "Weihnachten", from: "12-24", to: "12-26" })).toEqual([])
    expect(ruleErrors({ ...newRule("range"), name: "Schaltjahr", from: "02-29", to: "02-29" })).toEqual([])
  })

  it("macht aus einer Vorlage eine eigene Regel", () => {
    const r = fromTemplate({ name: "Weihnachten", kind: "range", from: "12-24", to: "12-26", priority: 60 })
    expect(r.id).toMatch(/^[a-z0-9]{8,}$/)
    expect(r).toMatchObject({ name: "Weihnachten", kind: "range", enabled: true, videos: [], priority: 60 })
    expect(fromTemplate({ name: "x", kind: "advent", priority: 1 }).id).not.toBe(r.id)
  })

  it("zeigt Dateigrößen", () => {
    expect(sizeLabel(512)).toBe("512 B")
    expect(sizeLabel(9_135_259)).toBe("8.7 MB")
    expect(sizeLabel(1536)).toBe("1.5 KB")
  })
})

describe("Einstellungen begrenzen", () => {
  it("hält Bildrate und Einblendungsdauer im erlaubten Bereich", () => {
    expect(clamp(24, 12, 30)).toBe(24)
    expect(clamp(5, 12, 30)).toBe(12)
    expect(clamp(99, 12, 30)).toBe(30)
    expect(clamp(17.6, 12, 30)).toBe(18)
    expect(clamp(Number(""), 5, 120)).toBe(5)
    expect(clamp(Number.NaN, 5, 120)).toBe(5)
  })
})
