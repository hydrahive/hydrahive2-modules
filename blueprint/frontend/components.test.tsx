import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/i18n/HelpButton", () => ({ HelpButton: () => null }))
vi.mock("@/shared/module-icon", () => ({ moduleIcon: () => () => null }))
import { BoardSidebar } from "./BoardSidebar"
import { ChatNotice } from "./ChatNotice"
import { ProposalBanner } from "./ProposalBanner"
import { SyncNotice } from "./SyncNotice"
import { de, type T } from "./texts.de"
import { VersionList } from "./VersionList"
import type { BoardListItem, BoardVersion, ChatInfo, ProjectFilter, SyncStatus } from "./types"
import type { ProposalDiff } from "./boardGraph"
import { NodePalette } from "./NodePalette"

const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_match, name: string) => String(vars?.[name] ?? ""))
const noop = () => undefined
const PROJECTS = [{ id: "p-alpha", name: "Alpha" }]

function diff(over: Partial<ProposalDiff> = {}): ProposalDiff {
  const base = { nodes: 4, edges: 2, kept: 2, added: ["Gültig?", "Fehler"], removed: ["Alte Anzeige"] }
  return { ...base, freshIds: new Set(), ...over }
}

function banner(over: Partial<Parameters<typeof ProposalBanner>[0]> = {}) {
  return renderToStaticMarkup(
    <ProposalBanner note="mit Fehlerfall" at="2026-11-12T16:00:00Z" diff={diff()} preview={false} busy={false}
      error={null} locale="de" t={t} onPreview={noop} onAccept={noop} onDiscard={noop} {...over} />,
  )
}

describe("ProposalBanner", () => {
  it("zeigt Notiz, Zeit, Umfang und was sich ändert", () => {
    const html = banner()
    expect(html).toContain(de.proposal_title)
    expect(html).toContain("mit Fehlerfall")
    expect(html).toContain("12.11.2026")
    expect(html).toContain("Bausteine: 4")
    expect(html).toContain("Verbindungen: 2")
    expect(html).toContain("Neu: 2")
    expect(html).toContain("Gültig?, Fehler")
    expect(html).toContain("Entfällt: 1")
    expect(html).toContain("Alte Anzeige")
    for (const label of [de.proposal_preview, de.proposal_accept, de.proposal_discard]) {
      expect(html).toContain(`>${label}</button>`)
    }
    expect(html).toContain(de.proposal_accept_hint)
    expect(html).not.toContain(de.proposal_same)
  })

  it("sagt, wenn sich an den Bausteinen nichts ändert", () => {
    const html = banner({ diff: diff({ added: [], removed: [], kept: 4 }) })
    expect(html).toContain(de.proposal_same)
    expect(html).not.toContain("Neu:")
  })

  it("kürzt lange Listen", () => {
    const added = Array.from({ length: 9 }, (_, i) => `Baustein ${i + 1}`)
    const html = banner({ diff: diff({ added }) })
    expect(html).toContain("Neu: 9")
    expect(html).toContain("Baustein 6")
    expect(html).not.toContain("Baustein 7")
    expect(html).toContain("und 3 weitere")
  })

  it("in der Vorschau führt der Knopf zurück zur eigenen Fassung", () => {
    const html = banner({ preview: true })
    expect(html).toContain(`>${de.proposal_preview_off}</button>`)
    expect(html).toContain(de.proposal_preview_hint)
  })

  it("ein unlesbarer Vorschlag lässt sich nur verwerfen", () => {
    const html = banner({ diff: null })
    expect(html).toContain(de.proposal_unreadable)
    expect(html).not.toContain(`>${de.proposal_accept}</button>`)
    expect(html).not.toContain(`>${de.proposal_preview}</button>`)
    expect(html).toContain(`>${de.proposal_discard}</button>`)
  })

  it("Notiz und Beschriftungen des Agenten sind Text, kein HTML", () => {
    const evil = '<img src=x onerror="alert(1)">'
    const html = banner({ note: evil, diff: diff({ added: [evil] }) })
    expect(html).not.toContain("<img")
    expect(html).toContain("&lt;img")
  })

  it("zeigt einen Fehler und sperrt die Knöpfe, solange etwas läuft", () => {
    const html = banner({ error: de.proposal_unsaved, busy: true })
    expect(html).toMatch(/role="alert"[^>]*>[^<]*noch nicht gespeichert/)
    expect(html.match(/disabled=""/g)?.length).toBe(3)
  })
})

