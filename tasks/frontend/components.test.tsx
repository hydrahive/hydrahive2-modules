import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", async () => await import("./i18nMock"))
vi.mock("@/shared/api-client", () => ({ api: {} }))
vi.mock("@/shared/CollapsibleBox", () => ({
  CollapsibleBox: ({ title, headerRight, children }: { title: React.ReactNode; headerRight?: React.ReactNode; children?: React.ReactNode }) => (
    <section><h2>{title}</h2>{headerRight}{children}</section>
  ),
}))
const tasksState = vi.hoisted(() => ({ tasks: [] as unknown[], loading: false, error: null as string | null }))
vi.mock("./useTasks", () => ({
  useTasks: () => ({ ...tasksState, complete: () => undefined, createTask: () => undefined, updateTask: () => undefined, deleteTask: () => undefined }),
}))
import { NewTaskForm } from "./components/NewTaskForm"
import { TaskBuddyBox } from "./components/TaskBuddyBox"
import { TaskPanel } from "./components/TaskPanel"
import { TaskRow } from "./components/TaskRow"
import { setLang } from "./i18nMock"
import type { Task } from "./types"

const noop = () => undefined
const nothing = async () => undefined

function task(over: Partial<Task> = {}): Task {
  return {
    id: "t-1", username: "alice", project_id: null, session_id: null, title: "Erfundener Task", description: "",
    status: "open", priority: "medium", created_at: "2026-11-12T08:00:00Z", updated_at: "2026-11-12T08:00:00Z", ...over,
  }
}

const row = (t: Task) => renderToStaticMarkup(<MemoryRouter><TaskRow task={t} onStatusChange={noop} onDelete={noop} /></MemoryRouter>)

beforeEach(() => {
  setLang("de")
  Object.assign(tasksState, { tasks: [], loading: false, error: null })
})

describe("TaskRow", () => {
  it("deutsch: Beschriftungen wie bisher", () => {
    const html = row(task({ history_count: 2, source_kind: "idea", source_id: "aaaa1111-0000-4000-8000-000000000001" }))
    for (const text of ["Als erledigt markieren", "Task löschen", "Offen", "In Arbeit", "Erledigt", "Abgebrochen", "Verlauf (2)", "Aus Idee"]) {
      expect(html).toContain(text)
    }
  })

  it("englisch: alles übersetzt, kein deutscher Rest", () => {
    setLang("en")
    const html = row(task({ history_count: 2, source_kind: "idea", source_id: "aaaa1111-0000-4000-8000-000000000001" }))
    for (const text of ["Mark as done", "Delete task", "Open", "In progress", "Done", "Cancelled", "History (2)", "From idea"]) {
      expect(html).toContain(text)
    }
    for (const text of ["erledigt", "löschen", "Offen", "Verlauf", "Aus Idee", "Abgebrochen"]) {
      expect(html).not.toContain(text)
    }
  })

  it("englisch: ein erledigter Task lässt sich wieder öffnen", () => {
    setLang("en")
    expect(row(task({ status: "done" }))).toContain("Reopen")
  })
})

describe("NewTaskForm", () => {
  it("deutsch und englisch", () => {
    const de = renderToStaticMarkup(<NewTaskForm onSave={nothing} onCancel={noop} />)
    for (const text of ["Aufgabentitel…", "Hoch", "Mittel", "Niedrig", "Abbrechen", "Hinzufügen"]) expect(de).toContain(text)
    setLang("en")
    const en = renderToStaticMarkup(<NewTaskForm onSave={nothing} onCancel={noop} />)
    for (const text of ["Task title…", "High", "Medium", "Low", "Cancel", "Add"]) expect(en).toContain(text)
    for (const text of ["Aufgabentitel", "Hoch", "Abbrechen", "Hinzufügen"]) expect(en).not.toContain(text)
  })
})

describe("TaskPanel", () => {
  it("leere Liste und Filter in beiden Sprachen", () => {
    const de = renderToStaticMarkup(<TaskPanel />)
    for (const text of ["Alle", "Offen", "In Arbeit", "Erledigt", "Abgebrochen", "Keine Aufgaben", "Neuen Task anlegen"]) expect(de).toContain(text)
    setLang("en")
    const en = renderToStaticMarkup(<TaskPanel />)
    for (const text of ["All", "Open", "In progress", "Done", "Cancelled", "No tasks", "Create new task"]) expect(en).toContain(text)
    for (const text of ["Alle", "Offen", "Keine Aufgaben", "anlegen"]) expect(en).not.toContain(text)
  })

  it("zeigt beim Laden und bei einem Fehler ohne Meldung den übersetzten Text", () => {
    setLang("en")
    Object.assign(tasksState, { loading: true })
    expect(renderToStaticMarkup(<TaskPanel />)).toContain("Loading…")
    Object.assign(tasksState, { loading: false, error: "" })
    expect(renderToStaticMarkup(<TaskPanel />)).toContain("Could not load tasks")
    Object.assign(tasksState, { error: "HTTP 500" })
    const html = renderToStaticMarkup(<TaskPanel />)
    expect(html).toContain("HTTP 500")
    expect(html).not.toContain("Could not load tasks")
  })
})

describe("TaskBuddyBox", () => {
  it("leer in beiden Sprachen", () => {
    const de = renderToStaticMarkup(<TaskBuddyBox onPrompt={noop} />)
    for (const text of ["Aufgaben", "keine", "Keine offenen Aufgaben", "Aufgaben besprechen"]) expect(de).toContain(text)
    setLang("en")
    const en = renderToStaticMarkup(<TaskBuddyBox onPrompt={noop} />)
    for (const text of ["Tasks", "none", "No open tasks", "Discuss tasks"]) expect(en).toContain(text)
    for (const text of ["Aufgaben", "keine", "besprechen"]) expect(en).not.toContain(text)
  })

  it("englisch mit vielen Tasks: Zähler, „in progress“ und „more“", () => {
    setLang("en")
    tasksState.tasks = Array.from({ length: 8 }, (_unused, index) =>
      task({ id: `t-${index}`, title: `Task ${index}`, status: index === 0 ? "in_progress" : "open" }))
    const html = renderToStaticMarkup(<TaskBuddyBox onPrompt={noop} />)
    for (const text of ["8 open", "in progress", "+2 more", "Show all", "Mark as done"]) expect(html).toContain(text)
    for (const text of ["offen", "in Arbeit", "weitere", "Alle anzeigen"]) expect(html).not.toContain(text)
  })
})
