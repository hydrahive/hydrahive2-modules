// Die Ansicht der Seite als statisches Markup (Muster telephony/studio): Zustand rein, Text raus. Laden steckt in der Seite.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import type { TvwState } from "./api"
import { PageView } from "./TvWerkstattPage"

const html = (s: TvwState | null, msg: string | null = null) => renderToStaticMarkup(<PageView s={s} msg={msg} />)
const LEER: TvwState = { incus: true, error_code: "", devices: [], builds: [], container: "missing", setup: null }

describe("TV-Werkstatt: Seite", () => {
  it("ohne Container-Umgebung eine verständliche Meldung statt einer leeren Seite", () => {
    const out = html({ ...LEER, incus: false, error_code: "tvw_no_incus" })
    expect(out).toContain("err.tvw_no_incus")
    expect(out).not.toContain("no_devices")
  })

  it("leere Geräteliste: Hinweis, dass noch kein Fernseher eingetragen ist", () => {
    expect(html(LEER)).toContain("no_devices")
  })

  it("Geräte werden mit Name, Adresse und System gezeigt", () => {
    const out = html({ ...LEER, devices: [{ device_id: "d1", name: "Wohnzimmer", address: "192.0.2.10",
      model: "KD-60XF8305", android: "9", adb_state: "open" }] })
    expect(out).toContain("Wohnzimmer")
    expect(out).toContain("192.0.2.10")
    expect(out).toContain("KD-60XF8305 · Android 9")
    expect(out).not.toContain("no_devices")
  })

  it("Fehler beim Laden: Text zum Code, Seite bleibt bedienbar", () => {
    const out = html(null, "err.general")
    expect(out).toContain("err.general")
    expect(out).toContain('role="alert"')
  })

  it("mit Container-Umgebung steht der Bereich Bauumgebung über den Geräten", () => {
    const out = html(LEER)
    expect(out).toContain("setup.title")
    expect(out.indexOf("setup.title")).toBeLessThan(out.indexOf("devices"))
  })

  it("ohne Container-Umgebung kein Knopf zum Einrichten", () => {
    expect(html({ ...LEER, incus: false, error_code: "tvw_no_incus" })).not.toContain("setup.start")
  })

  it("Reihenfolge: Bauumgebung, Fernseher, Startbildschirm", () => {
    const out = html(LEER)
    expect(out.indexOf("setup.title")).toBeLessThan(out.indexOf("devices"))
    expect(out.indexOf("devices")).toBeLessThan(out.indexOf("build.title"))
  })

  it("noch nichts geladen und kein Fehler: Ladeanzeige", () => {
    expect(html(null)).toContain("…")
  })
})
