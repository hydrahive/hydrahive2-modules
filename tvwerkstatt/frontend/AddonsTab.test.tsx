// Reiter Zusätze als statisches Markup, Logik und Texte.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}${JSON.stringify(o)}` : k,
}) }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
import type { TvwAddon, TvwAddons, TvwDevice } from "./api"
import { AddonsTab } from "./AddonsTab"
import { androidOf, FILTERS, fits, shownPerms, visible } from "./addonLogic"
import { tvwerkstattI18n } from "./i18n"

const DEV: TvwDevice = { device_id: "t1", name: "Wohnzimmer", address: "192.0.2.11", sdk: 28 }
const add = (p: Partial<TvwAddon>): TvwAddon => ({ id: "koi-pond", name: "Koi Pond", what: "A pixel koi pond",
  author: "@a", tested: "", permissions_text: "", package: "io.example.koi", min_sdk: 26, dream: true,
  permissions: [], has_image: false, installed: null, ...p })
const ITEMS = [add({}),
  add({ id: "remote-access", name: "Remote Access", what: "ADB state", dream: false,
    permissions: [{ name: "WRITE_SECURE_SETTINGS", level: "red" }, { name: "INTERNET", level: "" }] }),
  add({ id: "weather", name: "Weather", what: "Forecast", dream: false, permissions: [{ name: "INTERNET", level: "" }],
    installed: { version: "1.0 (1)", permissions: ["INTERNET", "WAKE_LOCK"], installed_at: "" } }),
  add({ id: "sleep-timer", name: "Sleep Timer", what: "Timer", dream: false, min_sdk: 30 })]
const A = { onCatalog: vi.fn(), onInstall: vi.fn(), onRemove: vi.fn() }
const html = (data: TvwAddons | null) => renderToStaticMarkup(<AddonsTab dev={DEV} data={data} busy={false} actions={A} />)

describe("TV-Werkstatt: Zusätze", () => {
  it("ohne Katalog: Knopf „Katalog laden“", () => {
    const out = html({ items: null, commit_id: "b953804", job: null })
    expect(out).toContain("add.load")
    expect(out).toContain("add.none_yet")
  })

  it("mit Katalog: Karten, Rechte farbig, installiert mit Neu bauen/Entfernen, zu alt gesperrt", () => {
    const out = html({ items: ITEMS, commit_id: "b953804", job: null })
    for (const n of ["Koi Pond", "Remote Access", "Weather", "Sleep Timer"]) expect(out).toContain(n)
    expect(out).toContain("add.perm.WRITE_SECURE_SETTINGS")
    expect(out).toMatch(/border-red-400\/60[^"]*"[^>]*>add\.perm\.WRITE_SECURE_SETTINGS/)
    expect(out).toContain("add.rebuild")
    expect(out).toContain("add.remove")
    expect(out).toContain("add.too_old{&quot;v&quot;:&quot;11&quot;}")
    expect(out).toContain("add.no_perms")
    expect(out).toContain("cleanyourtv · b953804")
  })

  it("Auftrag läuft und Fehler", () => {
    const job = { job_id: "j", state: "running", step: "build", error_code: "", error_detail: "", started_by: "",
      created_at: "", updated_at: "", kind: "addon_install" as const }
    expect(html({ items: ITEMS, commit_id: "x", job })).toContain("add.working")
    const failed = html({ items: ITEMS, commit_id: "x", job: { ...job, state: "failed", error_code: "tvw_build_failed" } })
    expect(failed).toContain("err.tvw_build_failed")
  })

  it("Logik: Filter, Suche, Rechte nach dem Bau, passt, Android-Version", () => {
    expect(visible(ITEMS, "all", "").length).toBe(4)
    expect(visible(ITEMS, "none", "").map((a) => a.id)).toEqual(["koi-pond", "sleep-timer"])
    expect(visible(ITEMS, "dream", "").map((a) => a.id)).toEqual(["koi-pond"])
    expect(visible(ITEMS, "installed", "").map((a) => a.id)).toEqual(["weather"])
    expect(visible(ITEMS, "all", "FORECAST").map((a) => a.id)).toEqual(["weather"])
    expect(shownPerms(ITEMS[2]).map((p) => p.name)).toEqual(["INTERNET", "WAKE_LOCK"])
    expect(shownPerms(ITEMS[1])[0].level).toBe("red")
    expect(fits(ITEMS[3], 28)).toBe(false)
    expect(fits(ITEMS[3], undefined)).toBe(true)
    expect(androidOf(26)).toBe("8")
    expect(androidOf(99)).toBe("99")
  })

  it("Texte de/en: Filter, Schritte, Fehler, Reiter", () => {
    for (const lang of ["de", "en"] as const) {
      const a = tvwerkstattI18n[lang].tvwerkstatt.add as unknown as Record<string, Record<string, string>>
      const err = tvwerkstattI18n[lang].tvwerkstatt.err as Record<string, string>
      expect(FILTERS.filter((f) => !a.filter[f]), lang).toEqual([])
      expect(["container", "catalog", "fetch", "verify", "build", "collect", "push", "remove"]
        .filter((s) => !a.step[s]), lang).toEqual([])
      expect(["tvw_addons_catalog_failed", "tvw_addon_unknown", "tvw_addon_remove_failed", "tvw_build_failed",
        "tvw_source_mismatch", "tvw_build_unexpected"].filter((k) => !err[k]), lang).toEqual([])
    }
  })
})
