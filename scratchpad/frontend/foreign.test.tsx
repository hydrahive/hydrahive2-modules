// Fremde Ideen anderer Instanzen (Gemeinsame Taskpflege, Spec federation-shared-tasks.md §Oberfläche, AK G3):
// Abzeichen, Filter-Standard „Alle Instanzen“ (gemerkt), Projekt-/Statusfilter auch für fremde,
// Detail-Zustände, keine Knöpfe zum Ändern.
import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: {} }))
vi.mock("@/features/chat/Markdown", () => ({ Markdown: ({ text }: { text: string }) => <div>{text}</div> }))
import { ForeignBadge } from "./components/ForeignBadge"
import { ForeignIdeaDetail } from "./components/ForeignIdeaDetail"
import { IdeaList } from "./components/IdeaList"
import { SCOPE_KEY, detailState, isForeignId, loadScope, saveScope, splitList, toForeignItem } from "./foreign"
import { countByStatus, filterIdeas, sortIdeas } from "./ideaView"
import { de, type T } from "./texts.de"
import { en } from "./texts.en"
import type { ForeignIdea, ForeignIdeaFull, IdeaListItem } from "./types"

const tr = (texts: Record<string, string>): T => (key, vars) =>
  (texts[key] ?? key).replace(/\{\{(\w+)\}\}/g, (_m, name: string) => String(vars?.[name] ?? ""))
const t = tr(de)
const PROJECTS = [{ id: "p-dev", name: "Hydrahive DEV" }]
const noop = () => undefined

function foreign(over: Partial<ForeignIdea> = {}): ForeignIdea {
  return {
    foreign: true, origin_fp: "fp-home", origin_name: "hydrahome", item_id: "f-1", owner: "alice",
    title: "Fremde Idee", status: "new", project_id: "o-dev", project_name: "Hydrahive DEV", local_project_id: "p-dev",
    created_at: "2026-11-20T10:00:00Z", updated_at: "2026-11-21T10:00:00Z", origin_last_seen: "2026-11-22T10:00:00Z",
    stale: false, ...over,
  }
}

function own(id: string, over: Partial<IdeaListItem> = {}): IdeaListItem {
  return { id, project_id: null, title: `Eigen ${id}`, status: "new", origin: "user", task_id: null, board_id: null,
    created_at: "2026-11-12T08:00:00.000000Z", updated_at: "2026-11-12T08:00:00.000000Z", body_preview: "", note_count: 0, ...over }
}

function full(over: Partial<ForeignIdeaFull> = {}): ForeignIdeaFull {
  return { item: {}, content: { body: "Der Ideentext", notes: [
    { author: "agent", agent_name: "Buddy", body: "Eine Anmerkung", created_at: "2026-11-21T09:00:00Z" }] },
  source: "live", origin_offline: false, snapshot_at: null, last_seen: "2026-11-22T10:00:00Z", hub_unreachable: false, ...over }
}

function memory(initial: Record<string, string> = {}) {
  const data = { ...initial }
  return { getItem: (k: string) => data[k] ?? null, setItem: (k: string, v: string) => { data[k] = v }, data }
}

const list = (ideas: IdeaListItem[], project = "all", status = "all", scope: "all" | "local" | undefined = "all") =>
  renderToStaticMarkup(<IdeaList ideas={ideas} projects={PROJECTS} project={project} status={status as never} activeId={null}
    loading={false} locale="de" t={t} onProject={noop} onStatus={noop} onSelect={noop} scope={scope} onScope={noop} />)

beforeEach(() => vi.unstubAllGlobals())

describe("Herkunftsabzeichen", () => {
  it("Instanzname mit Tooltip „Stand vom …, zuletzt gesehen am …“", () => {
    const h = renderToStaticMarkup(<ForeignBadge idea={foreign()} locale="de" t={t} />)
    expect(h).toContain("hydrahome")
    expect(h).toMatch(/title="Stand vom [^"]+, zuletzt gesehen am [^"]+"/)
    expect(h).toContain('data-stale="0"')
  })
  it("stale: grau mit „nicht aktuell“, englisch „not current“", () => {
    expect(renderToStaticMarkup(<ForeignBadge idea={foreign({ stale: true })} locale="de" t={t} />)).toContain("nicht aktuell")
    const h = renderToStaticMarkup(<ForeignBadge idea={foreign({ stale: true })} locale="en" t={tr(en)} />)
    expect(h).toContain("not current")
    expect(h).toContain('data-stale="1"')
  })
})

