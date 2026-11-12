import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { IdeaList } from "./components/IdeaList"
import { IdeaNotes } from "./components/IdeaNotes"
import { de, type T } from "./texts.de"
import type { IdeaListItem, IdeaNote, ProjectFilter, StatusFilter } from "./types"

const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))
const PROJECTS = [{ id: "p-alpha", name: "Alpha" }]
const noop = () => undefined

function item(id: string, over: Partial<IdeaListItem> = {}): IdeaListItem {
  return {
    id, project_id: null, title: `Idee ${id}`, status: "new", origin: "user", task_id: null, board_id: null,
    created_at: "2026-11-12T08:00:00.000000Z", updated_at: "2026-11-12T08:00:00.000000Z",
    body_preview: "", note_count: 0, ...over,
  }
}

function list(ideas: IdeaListItem[], project: ProjectFilter = "all", status: StatusFilter = "open", activeId: string | null = null) {
  return renderToStaticMarkup(
    <IdeaList ideas={ideas} projects={PROJECTS} project={project} status={status} activeId={activeId} loading={false}
      locale="de" t={t} onProject={noop} onStatus={noop} onSelect={noop} />,
  )
}

describe("IdeaList", () => {
  it("erklärt bei leerer Liste, wie die erste Idee entsteht", () => {
    const html = list([])
    expect(html).toContain(de.empty_title)
    expect(html).toContain("Strg+Enter")
  })

  it("unterscheidet „keine Ideen“ von „der Filter zeigt nichts“", () => {
    const html = list([item("a", { status: "done" })])
    expect(html).toContain(de.empty_filtered)
    expect(html).toContain(de.empty_filtered_action)
    expect(html).not.toContain(de.empty_title)
  })

  it("gruppiert bei „Alle Projekte“ nach Projekt und zeigt Status, Herkunft und Anmerkungen", () => {
    const html = list([
      item("a", { project_id: "p-alpha", status: "planned", origin: "agent", note_count: 2 }),
      item("b"),
    ])
    expect(html).toContain("Alpha")
    expect(html).toContain(de.no_project)
    expect(html).toContain(de.status_planned)
    expect(html).toContain(de.origin_agent)
    expect(html).toContain("Anmerkungen: 2")
    expect(html.indexOf("Idee a")).toBeLessThan(html.indexOf("Idee b"))
  })

  it("zeigt je Status die Anzahl, auch für ausgeblendete", () => {
    const html = list([item("a"), item("b"), item("c", { status: "done" })])
    expect(html).toMatch(/Offene\s*<span[^>]*>2<\/span>/)
    expect(html).toMatch(/Alle\s*<span[^>]*>3<\/span>/)
    expect(html).toMatch(/Umgesetzt\s*<span[^>]*>1<\/span>/)
  })

  it("zeigt bei einem einzelnen Projekt nur dessen Ideen", () => {
    const html = list([item("a", { project_id: "p-alpha" }), item("b")], "p-alpha")
    expect(html).toContain("Idee a")
    expect(html).not.toContain("Idee b")
  })

  it("markiert die ausgewählte Idee", () => {
    const html = list([item("a"), item("b")], "all", "open", "b")
    expect(html.match(/aria-current="true"/g)).toHaveLength(1)
  })

  it("gibt Kopfzeilen als Text aus, nicht als HTML", () => {
    const html = list([item("a", { title: "<img src=x onerror=alert(1)>" })])
    expect(html).toContain("&lt;img src=x")
    expect(html).not.toContain("<img src=x")
  })
})

describe("IdeaNotes", () => {
  const note = (id: number, over: Partial<IdeaNote> = {}): IdeaNote => ({
    id, idea_id: "a", author: "agent", agent_name: null, body: `Anmerkung ${id}`,
    created_at: "2026-11-12T08:00:00.000000Z", ...over,
  })
  const notes = (items: IdeaNote[]) =>
    renderToStaticMarkup(<IdeaNotes notes={items} locale="de" t={t} onRemove={noop} />)

  it("sagt, dass Agenten den Text nicht ändern, auch ohne Anmerkungen", () => {
    const html = notes([])
    expect(html).toContain(de.notes_hint)
    expect(html).toContain(de.notes_empty)
  })

  it("nennt den Agenten beim Namen und fällt sonst auf Agent oder System zurück", () => {
    const html = notes([note(1, { agent_name: "Buddy" }), note(2), note(3, { author: "system", body: "Status: Neu → Geplant" })])
    expect(html).toContain("Buddy")
    expect(html).toContain(`>${de.note_author_agent}<`)
    expect(html).toContain(`>${de.note_author_system}<`)
    expect(html).toContain("Status: Neu → Geplant")
    expect(html.match(new RegExp(`aria-label="${de.note_delete}"`, "g"))).toHaveLength(3)
  })
})
