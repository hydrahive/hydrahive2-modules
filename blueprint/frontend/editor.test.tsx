// Einbindung des Chats im Editor: wann das Dock steht und wann die rechte Spalte dafür weicht.
import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

const state = vi.hoisted(() => ({
  dock: { open: false, width: 420 },
  board: null as unknown,
  selectedNode: undefined as unknown,
  preview: false,
  space: null as number | null,
  proposalOpen: false,
  onPreview: null as null | (() => void),
  toggles: 0,
  saved: [] as unknown[],
  actions: null as null | { onVersions: () => void; onChat: () => void },
}))

vi.mock("@/shared/module-icon", () => ({ moduleIcon: () => () => null }))
vi.mock("./api", () => ({ blueprintApi: {} }))
vi.mock("./dock", async (original) => ({
  ...(await original<typeof import("./dock")>()),
  loadDock: () => state.dock,
  saveDock: (next: unknown) => { state.saved.push(next) },
}))
vi.mock("./EditorActions", async (original) => {
  const real = await original<typeof import("./EditorActions")>()
  type Props = Parameters<typeof real.EditorActions>[0]
  // Der echte Baustein, nur mit gemerkten Handlern: Im statischen Markup lässt sich kein Knopf drücken.
  return { EditorActions: (p: Props) => { state.actions = p; return real.EditorActions(p) } }
})
vi.mock("./ProposalBanner", () => ({
  ProposalBanner: (p: { onPreview: () => void }) => { state.onPreview = p.onPreview; return null },
}))
vi.mock("./useWidth", () => ({ useWidth: () => state.space }))
vi.mock("./Canvas", async () => {
  const { createElement } = await import("react")
  return { Canvas: () => createElement("div", { "data-part": "canvas" }) }
})
vi.mock("./AgentDock", async () => {
  const { createElement } = await import("react")
  const AgentDock = (p: { boardId: number; projectId: string | null; width: number; over: boolean }) =>
    createElement("aside", {
      "data-part": "dock", "data-board": p.boardId, "data-project": p.projectId ?? "", "data-width": p.width,
      "data-over": String(p.over),
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
    open: state.proposalOpen, busy: false, error: null, preview: state.preview,
    togglePreview: () => { state.toggles += 1 },
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
    Object.assign(state, {
      dock: { open: false, width: 420 }, board: BOARD, selectedNode: undefined, preview: false, space: null,
      proposalOpen: false, onPreview: null, toggles: 0, saved: [], actions: null,
    })
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

  it("bei genug Platz steht das Board sichtbar neben dem Chat", () => {
    state.dock = { open: true, width: 420 }
    state.space = 1244
    const html = editor()
    expect(html).toContain('data-width="420" data-over="false"')
    expect(html).toMatch(/<div class="contents">.*data-part="canvas"/s)
    expect(html).not.toContain('<div class="hidden">')
  })

  it("wird der Platz knapp, gibt der Chat nach statt der Zeichenfläche", () => {
    state.dock = { open: true, width: 600 }
    state.space = 944
    expect(editor()).toContain('data-width="464" data-over="false"')
  })

  it("auf schmalen Fenstern liegt der Chat über dem Board; Zeichenfläche bleibt eingehängt, Kopfzeile sichtbar", () => {
    state.dock = { open: true, width: 420 }
    state.space = 520
    const html = editor()
    expect(html).toContain('data-width="520" data-over="true"')
    expect(html).toMatch(/<div class="hidden">.*data-part="canvas"/s)
    expect(html).not.toContain('<div class="contents">')
    // Der Knopf zum Schließen des Chats steht in der Kopfzeile, nicht im verdeckten Teil.
    expect(html.indexOf(`title="${de.chat_title}"`)).toBeLessThan(html.indexOf('<div class="hidden">'))
  })

  it("ohne offenen Chat ist das Board auch auf schmalen Fenstern sichtbar", () => {
    state.space = 520
    const html = editor()
    expect(html).toContain('<div class="contents">')
    expect(html).not.toContain('<div class="hidden">')
  })

  it("ein gewählter Baustein lässt den Chat weiter nachgeben", () => {
    state.dock = { open: true, width: 600 }
    state.space = 1244
    state.selectedNode = NODE
    expect(editor()).toContain('data-width="508" data-over="false"')
  })

  it("liegt der Chat über dem Board, macht er für die Vorschau des Vorschlags Platz", () => {
    // Sonst täte „Vorschau“ auf schmalen Fenstern nichts Sichtbares: Die Vorschau steht im verdeckten Board.
    state.dock = { open: true, width: 420 }
    state.space = 520
    state.proposalOpen = true
    editor()
    state.onPreview?.()
    expect(state.saved).toEqual([{ open: false, width: 420 }])
    expect(state.toggles).toBe(1)
  })

  it("steht der Chat neben dem Board, bleibt er bei der Vorschau offen", () => {
    state.dock = { open: true, width: 420 }
    state.space = 1244
    state.proposalOpen = true
    editor()
    state.onPreview?.()
    expect(state.saved).toEqual([])
    expect(state.toggles).toBe(1)
  })

  it("liegt der Chat über dem Board, macht er auch für die früheren Fassungen Platz", () => {
    state.dock = { open: true, width: 420 }
    state.space = 520
    editor()
    state.actions?.onVersions()
    expect(state.saved).toEqual([{ open: false, width: 420 }])
  })

  it("steht der Chat neben dem Board, bleibt er bei den früheren Fassungen offen", () => {
    state.dock = { open: true, width: 420 }
    state.space = 1244
    editor()
    state.actions?.onVersions()
    expect(state.saved).toEqual([])
  })

  it("der Knopf „Agent“ öffnet und schließt den Chat und merkt sich das mit der Breite", () => {
    state.dock = { open: false, width: 512 }
    editor()
    state.actions?.onChat()
    expect(state.saved).toEqual([{ open: true, width: 512 }])
    state.saved = []
    state.dock = { open: true, width: 512 }
    editor()
    state.actions?.onChat()
    expect(state.saved).toEqual([{ open: false, width: 512 }])
  })
})