describe("Filter „Nur diese / Alle Instanzen“", () => {
  it("Standard „Alle Instanzen“, eigener Schlüssel, Auswahl bleibt", () => {
    expect(SCOPE_KEY).toBe("hh.scratchpad.instances")
    expect(loadScope(memory())).toBe("all")
    expect(loadScope(null)).toBe("all")
    expect(loadScope({ getItem: () => { throw new Error("gesperrt") } })).toBe("all")
    const store = memory()
    saveScope("local", store)
    expect(loadScope(store)).toBe("local")
    expect(loadScope(memory({ "hh.tasks.instances": "local" }))).toBe("all")   // eigener Schlüssel je Modul
  })
  it("Chip in der Liste zeigt die Auswahl", () => {
    expect(list([], "all", "all", "all")).toContain("Alle Instanzen")
    expect(list([], "all", "all", "local")).toContain("Nur diese Instanz")
  })
})

describe("Fremde Ideen in der Liste", () => {
  it("Abzeichen und „gehört zu …“ in der Zeile", () => {
    const h = list([own("a1b2c3d4"), toForeignItem(foreign())])
    expect(h).toContain("Fremde Idee")
    expect(h).toContain("gehört zu hydrahome")
    expect(h).toContain('data-testid="foreign-badge"')
  })
  it("Projekt- und Statusfilter gelten auch für fremde (AK G3)", () => {
    const rows = [own("a1b2c3d4", { project_id: "p-dev" }), toForeignItem(foreign()),
      toForeignItem(foreign({ item_id: "f-2", status: "done" })), toForeignItem(foreign({ item_id: "f-3", local_project_id: null }))]
    expect(filterIdeas(rows, "p-dev", "open").map((i) => i.title)).toEqual(["Eigen a1b2c3d4", "Fremde Idee"])
    expect(filterIdeas(rows, "none", "all").map((i) => i.id)).toEqual(["f:fp-home:f-3"])
    expect(countByStatus(rows, "p-dev")).toMatchObject({ new: 2, done: 1 })
  })
  it("Liste trennt eigene und fremde, sortiert neueste zuerst, fremde IDs unverwechselbar", () => {
    const rows = sortIdeas(splitList([own("a1b2c3d4", { updated_at: "2026-11-21T10:00:00.500000Z" }), foreign()]))
    expect(rows.map((r) => r.id)).toEqual(["a1b2c3d4", "f:fp-home:f-1"])     // gleiche Sekunde: eigene mit Mikrosekunden zuerst
    expect(isForeignId(rows[1].id)).toBe(true)
    expect(isForeignId(rows[0].id)).toBe(false)
  })
})

describe("Detailansicht einer fremden Idee", () => {
  const render = (f: ForeignIdeaFull | null, texts = de) =>
    renderToStaticMarkup(<ForeignIdeaDetail idea={foreign()} locale="de" t={tr(texts)} initial={f} />)

  it("live: Ideentext und Anmerkungen, keine Knöpfe zum Ändern", () => {
    const h = render(full())
    expect(detailState(full())).toBe("live")
    expect(h).toContain('data-state="live"')
    expect(h).toContain("Der Ideentext")
    expect(h).toContain("Eine Anmerkung")
    expect(h).toContain("gehört zu hydrahome")
    for (const verboten of ["<select", "<textarea", "<input", "<button", de.delete_yes, de.note_delete]) {
      expect(h).not.toContain(verboten)
    }
  })
  it("Snapshot: „Stand vom …“ mit Text", () => {
    const h = render(full({ source: "snapshot", origin_offline: true, snapshot_at: "2026-11-21T08:00:00Z" }))
    expect(h).toContain('data-state="snapshot"')
    expect(h).toMatch(/Stand vom \d/)
    expect(h).toContain("Der Ideentext")
  })
  it("Ursprung offline ohne Snapshot: „hydrahome zuletzt gesehen am …“", () => {
    const h = render(full({ source: "none", origin_offline: true, content: null }))
    expect(h).toContain('data-state="origin_offline"')
    expect(h).toMatch(/hydrahome zuletzt gesehen am \d/)
  })
  it("Hub nicht erreichbar, englisch „Hub unreachable“", () => {
    const f = full({ source: "metadata", origin_offline: true, content: null, hub_unreachable: true })
    expect(render(f)).toContain("Hub nicht erreichbar")
    expect(render(f, en)).toContain("Hub unreachable")
  })
  it("lädt noch: Ladehinweis", () => {
    expect(render(null)).toContain("Ideentext wird geladen")
  })
})
