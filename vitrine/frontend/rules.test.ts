import { describe, expect, it } from "vitest"
import { clamp, dashboardErrors, dashboardInfo, parseRepos, describeRule, displayState, formatDates, fromTemplate, newRule, parseDates, ruleErrors, sizeLabel, type Rule } from "./rules"

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

describe("Neue Feiertagsarten", () => {
  it("beschreibt Adventssonntag, n-ten Wochentag und Termine je Jahr", () => {
    expect(describeRule({ kind: "advent_sunday", n: 2 } as Rule, t)).toBe('advent_n:{"n":2}')
    expect(describeRule({ kind: "nth_weekday", month: 5, weekday: 6, n: 2 } as Rule, t)).toBe('nth_weekday_desc:{"n":"nth.2","weekday":"weekday.6","month":"month.5"}')
    expect(describeRule({ kind: "dates", dates: [{ from: "2026-12-04", to: "2026-12-12" }, { from: "2027-12-24", to: "2028-01-01" }] } as Rule, t))
      .toBe('dates_desc:{"count":2,"first":"04.12.2026","last":"01.01.2028"}')
    expect(describeRule({ kind: "dates", dates: [] } as unknown as Rule, t)).toBe('dates_desc:{"count":0,"first":"?","last":"?"}')
  })

  it("prüft die neuen Arten wie der Server", () => {
    expect(ruleErrors({ ...newRule("advent_sunday"), name: "x" })).toEqual([])
    expect(ruleErrors({ ...newRule("advent_sunday"), name: "x", n: 5 })).toContain("n")
    expect(ruleErrors({ ...newRule("nth_weekday"), name: "x" })).toEqual([])
    expect(ruleErrors({ ...newRule("nth_weekday"), name: "x", month: 13 })).toContain("month")
    expect(ruleErrors({ ...newRule("nth_weekday"), name: "x", n: 0 })).toContain("n")
    expect(ruleErrors({ ...newRule("dates"), name: "x" })).toEqual([])
    expect(ruleErrors({ ...newRule("dates"), name: "x", dates: [{ from: "2026-12-12", to: "2026-12-04" }] })).toContain("dates")
    expect(ruleErrors({ ...newRule("dates"), name: "x", dates: [{ from: "2026-02-30", to: "2026-03-01" }] })).toContain("dates")
    expect(ruleErrors({ ...newRule("dates"), name: "x", dates: [{ from: "2026-01-01", to: "2026-03-01" }] })).toContain("dates")
  })

  it("liest und schreibt Termine als Textzeilen", () => {
    expect(parseDates("2026-12-04 2026-12-12\n\n 2027-12-24  2028-01-01 ")).toEqual([
      { from: "2026-12-04", to: "2026-12-12" }, { from: "2027-12-24", to: "2028-01-01" }])
    expect(formatDates([{ from: "2026-12-04", to: "2026-12-12" }])).toBe("2026-12-04 2026-12-12")
    expect(parseDates("quatsch")).toEqual([{ from: "quatsch", to: "" }])
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

describe("Statuskarte", () => {
  it("unterscheidet Dienst aus, Display fehlt, Nacht und läuft", () => {
    expect(displayState(null)).toBe("loading")
    expect(displayState({ running: false, connected: false, night: null })).toBe("stopped")
    expect(displayState({ running: true, connected: false, night: null })).toBe("no_display")
    expect(displayState({ running: true, connected: false, night: "dim" })).toBe("no_display")
    expect(displayState({ running: true, connected: true, night: "dim" })).toBe("night")
    expect(displayState({ running: true, connected: true, night: null })).toBe("running")
  })
})

describe("Dashboard-Anzeige", () => {
  it("zeigt Modus und ob das Dashboard verfügbar ist", () => {
    expect(dashboardInfo(null)).toEqual({ mode: null, state: "off", reason: null })
    expect(dashboardInfo({ mode: "video", dashboard: "aus" })).toEqual({ mode: "video", state: "off", reason: null })
    expect(dashboardInfo({ mode: "dashboard", dashboard: "bereit" })).toEqual({ mode: "dashboard", state: "ready", reason: null })
    expect(dashboardInfo({ mode: "video", dashboard: "nicht verfügbar: libevdi fehlt" }))
      .toEqual({ mode: "video", state: "unavailable", reason: "libevdi fehlt" })
    expect(dashboardInfo({ mode: "video", dashboard: "startet" })).toEqual({ mode: "video", state: "unavailable", reason: "startet" })
  })
})

describe("Statuszentrale-Einstellungen", () => {
  const ok = { tasks_user: "till", github_project: "Hydrahive DEV", github_repos: ["hydrahive/hydrahive2"] }
  it("nimmt gültige Werte", () => { expect(dashboardErrors(ok)).toEqual([]) })
  it("lehnt wie der Server ab", () => {
    expect(dashboardErrors({ ...ok, tasks_user: "a b" })).toContain("tasks_user")
    expect(dashboardErrors({ ...ok, github_project: " " })).toContain("github_project")
    expect(dashboardErrors({ ...ok, github_repos: ["a/.."] })).toContain("github_repos")
    expect(dashboardErrors({ ...ok, github_repos: ["https://x/y"] })).toContain("github_repos")
    expect(dashboardErrors({ ...ok, github_repos: Array(6).fill("a/b") })).toContain("github_repos")
  })
  it("liest Repos aus Komma/Zeilen", () => { expect(parseRepos(" a/b,\nc/d  ")).toEqual(["a/b", "c/d"]) })
})
