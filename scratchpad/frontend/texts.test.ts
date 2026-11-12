import { describe, expect, it, vi } from "vitest"

// Der Modul-Index des Kerns importiert dieses Modul; ohne diese Mocks entsteht im Test ein Import-Kreis.
vi.mock("@/shared/api-client", () => ({ api: {} }))
vi.mock("@/features/projects/api", () => ({ projectsApi: {} }))
vi.mock("@/features/cockpit/CockpitShell", () => ({ CockpitShell: () => null }))
vi.mock("@/features/cockpit/CockpitTopbar", () => ({ CockpitTopbar: () => null }))
vi.mock("@/i18n/HelpButton", () => ({ HelpButton: () => null }))
import { i18n, nav, routes } from "./index"
import { de } from "./texts.de"
import { en } from "./texts.en"
import { OPEN_STATUSES, STATUSES } from "./types"

describe("Texte des Ideen-Moduls", () => {
  it("deutsch und englisch haben dieselben Schlüssel", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(de).sort())
  })

  it("kein Text ist leer", () => {
    for (const [lang, texts] of [["de", de], ["en", en]] as const) {
      const leer = Object.entries(texts).filter(([, value]) => !value.trim()).map(([key]) => `${lang}:${key}`)
      expect(leer).toEqual([])
    }
  })

  it("jeder Status hat in beiden Sprachen eine Beschriftung", () => {
    for (const status of STATUSES) {
      expect(de).toHaveProperty(`status_${status}`)
      expect(en).toHaveProperty(`status_${status}`)
    }
    expect(OPEN_STATUSES.every((status) => STATUSES.includes(status))).toBe(true)
  })

  it("Platzhalter stimmen in beiden Sprachen überein", () => {
    const holes = (text: string) => [...text.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort()
    const abweichend = Object.keys(de).filter((key) =>
      holes(de[key as keyof typeof de]).join() !== holes(en[key as keyof typeof en]).join())
    expect(abweichend).toEqual([])
  })
})

describe("Anmeldung im Kern", () => {
  it("bleibt unter /scratchpad und heißt im Menü Ideen", () => {
    expect(routes.map((r) => r.path)).toEqual(["/scratchpad"])
    expect(nav).toHaveLength(1)
    expect(nav[0]).toMatchObject({ path: "/scratchpad", labelKey: "scratchpad", icon: "Lightbulb", area: "schreiben" })
    expect(i18n.de.scratchpad.title).toBe("Ideen")
    expect(i18n.en.scratchpad.title).toBe("Ideas")
  })
})
