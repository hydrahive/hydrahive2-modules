import { describe, expect, it, vi } from "vitest"

// Der Modul-Index des Kerns importiert dieses Modul; ohne diese Mocks entsteht im Test ein Import-Kreis.
vi.mock("@/shared/api-client", () => ({ api: {} }))
vi.mock("@/features/projects/api", () => ({ projectsApi: {} }))
vi.mock("@/shared/module-icon", () => ({ moduleIcon: () => () => null }))
vi.mock("@/i18n/HelpButton", () => ({ HelpButton: () => null }))
vi.mock("@/features/chat/ChatPane", () => ({ ChatPane: () => null }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: () => "user" }))
import { errorText } from "./boardView"
import { i18n, nav, routes } from "./index"
import { de, type T } from "./texts.de"
import { en } from "./texts.en"

const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))

describe("Texte des Blueprint-Moduls", () => {
  it("deutsch und englisch haben dieselben Schlüssel", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(de).sort())
  })

  it("kein Text ist leer", () => {
    for (const [lang, texts] of [["de", de], ["en", en]] as const) {
      const leer = Object.entries(texts).filter(([, value]) => !value.trim()).map(([key]) => `${lang}:${key}`)
      expect(leer).toEqual([])
    }
  })

  it("Platzhalter stimmen in beiden Sprachen überein", () => {
    const holes = (text: string) => [...text.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort()
    const abweichend = Object.keys(de).filter((key) =>
      holes(de[key as keyof typeof de]).join() !== holes(en[key as keyof typeof en]).join())
    expect(abweichend).toEqual([])
  })

  it("jeder Zustand der Zeichenfläche und jede Herkunft einer Fassung hat eine Beschriftung", () => {
    for (const status of ["loading", "saved", "saving", "save_error", "conflict", "load_error", "unreadable", "gone"]) {
      expect(de).toHaveProperty(`status_${status}`)
    }
    for (const source of ["proposal", "restore", "overwrite"]) expect(de).toHaveProperty(`version_source_${source}`)
  })
})

describe("Anmeldung im Kern", () => {
  it("bleibt unter /blueprint", () => {
    expect(routes.map((r) => r.path)).toEqual(["/blueprint"])
    expect(nav[0]).toMatchObject({ path: "/blueprint", labelKey: "blueprint", icon: "PenTool" })
    expect(i18n.de.blueprint.title).toBe("Blueprint")
    expect(i18n.en.blueprint.subtitle).toBe("Sketch layouts & flows visually")
  })
})

describe("errorText", () => {
  const failure = (code?: string, message = "kaputt") => Object.assign(new Error(message), { code })

  it("übersetzt bekannte Fehler", () => {
    expect(errorText(failure("project_not_found"), t)).toBe(de.project_error)
    expect(errorText(failure("boards_full"), t)).toBe(de.boards_full)
    expect(errorText(failure("proposal_changed"), t)).toBe(de.proposal_changed)
    expect(errorText(failure("no_proposal"), t)).toBe(de.proposal_changed)
    expect(errorText(failure("board_not_found"), t)).toBe(de.notice_gone)
    expect(errorText(failure("version_not_found"), t)).toBe(de.version_gone)
  })

  it("nennt bei unbekannten Fehlern die Meldung", () => {
    expect(errorText(failure(undefined, "HTTP 502"), t)).toBe("Das hat nicht geklappt: HTTP 502")
    expect(errorText("einfach so", t)).toBe("Das hat nicht geklappt: einfach so")
  })
})
