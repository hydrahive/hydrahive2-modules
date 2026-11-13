// Reiter Apps (App-Verwaltung mit dem Play Store) als statisches Markup, Logik und Texte.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}${JSON.stringify(o)}` : k,
}) }))
import type { TvwDesktop, TvwDevice, TvwJob, TvwStore, TvwStoreApp } from "./api"
import { AppsTab } from "./AppsTab"
import { tvwerkstattI18n } from "./i18n"
import { nameOf, sorted, sourceKey, validQuery } from "./storeLogic"

const DEV: TvwDevice = { device_id: "t1", name: "Wohnzimmer", address: "192.0.2.11" }
const app = (p: Partial<TvwStoreApp>): TvwStoreApp => ({ package: "com.example.a", version_code: "1",
  version_name: "1.0", installer: "com.android.vending", enabled: true, store: true, locked: false, ...p })
const APPS = [app({ package: "tv.emby.embyatv", version_name: "2.5.05g" }),
  app({ package: "com.gathin.tvhome", installer: "", store: false, locked: true }),
  app({ package: "com.side.load", installer: "", store: false, enabled: false })]
const DESK = { apps: [{ package: "tv.emby.embyatv", label: "Emby", version: "1", has_banner: 1, color: "" }] } as TvwDesktop
const job = (kind: string, state: string, error_code = ""): TvwStore["job"] => ({ kind, state, step: "", error_code,
  error_detail: "", started_by: "", created_at: "", updated_at: "", job_id: "j" } as TvwJob & { kind: "store_read" })
const A = { onRead: vi.fn(), onOpen: vi.fn(), onSearch: vi.fn(), onUninstall: vi.fn() }
const html = (data: TvwStore | null, busy = false) =>
  renderToStaticMarkup(<AppsTab dev={DEV} data={data} desk={DESK} busy={busy} actions={A} />)

describe("TV-Werkstatt: Apps", () => {
  it("noch nicht gelesen: Suche da, Liste leer mit Hinweis", () => {
    const out = html({ view: null, job: null })
    expect(out).toContain("apps.store_title")
    expect(out).toContain("apps.empty")
    expect(out).toMatch(/disabled=""[^>]*>apps\.search</)          // leeres Suchfeld → Knopf aus
  })

  it("gelesen: Name aus Desktop, Store-Knopf nur für Store-Apps, Deinstallieren nicht für Geschütztes", () => {
    const out = html({ view: { apps: APPS, read_at: "2026-11-13T21:00:00Z" }, job: null })
    expect(out).toContain(">Emby<")
    expect(out).toContain("2.5.05g")
    expect(out).toContain("apps.off")
    expect(out.split("apps.open").length - 1).toBe(1)
    expect(out.split("apps.uninstall").length - 1).toBe(2)          // emby + side.load, nicht tvhome
    expect(out).toContain("apps.src_locked")
    expect(out.indexOf(">Emby<")).toBeLessThan(out.indexOf("com.side.load"))
  })

  it("Auftrag läuft: Knöpfe aus; geöffnet: Hinweis; Fehler: Text", () => {
    const v = { apps: APPS, read_at: "2026-11-13T21:00:00Z" }
    expect(html({ view: v, job: job("store_uninstall", "running") })).toContain("apps.job.store_uninstall")
    expect(html({ view: v, job: job("store_open", "done") })).toContain("apps.opened")
    expect(html({ view: v, job: job("store_open", "failed", "tvw_store_failed") })).toContain("err.tvw_store_failed")
  })

  it("Logik: Suchtext wie der Server, Name, Sortierung, Herkunft", () => {
    expect(validQuery("Kodi Media Center")).toBe(true)
    expect(validQuery("Mediathek Ärger & Co.")).toBe(true)
    for (const bad of ["", "   ", "x; reboot", "a$(id)", "a|b", "<b>", "a".repeat(61)]) {
      expect(validQuery(bad), bad).toBe(false)
    }
    expect(nameOf(APPS[0], DESK)).toBe("Emby")
    expect(nameOf(APPS[2], DESK)).toBe("com.side.load")
    expect(sorted(APPS, DESK).map((a) => a.package)[0]).toBe("tv.emby.embyatv")
    expect(APPS.map(sourceKey)).toEqual(["apps.src_store", "apps.src_locked", "apps.src_other"])
  })

  it("alle Texte und Fehler des Reiters in beiden Sprachen", () => {
    for (const lang of ["de", "en"] as const) {
      const a = tvwerkstattI18n[lang].tvwerkstatt.apps as unknown as Record<string, Record<string, string>>
      const err = tvwerkstattI18n[lang].tvwerkstatt.err as Record<string, string>
      expect(["store_read", "store_open", "store_uninstall"].filter((k) => !a.job[k]), lang).toEqual([])
      expect(["tvw_store_bad_query", "tvw_store_bad_package", "tvw_store_failed", "tvw_store_locked",
        "tvw_store_not_user_app"].filter((k) => !err[k]), lang).toEqual([])
      expect((tvwerkstattI18n[lang].tvwerkstatt.tab as Record<string, string>).apps, lang).toBeTruthy()
    }
  })
})