describe("SyncNotice", () => {
  const notice = (status: SyncStatus) =>
    renderToStaticMarkup(
      <SyncNotice status={status} busy={false} t={t} onRetry={noop} onKeepMine={noop} onTakeTheirs={noop} />,
    )

  it("schweigt, solange alles in Ordnung ist", () => {
    for (const status of ["loading", "saved", "saving"] as const) expect(notice(status)).toBe("")
  })

  it("bietet im Konflikt beide Wege an und sagt, was jeweils passiert", () => {
    const html = notice("conflict")
    expect(html).toContain(de.notice_conflict)
    expect(html).toContain(`>${de.conflict_keep}</button>`)
    expect(html).toContain(`>${de.conflict_load}</button>`)
    expect(html).toContain(de.conflict_keep_hint)
    expect(html).toContain(de.conflict_load_hint)
  })

  it("bietet bei Lade- und Speicherfehlern das Wiederholen an", () => {
    expect(notice("load_error")).toContain(de.notice_load_error)
    expect(notice("load_error")).toContain(`>${de.retry}</button>`)
    expect(notice("save_error")).toContain(de.notice_save_error)
    expect(notice("save_error")).toContain(`>${de.retry}</button>`)
  })

  it("erklärt unlesbare und gelöschte Boards ohne Knopf", () => {
    expect(notice("unreadable")).toContain(de.notice_unreadable)
    expect(notice("gone")).toContain(de.notice_gone)
    expect(notice("unreadable") + notice("gone")).not.toContain("<button")
  })
})

describe("VersionList", () => {
  const version = (id: number, over: Partial<BoardVersion> = {}): BoardVersion =>
    ({ id, source: "proposal", node_count: 3, created_at: "2026-11-12T15:30:00Z", ...over })
  const list = (versions: BoardVersion[] | null, error = false) =>
    renderToStaticMarkup(
      <VersionList versions={versions} error={error} busy={false} locale="de" t={t} onRestore={noop} onClose={noop} />,
    )

  it("erklärt die leere Liste", () => {
    expect(list([])).toContain(de.versions_empty)
  })

  it("zeigt Zeit, Umfang und Herkunft je Fassung", () => {
    const html = list([version(2, { source: "overwrite", node_count: 5 }), version(1)])
    expect(html).toContain("12.11.2026")
    expect(html).toContain("Bausteine: 5")
    expect(html).toContain(de.version_source_overwrite)
    expect(html).toContain(de.version_source_proposal)
    expect(html.match(new RegExp(`>${de.versions_restore}</button>`, "g"))?.length).toBe(2)
    expect(html).toContain(de.versions_restore_hint)
  })

  it("meldet einen Ladefehler", () => {
    expect(list(null, true)).toContain(de.versions_load_error)
  })
})

describe("BoardSidebar", () => {
  const board = (id: number, over: Partial<BoardListItem> = {}): BoardListItem =>
    ({ id, name: `Board ${id}`, project_id: null, created_at: "", updated_at: "", has_proposal: false, ...over })
  const sidebar = (boards: BoardListItem[], project: ProjectFilter = "all", projects = PROJECTS) =>
    renderToStaticMarkup(
      <BoardSidebar boards={boards} projects={projects} project={project} activeId={boards[0]?.id ?? null} t={t}
        onProject={noop} onSelect={noop} onCreate={noop} onDelete={noop} />,
    )

  it("zeigt im Leer-Zustand Bild und Hinweis", () => {
    const html = sidebar([])
    expect(html).toContain(de.boards_empty)
    expect(html).toContain("<img")
  })

  it("unterscheidet „keine Boards“ von „der Filter zeigt nichts“", () => {
    const html = sidebar([board(1)], "p-alpha")
    expect(html).toContain(de.boards_empty_filtered)
    expect(html).toContain(`>${de.boards_show_all}</button>`)
    expect(html).not.toContain(de.boards_empty)
    expect(html).not.toContain("Board 1")
  })

  it("zeigt nur die Boards des gewählten Projekts", () => {
    const html = sidebar([board(1, { project_id: "p-alpha" }), board(2)], "p-alpha")
    expect(html).toContain("Board 1")
    expect(html).not.toContain("Board 2")
  })

  it("nennt bei „Alle Projekte“ das Projekt am Board", () => {
    const html = sidebar([board(1, { project_id: "p-alpha" }), board(2), board(3, { project_id: "p-weg" })])
    expect(html).toMatch(/Board 1<\/span><span[^>]*>Alpha</)
    expect(html).toMatch(/Board 3<\/span><span[^>]*>Unbekanntes Projekt</)
    expect(html).not.toMatch(/Board 2<\/span><span[^>]*>/)
  })

  it("markiert Boards mit offenem Vorschlag", () => {
    expect(sidebar([board(1, { has_proposal: true })])).toContain(de.has_proposal)
    expect(sidebar([board(2)])).not.toContain(de.has_proposal)
  })

  it("ohne Projekte gibt es keinen Projektfilter", () => {
    expect(sidebar([board(1)], "all", [])).not.toContain("<select")
    expect(sidebar([board(1)])).toContain("<select")
    expect(sidebar([board(1)])).toContain(`>${de.no_project}</option>`)
  })
})

