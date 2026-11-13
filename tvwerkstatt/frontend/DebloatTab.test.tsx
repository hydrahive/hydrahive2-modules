// Reiter Entrümpeln (Teil 1, nur lesen) als statisches Markup, mit Logik und Texten de/en.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}${JSON.stringify(o)}` : k,
}) }))
import type { TvwDebloat, TvwDebloatRow, TvwDebloatView, TvwDevice } from "./api"
import { DebloatTab } from "./DebloatTab"
import { GROUP_ORDER, grouped, listName, listNames, mark, others } from "./debloatLogic"
import { tvwerkstattI18n } from "./i18n"

const DEV: TvwDevice = { device_id: "t1", name: "Wohnzimmer", address: "192.0.2.11", kind: "google_tv" }
const row = (p: Partial<TvwDebloatRow>): TvwDebloatRow => ({ package: "com.example.a", state: "on", recommended: true,
  of: 3, kept: 0, lists: 9, note: "", group: "other", locked: "", ...p })
const VIEW: TvwDebloatView = { lists_used: ["tcl-a/debloat.txt", "tcl-b/debloat-eu.txt"], score: 75, total_lists: 477,
  off_count: 2, recommended_on: 1, read_at: "2026-11-13T20:00:00Z", commit_id: "b953804", packages: [
    row({ package: "com.example.track", group: "tracking", note: "log capture" }),
    row({ package: "com.example.ads", group: "ads", state: "off" }),
    row({ package: "com.example.home", group: "home", state: "off", locked: "home" }),
    row({ package: "com.example.tv", recommended: false, of: 1, kept: 2, note: "Live TV" }),
  ] }
const html = (data: TvwDebloat | null, busy = false) =>
  renderToStaticMarkup(<DebloatTab dev={DEV} data={data} busy={busy} onRead={() => {}} />)

describe("TV-Werkstatt: Entrümpeln", () => {
  it("noch nie gelesen: Hinweis und Lese-Knopf, keine Liste", () => {
    const out = html({ view: null, read_job: null })
    expect(out).toContain("deb.never")
    expect(out).toContain("deb.read")
    expect(out).toContain("deb.empty")
    expect(out).not.toContain("deb.group.")
  })

  it("gelesen: Stand, Gruppen in fester Reihenfolge, Kennzeichen, Weitere zugeklappt", () => {
    const out = html({ view: VIEW, read_job: null })
    expect(out).toContain("deb.lists_of{&quot;n&quot;:2,&quot;all&quot;:477}")
    expect(out).toContain("tcl-a, tcl-b")
    expect(out.split("com.example.ads").length - 1).toBe(1)          // ohne Beschreibung: Paketname nur einmal
    expect(out.split("com.example.track").length - 1).toBe(1)
    expect(out).toContain("log capture")
    expect(out.indexOf("deb.group.tracking")).toBeLessThan(out.indexOf("deb.group.ads"))
    expect(out.indexOf("deb.group.ads")).toBeLessThan(out.indexOf("deb.group.home"))
    expect(out).toContain("deb.mark.todo")
    expect(out).toContain("deb.mark.locked")
    expect(out).toContain("deb.lock.home")
    expect(out).toContain("log capture")
    expect(out).toMatch(/<details[^>]*>.*deb\.others/)
    expect(out).toContain("deb.kept{&quot;n&quot;:2}")
  })

  it("Lesen läuft: Knopf gesperrt, Schritt sichtbar; Fehler wird gezeigt", () => {
    const run = { job_id: "j", state: "running", step: "lists", error_code: "", error_detail: "", started_by: "",
      created_at: "", updated_at: "" }
    expect(html({ view: null, read_job: run })).toMatch(/disabled="".*deb\.reading/)
    const failed = html({ view: null, read_job: { ...run, state: "failed", error_code: "tvw_debloat_read_failed" } })
    expect(failed).toContain("err.tvw_debloat_read_failed")
  })

  it("Logik: Gruppen nur Empfohlenes, Weitere den Rest, Kennzeichen, Listenname", () => {
    expect(grouped(VIEW).map((g) => g.group)).toEqual(["tracking", "ads", "home"])
    expect(others(VIEW).map((r) => r.package)).toEqual(["com.example.tv"])
    expect(mark(row({ locked: "core", state: "off" }))).toBe("locked")
    expect(mark(row({ state: "off" }))).toBe("off")
    expect(mark(row({}))).toBe("todo")
    expect(mark(row({ recommended: false }))).toBe("on")
    expect(listName("tcl-65c7k-google-tv/debloat-75t8c-eu.txt")).toBe("tcl-65c7k-google-tv")
    expect(listNames(["b/debloat.txt", "a/debloat.txt", "b/debloat-eu.txt"])).toBe("a, b")
  })

  it("de und en haben überall dieselben Schlüssel (ganze Seite)", () => {
    const paths = (o: unknown, pre = ""): string[] => typeof o !== "object" || o === null ? [pre]
      : Object.entries(o).flatMap(([k, v]) => paths(v, pre ? `${pre}.${k}` : k))
    expect(paths(tvwerkstattI18n.de).sort()).toEqual(paths(tvwerkstattI18n.en).sort())
  })

  it("jede Gruppe, jedes Kennzeichen, jeder Schritt hat Text (de/en)", () => {
    for (const lang of ["de", "en"] as const) {
      const d = tvwerkstattI18n[lang].tvwerkstatt.deb as unknown as Record<string, Record<string, string>>
      expect(GROUP_ORDER.filter((g) => !d.group[g]), lang).toEqual([])
      expect(["off", "todo", "locked", "on"].filter((m) => !d.mark[m]), lang).toEqual([])
      expect(["container", "lists", "packages"].filter((s) => !d.step[s]), lang).toEqual([])
      expect(["core", "home"].filter((s) => !d.lock[s]), lang).toEqual([])
    }
  })
})
