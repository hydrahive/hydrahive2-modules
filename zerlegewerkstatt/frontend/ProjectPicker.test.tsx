import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { ProjectPicker } from "./ProjectPicker"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }))

const projects = [
  { id: "p1", name: "Wohnzimmer" },
  { id: "p2", name: "Labor" },
]

describe("Projektwahl der Zerlege-Werkstatt", () => {
  it("zeigt Namen statt manuell einzutippender IDs", () => {
    const html = renderToStaticMarkup(<ProjectPicker projects={projects} projectId="p2" status="ready" onChange={() => {}} />)
    expect(html).toContain("<select")
    expect(html).toContain('value="p2"')
    expect(html).toContain("Wohnzimmer")
    expect(html).toContain("Labor")
    expect(html).not.toContain('type="text"')
  })

  it("unterscheidet Laden und keine verfügbaren Projekte", () => {
    const loading = renderToStaticMarkup(<ProjectPicker projects={[]} projectId="" status="loading" onChange={() => {}} />)
    const empty = renderToStaticMarkup(<ProjectPicker projects={[]} projectId="" status="ready" onChange={() => {}} />)
    expect(loading).toContain("projectsLoading")
    expect(empty).toContain("projectsEmpty")
    expect(empty).not.toContain("projectsLoading")
  })

  it("zeigt Projekt-API-Fehler statt eines leeren Projekts", () => {
    const html = renderToStaticMarkup(<ProjectPicker projects={[]} projectId="" status="error" onChange={() => {}} />)
    expect(html).toContain('role="alert"')
    expect(html).toContain("projectsError")
    expect(html).not.toContain("projectsEmpty")
  })
})
