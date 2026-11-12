import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", async () => await import("./i18nMock"))
vi.mock("@/shared/api-client", () => ({ api: {} }))
import { TaskSource } from "./components/TaskSource"
import { setLang } from "./i18nMock"

const IDEA = "aaaa1111-0000-4000-8000-000000000001"
const html = (task: { source_kind?: string | null; source_id?: string | null }) =>
  renderToStaticMarkup(<MemoryRouter><TaskSource task={task} /></MemoryRouter>)

describe("TaskSource", () => {
  beforeEach(() => setLang("de"))

  it("zeigt nichts ohne Herkunft", () => {
    expect(html({})).toBe("")
    expect(html({ source_kind: null, source_id: null })).toBe("")
    expect(html({ source_kind: "idea", source_id: null })).toBe("")
  })

  it("verlinkt die Idee, aus der der Task entstanden ist", () => {
    const out = html({ source_kind: "idea", source_id: IDEA })
    expect(out).toContain(`href="/scratchpad?idea=${IDEA}"`)
    expect(out).toContain("Aus Idee")
  })

  it("englisch: Link und Hinweis übersetzt", () => {
    setLang("en")
    const out = html({ source_kind: "idea", source_id: IDEA })
    expect(out).toContain("From idea")
    expect(out).toContain("Go to the idea this task came from")
    expect(out).not.toContain("Aus Idee")
  })

  it("zeigt bei einer unbekannten Art nichts", () => {
    expect(html({ source_kind: "ticket", source_id: "T-17" })).toBe("")
  })

  it("kodiert die ID in der Adresse", () => {
    expect(html({ source_kind: "idea", source_id: "a b&c" })).toContain('href="/scratchpad?idea=a%20b%26c"')
  })
})
