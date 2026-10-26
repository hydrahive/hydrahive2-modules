import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(async () => ({})), post: vi.fn(), put: vi.fn(), delete: vi.fn(), postForm: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/cockpit/CockpitShell", () => ({ CockpitShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }))
vi.mock("@/features/cockpit/CockpitTopbar", () => ({ CockpitTopbar: () => <div /> }))

const { VitrinePage } = await import("./VitrinePage")

const html = (url: string) => renderToStaticMarkup(<MemoryRouter initialEntries={[url]}><VitrinePage /></MemoryRouter>)

describe("Vitrine-Seite mit Reitern", () => {
  it("Kopf und alle sechs Reiter, Speichern im Kopf", () => {
    const h = html("/vitrine")
    for (const id of ["overview", "program", "display", "dashboard", "light", "bluetooth"]) expect(h).toContain(`data-tab="${id}"`)
    expect(h.match(/role="tab"/g)).toHaveLength(6)
    expect(h).toContain("save")
  })

  it("ohne Angabe: Übersicht mit Status und Einblendungen, sonst nichts", () => {
    const h = html("/vitrine")
    expect(h).toContain('data-panel="overview"')
    expect(h).toContain('aria-selected="true" tabindex="0" data-tab="overview"')
    expect(h).toContain("messages")
    expect(h).not.toContain("bt_title")
    expect(h).not.toContain("simulate")
  })

  it("Reiter aus der Adresse, unbekannt → Übersicht", () => {
    expect(html("/vitrine?tab=bluetooth")).toContain('data-panel="bluetooth"')
    expect(html("/vitrine?tab=bluetooth")).toContain("bt_title")
    expect(html("/vitrine?tab=quatsch")).toContain('data-panel="overview"')
  })
})
