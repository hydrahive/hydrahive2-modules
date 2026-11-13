// Reiter Entrümpeln (Teil 1 lesen + Teil 2 Schalter) als statisches Markup, mit Logik und Texten de/en.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}${JSON.stringify(o)}` : k,
}) }))
import type { TvwDebloat, TvwDebloatRow, TvwDebloatView, TvwDevice, TvwJob } from "./api"
import { DebloatTab } from "./DebloatTab"
import { GROUP_ORDER, grouped, listName, listNames, mark, others, split, stepText, suggested } from "./debloatLogic"
import { tvwerkstattI18n } from "./i18n"

const DEV: TvwDevice = { device_id: "t1", name: "Wohnzimmer", address: "192.0.2.11", kind: "google_tv" }
const row = (p: Partial<TvwDebloatRow>): TvwDebloatRow => ({ package: "com.example.a", state: "on", recommended: true,
  of: 3, kept: 0, lists: 9, note: "", group: "other", locked: "", ...p })
const VIEW: TvwDebloatView = { lists_used: ["tcl-a/debloat.txt", "tcl-b/debloat-eu.txt"], score: 75, total_lists: 477,
  off_count: 2, recommended_on: 1, read_at: "2026-11-13T20:00:00Z", commit_id: "b953804", ours: [], back_on: [],
  packages: [
    row({ package: "com.example.track", group: "tracking", note: "log capture" }),
    row({ package: "com.example.ads", group: "ads", state: "off" }),
    row({ package: "com.example.home", group: "home", state: "off", locked: "home" }),
    row({ package: "com.example.tv", recommended: false, of: 1, kept: 2, note: "Live TV" }),
  ] }
const job = (state: string, step: string, error_code = ""): TvwJob => ({ job_id: "j", state, step, error_code,
  error_detail: "", started_by: "", created_at: "", updated_at: "" })
const data = (p: Partial<TvwDebloat>): TvwDebloat => ({ view: VIEW, read_job: null, switch_job: null, backup_at: "", ...p })
const A = { onRead: vi.fn(), onPick: vi.fn(), onOff: vi.fn(), onOn: vi.fn(), onUndoAll: vi.fn() }
const html = (d: TvwDebloat | null, picked: string[] = [], busy = false) =>
  renderToStaticMarkup(<DebloatTab dev={DEV} data={d} picked={new Set(picked)} busy={busy} actions={A} />)

