// Einbindung des Chats im Editor: wann das Dock steht und wann die rechte Spalte dafür weicht.
import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

const state = vi.hoisted(() => ({
  dock: { open: false, width: 420 },
  board: null as unknown,
  selectedNode: undefined as unknown,
  preview: false,
}))

vi.mock("@/shared/module-icon", () => ({ moduleIcon: () => () => null }))
vi.mock("./api", () => ({ blueprintApi: {} }))
vi.mock("./dock", async (original) => ({ ...(await original<typeof import("./dock")>()), loadDock: () => state.dock }))
vi.mock("./Canvas", async () => {
  const { createElement } = await import("react")
  return { Canvas: () => createElement("div", { "data-part": "canvas" }) }
})
vi.mock("./AgentDock", async () => {
  const { createElement } = await import("react")
  const AgentDock = (p: { boardId: number; projectId: string | null; width: number }) =>
    createElement("aside", {
      "data-part": "dock", "data-board": p.boardId, "data-project": p.projectId ?? "", "data-width": p.width,
    })
  return { AgentDock }
})
vi.mock("./useBoard", () => ({
  useBoard: () => ({
    nodes: [], edges: [], selectedNode: state.selectedNode, status: "saved", board: state.board, editable: true,
    actions: {},
  }),
}))
vi.mock("./useProposal", () => ({
  useProposal: () => ({
    open: false, busy: false, error: null, preview: state.preview,
    graph: state.preview ? { nodes: [], edges: [] } : null,
    diff: state.preview ? { nodes: 0, edges: 0, kept: 0, added: [], removed: [], freshIds: new Set<string>() } : null,
  }),
  useVersions: () => ({ versions: null, loadFailed: false, busy: false, message: null }),
}))
import { BoardEditor } from "./BoardEditor"
import { de, type T } from "./texts.de"

const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))
const BOARD = {
  id: 7, name: "Admin", project_id: "p-alpha", created_at: "", updated_at: "", revision: 1, graph_json: "{}",
  proposal_json: null, proposal_note: null, proposal_at: null,
}
const NODE = {
  id: "n1", position: { x: 0, y: 0 }, data: { kind: "layout", subtype: "button", label: "Speichern", note: "" },
}
const editor = () => renderToStaticMarkup(
  <BoardEditor boardId={7} boardName="Admin" projects={[{ id: "p-alpha", name: "Alpha" }]} locale="de" t={t}
    onBoard={() => undefined} />,
)
const chatButton = (html: string) => html.match(new RegExp(`<button[^>]*title="${de.chat_title}"[^>]*>`))?.[0] ?? ""

describe("Chat neben dem Board im Editor", () => {
  beforeEach(() => {
    Object.assign(state, { dock: { open: false, width: 420 }, board: BOARD, selectedNode: undefined, preview: false })
  })

  it("die Projekt-Auswahl am Board trägt ihren eigenen Namen", () => {
    const html = editor()
    expect(html).toContain(`aria-label="${de.project_label}"`)
    expect(html).not.toContain(`aria-label="${de.project_filter_label}"`)
  })

  it("ohne offenen Chat steht kein Dock da, die rechte Spalte bleibt wie bisher", () => {
    const html = editor()
    expect(html).not.toContain('data-part="dock"')
    expect(html).toContain(de.panel_empty)
    expect(chatButton(html)).toContain('aria-pressed="false"')
  })

  it("mit offenem Chat steht das Dock neben dem Editor, mit Board, Projekt und gemerkter Breite", () => {
    state.dock = { open: true, width: 512 }
    const html = editor()
    expect(html).toContain('data-part="dock" data-board="7" data-project="p-alpha" data-width="512"')
    expect(chatButton(html)).toContain('aria-pressed="true"')
    // Das Dock ist Geschwister der Editor-Spalte, nicht ihr Kind: Es steht hinter der Zeichenfläche.
    expect(html.indexOf('data-part="dock"')).toBeGreaterThan(html.indexOf('data-part="canvas"'))
  })

  it("ein Board ohne Projekt gibt dem Dock kein Projekt mit", () => {
    state.dock = { open: true, width: 420 }
    state.board = { ...BOARD, project_id: null }
    expect(editor()).toContain('data-part="dock" data-board="7" data-project="" data-width="420"')
  })

  it("solange das Board nicht geladen ist, steht auch bei gemerktem offenem Chat kein Dock da", () => {
    state.dock = { open: true, width: 420 }
    state.board = null
    expect(editor()).not.toContain('data-part="dock"')
  })

  it("mit offenem Chat weicht die leere rechte Spalte, damit die Zeichenfläche Platz behält", () => {
    state.dock = { open: true, width: 420 }
    expect(editor()).not.toContain(de.panel_empty)
  })

  it("ein gewählter Baustein bleibt auch mit offenem Chat bearbeitbar", () => {
    state.dock = { open: true, width: 420 }
    state.selectedNode = NODE
    const html = editor()
    expect(html).toContain(de.panel_label)
    expect(html).toContain('value="Speichern"')
  })

  it("in der Vorschau zeigt nur der Editor ohne Chat den Hinweis, mit Chat entfällt die Spalte", () => {
    state.preview = true
    state.selectedNode = NODE
    expect(editor()).toContain(de.panel_preview)
    state.dock = { open: true, width: 420 }
    const html = editor()
    expect(html).not.toContain(de.panel_preview)
    expect(html).not.toContain(de.panel_label)
  })
})