describe("NodePalette", () => {
  it("lässt sich nur ziehen, wenn die Zeichenfläche bearbeitbar ist", () => {
    expect(renderToStaticMarkup(<NodePalette disabled={false} />)).toContain('draggable="true"')
    const off = renderToStaticMarkup(<NodePalette disabled />)
    expect(off).not.toContain('draggable="true"')
    expect(off).toContain('aria-disabled="true"')
  })
})

describe("ChatNotice", () => {
  const AGENT = { id: "agent-1", name: "Projekt-Agent" }
  const info = (over: Partial<ChatInfo> = {}): ChatInfo =>
    ({ agent: AGENT, reason: null, can_start: true, tools_missing: [], ...over })
  const notice = (over: Partial<Parameters<typeof ChatNotice>[0]> = {}) =>
    renderToStaticMarkup(
      <ChatNotice info={info()} intro={null} showIntro={false} isAdmin={false} busy={false} failed={false}
        copied="" t={t} onAddTools={noop} onCopy={noop} onToggleIntro={noop} {...over} />,
    )

  it("schweigt, wenn alles da ist und kein Einstiegstext vorliegt", () => {
    expect(notice()).toBe("")
  })

  it("nennt je Grund, warum es keinen Chat gibt", () => {
    for (const reason of ["no_project", "project_missing", "no_agent", "read_only"] as const) {
      const html = notice({ info: info({ agent: null, reason, can_start: false }) })
      expect(html, reason).toContain(de[`chat_reason_${reason}`])
    }
  })

  it("meldet fehlende Werkzeuge; nur Admins bekommen den Knopf", () => {
    const missing = info({ tools_missing: ["blueprint_propose", "idea_read"] })
    const user = notice({ info: missing })
    expect(user).toContain("blueprint_propose, idea_read")
    expect(user).toContain(de.chat_tools_ask_admin)
    expect(user).not.toContain("<button")
    const admin = notice({ info: missing, isAdmin: true })
    expect(admin).toContain(`${de.chat_tools_add}</button>`)
    expect(admin).not.toContain(de.chat_tools_ask_admin)
    expect(notice({ info: missing, isAdmin: true, busy: true })).toContain('disabled=""')
  })

  it("sagt, warum sich die Werkzeuge nicht ergänzen ließen, und nennt das nicht einen Fehler beim Öffnen", () => {
    const missing = info({ tools_missing: ["blueprint_propose"] })
    const reason = "Dieser Agent wird von einem Modul verwaltet."
    const html = notice({ info: missing, isAdmin: true, toolsError: reason })
    expect(html).toMatch(new RegExp(`role="alert"[^>]*>${reason}`))
    expect(html).not.toContain(de.chat_failed)
    // Der Knopf bleibt: Der Admin kann es nach einer Störung erneut versuchen.
    expect(html).toContain(`${de.chat_tools_add}</button>`)
    expect(notice({ info: missing, isAdmin: true })).not.toContain('role="alert"')
  })

  it("zeigt den Einstiegstext zum Kopieren und sagt, wozu er dient", () => {
    const html = notice({ intro: "Ich arbeite am Board „Admin“ (ID 7).", showIntro: true })
    expect(html).toContain(de.chat_intro_hint)
    expect(html).toContain("Ich arbeite am Board „Admin“ (ID 7).")
    expect(html).toContain(`${de.chat_intro_copy}</button>`)
    expect(notice({ intro: "Text", showIntro: true, copied: "ok" })).toContain(`${de.copied}</button>`)
    expect(notice({ intro: "Text", showIntro: true, copied: "fail" })).toContain(`${de.copy_failed}</button>`)
  })

  it("klappt den Einstiegstext ein, lässt ihn aber erreichbar", () => {
    const html = notice({ intro: "Geheimer Rest", showIntro: false })
    expect(html).toContain(`${de.chat_intro_show}</button>`)
    expect(html).not.toContain("Geheimer Rest")
  })

  it("meldet einen Fehler beim Öffnen", () => {
    expect(notice({ info: null, failed: true })).toMatch(new RegExp(`role="alert"[^>]*>${de.chat_failed}`))
  })

  it("gibt Namen aus dem Einstiegstext als Text aus, nicht als HTML", () => {
    const html = notice({ intro: 'Board „<img src=x onerror="alert(1)">“', showIntro: true })
    expect(html).not.toContain("<img")
    expect(html).toContain("&lt;img")
  })
})