describe("TV-Werkstatt: Entrümpeln", () => {
  it("noch nie gelesen: Hinweis und Lese-Knopf, keine Liste, Abschalten gesperrt", () => {
    const out = html(data({ view: null }))
    expect(out).toContain("deb.never")
    expect(out).toContain("deb.read")
    expect(out).toContain("deb.empty")
    expect(out).not.toContain("deb.group.")
    expect(out).toMatch(/disabled=""[^>]*>deb\.switch_off/)
  })

  it("gelesen: Stand, Gruppen in fester Reihenfolge, Kennzeichen, Weitere zugeklappt, Paketname einmal", () => {
    const out = html(data({}))
    expect(out).toContain("deb.lists_of{&quot;n&quot;:2,&quot;all&quot;:477}")
    expect(out).toContain("tcl-a, tcl-b")
    expect(out).toContain("deb.check_update")
    expect(out.indexOf("deb.group.tracking")).toBeLessThan(out.indexOf("deb.group.ads"))
    expect(out.indexOf("deb.group.ads")).toBeLessThan(out.indexOf("deb.group.home"))
    expect(out).toContain("deb.mark.todo")
    expect(out).toContain("deb.lock.home")
    expect(out).toMatch(/<details[^>]*>.*deb\.others/)
    expect(out.split(">com.example.ads<").length - 1).toBe(1)
    expect(out).not.toContain("deb.undo_all")
  })

  it("Haken: gesperrte nicht wählbar; Auswahl zählt getrennt nach ab- und einschalten", () => {
    const out = html(data({}), ["com.example.track", "com.example.ads", "com.example.home"])
    expect(out).toMatch(/disabled=""[^>]*aria-label="com\.example\.home"|aria-label="com\.example\.home"[^>]*disabled=""/)
    expect(out).toContain("deb.switch_off{&quot;n&quot;:1}")
    expect(out).toContain("deb.switch_on{&quot;n&quot;:1}")
  })

  it("von der Werkstatt abgeschaltet: „Alles zurück“; wieder angegangen: Hinweis", () => {
    const v = { ...VIEW, ours: ["com.example.ads", "com.example.track"], back_on: ["com.example.track"] }
    const out = html(data({ view: v, backup_at: "2026-11-13T20:10:00Z" }))
    expect(out).toContain("deb.undo_all")
    expect(out).toContain("deb.back_on{&quot;n&quot;:1}")
    expect(out).toContain("2026-11-13 20:10")
  })

  it("Auftrag läuft: alles gesperrt, Schritt sichtbar; Fehler wird gezeigt", () => {
    const out = html(data({ switch_job: job("running", "batch 2") }), ["com.example.track"])
    expect(out).toContain("deb.working")
    expect(out).toContain("deb.step.batch")
    expect(out).toMatch(/disabled=""[^>]*>deb\.switch_off/)
    expect(html(data({ switch_job: job("failed", "guard", "tvw_debloat_blocked") }))).toContain("err.tvw_debloat_blocked")
  })

  it("Logik: Gruppen, Weitere, Kennzeichen, Listennamen, Auswahl, Vorschlag, Schritte", () => {
    expect(grouped(VIEW).map((g) => g.group)).toEqual(["tracking", "ads", "home"])
    expect(others(VIEW).map((r) => r.package)).toEqual(["com.example.tv"])
    expect(mark(row({ locked: "core", state: "off" }))).toBe("locked")
    expect(mark(row({ state: "off" }))).toBe("off")
    expect(mark(row({}))).toBe("todo")
    expect(mark(row({ recommended: false }))).toBe("on")
    expect(listName("tcl-65c7k-google-tv/debloat-75t8c-eu.txt")).toBe("tcl-65c7k-google-tv")
    expect(listNames(["b/debloat.txt", "a/debloat.txt", "b/debloat-eu.txt"])).toBe("a, b")
    const s = split(VIEW, new Set(["com.example.track", "com.example.ads", "com.example.home", "com.gibts.nicht"]))
    expect(s).toEqual({ off: ["com.example.track"], on: ["com.example.ads"] })
    expect(suggested(VIEW)).toEqual(["com.example.track"])
    expect(stepText("batch 3")).toEqual({ key: "deb.step.batch", n: 3 })
    expect(stepText("guard").key).toBe("deb.step.guard")
    expect(stepText("<script>").key).toBe("deb.step.other")
  })

  it("de und en haben überall dieselben Schlüssel (ganze Seite)", () => {
    const paths = (o: unknown, pre = ""): string[] => typeof o !== "object" || o === null ? [pre]
      : Object.entries(o).flatMap(([k, v]) => paths(v, pre ? `${pre}.${k}` : k))
    expect(paths(tvwerkstattI18n.de).sort()).toEqual(paths(tvwerkstattI18n.en).sort())
  })

  it("jede Gruppe, jedes Kennzeichen, jeder Schritt, jeder neue Fehler hat Text (de/en)", () => {
    const errs = ["tvw_debloat_blocked", "tvw_debloat_locked", "tvw_debloat_bad_package", "tvw_debloat_nothing",
      "tvw_debloat_home_changed", "tvw_debloat_not_off", "tvw_debloat_restore_incomplete", "tvw_debloat_not_on"]
    for (const lang of ["de", "en"] as const) {
      const d = tvwerkstattI18n[lang].tvwerkstatt.deb as unknown as Record<string, Record<string, string>>
      const err = tvwerkstattI18n[lang].tvwerkstatt.err as Record<string, string>
      expect(GROUP_ORDER.filter((g) => !d.group[g]), lang).toEqual([])
      expect(["off", "todo", "locked", "on"].filter((m) => !d.mark[m]), lang).toEqual([])
      expect(["container", "lists", "packages", "guard", "backup", "batch", "restore", "read", "other"]
        .filter((s) => !d.step[s]), lang).toEqual([])
      expect(errs.filter((e) => !err[e]), lang).toEqual([])
    }
  })
})
