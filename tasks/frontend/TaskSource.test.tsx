import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { TaskSource } from "./components/TaskSource"

const IDEA = "aaaa1111-0000-4000-8000-000000000001"
const html = (task: { source_kind?: string | null; source_id?: string | null }) =>
  renderToStaticMarkup(<MemoryRouter><TaskSource task={task} /></MemoryRouter>)

describe("TaskSource", () => {
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

  it("zeigt bei einer unbekannten Art nichts", () => {
    expect(html({ source_kind: "ticket", source_id: "T-17" })).toBe("")
  })

  it("kodiert die ID in der Adresse", () => {
    expect(html({ source_kind: "idea", source_id: "a b&c" })).toContain('href="/scratchpad?idea=a%20b%26c"')
  })
})
