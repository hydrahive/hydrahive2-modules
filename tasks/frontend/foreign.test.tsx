// Fremde Tasks anderer Instanzen (Gemeinsame Taskpflege, Spec federation-shared-tasks.md §Oberfläche):
// Abzeichen, Filter-Standard „Alle Instanzen“ (gemerkt), Detail-Zustände, keine Bearbeiten-Knöpfe.
import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", async () => await import("./i18nMock"))
vi.mock("@/shared/api-client", () => ({ api: {} }))
const state = vi.hoisted(() => ({ items: [] as unknown[], opts: [] as Record<string, unknown>[] }))
vi.mock("./useTasks", () => ({
  useTasks: (opts: Record<string, unknown>) => {
    state.opts.push(opts)
    return { tasks: [], items: state.items, loading: false, error: null, createTask: () => undefined,
      updateTask: () => undefined, deleteTask: () => undefined }
  },
}))
import { ForeignBadge } from "./components/ForeignBadge"
import { ForeignDetail } from "./components/ForeignDetail"
import { ForeignTaskRow } from "./components/ForeignTaskRow"
import { TaskPanel } from "./components/TaskPanel"
import { SCOPE_KEY, detailState, loadScope, mergeSorted, saveScope } from "./foreign"
import { setLang } from "./i18nMock"
import type { ForeignTask, ForeignTaskFull, Task } from "./types"

function foreign(over: Partial<ForeignTask> = {}): ForeignTask {
  return {
    foreign: true, origin_fp: "fp-home", origin_name: "hydrahome", kind: "task", item_id: "f-1", owner: "alice",
    title: "Fremder Task", status: "open", priority: "medium", project_id: "o-dev", project_name: "Hydrahive DEV",
    created_at: "2026-11-20T10:00:00Z", updated_at: "2026-11-21T10:00:00Z",
    origin_last_seen: "2026-11-22T10:00:00Z", stale: false, pending_edits: 0, local_project_id: "p-dev", ...over,
  }
}

function full(over: Partial<ForeignTaskFull> = {}): ForeignTaskFull {
  return { item: {}, content: { description: "Der ganze Text" }, source: "live", origin_offline: false,
    snapshot_at: null, last_seen: "2026-11-22T10:00:00Z", hub_unreachable: false, ...over }
}

function memory(initial: Record<string, string> = {}) {
  const data = { ...initial }
  return { getItem: (k: string) => data[k] ?? null, setItem: (k: string, v: string) => { data[k] = v }, data }
}

let store = memory()

beforeEach(() => {
  setLang("de")
  state.items = []
  state.opts = []
  store = memory()                                  // Testumgebung ohne DOM: eigenes localStorage
  vi.stubGlobal("window", { localStorage: store })
})

describe("Herkunftsabzeichen", () => {
  it("zeigt den Instanznamen mit Tooltip „Stand vom …, zuletzt gesehen am …“", () => {
    const h = renderToStaticMarkup(<ForeignBadge task={foreign()} />)
    expect(h).toContain("hydrahome")
    expect(h).toMatch(/title="Stand vom [^"]+, zuletzt gesehen am [^"]+"/)
    expect(h).toContain('data-stale="0"')
    expect(h).not.toContain("nicht aktuell")
  })
  it("stale: grau mit „nicht aktuell“", () => {
    const h = renderToStaticMarkup(<ForeignBadge task={foreign({ stale: true })} />)
    expect(h).toContain('data-stale="1"')
    expect(h).toContain("nicht aktuell")
    expect(h).toContain("text-[#9aa7bc]")
  })
  it("englisch", () => {
    setLang("en")
    const h = renderToStaticMarkup(<ForeignBadge task={foreign({ stale: true })} />)
    expect(h).toContain("not current")
    expect(h).toMatch(/title="As of [^"]+, last seen [^"]+"/)
  })
})

describe("Filter „Nur diese / Alle Instanzen“", () => {
  it("Standard ist „Alle Instanzen“, auch ohne gespeicherte Auswahl", () => {
    expect(loadScope(memory())).toBe("all")
    expect(loadScope(null)).toBe("all")
    expect(loadScope({ getItem: () => { throw new Error("gesperrt") } })).toBe("all")
  })
  it("gemerkte Auswahl „Nur diese Instanz“ bleibt", () => {
    const store = memory()
    saveScope("local", store)
    expect(store.data[SCOPE_KEY]).toBe("local")
    expect(loadScope(store)).toBe("local")
  })
  it("TaskPanel lädt standardmäßig fremde Einträge und zeigt den Chip „Alle Instanzen“", () => {
    const h = renderToStaticMarkup(<TaskPanel projectId="p-dev" />)
    expect(h).toContain('data-scope="all"')
    expect(h).toContain("Alle Instanzen")
    expect(state.opts.at(-1)).toMatchObject({ includeForeign: true, foreignProjectId: "p-dev" })
  })
  it("TaskPanel mit gemerkter Auswahl „Nur diese Instanz“ lädt keine fremden", () => {
    store.setItem(SCOPE_KEY, "local")
    const h = renderToStaticMarkup(<TaskPanel projectId="p-dev" />)
    expect(h).toContain("Nur diese Instanz")
    expect(state.opts.at(-1)).toMatchObject({ includeForeign: false })
  })
})

describe("Fremde Zeile im TaskPanel", () => {
  it("Abzeichen, „gehört zu …“, kein Löschen, kein Statuswechsel", () => {
    state.items = [foreign()]
    const h = renderToStaticMarkup(<TaskPanel />)
    expect(h).toContain('data-testid="foreign-row"')
    expect(h).toContain("gehört zu hydrahome")
    expect(h).not.toContain("Task löschen")
    expect(h).not.toContain("<select")
    expect(h).not.toContain("Als erledigt markieren")
  })
  it("eigene und fremde stehen in derselben Liste", () => {
    const own: Task = { id: "t-1", username: "alice", project_id: null, session_id: null, title: "Eigen",
      description: "", status: "open", priority: "high", created_at: "2026-11-25T00:00:00Z",
      updated_at: "2026-11-25T00:00:00Z" }
    state.items = [own, foreign()]
    const h = renderToStaticMarkup(<TaskPanel />)
    expect(h).toContain("Eigen")
    expect(h).toContain("Fremder Task")
    expect(h).toContain("Task löschen")                       // nur an der eigenen Zeile
  })
  it("sortiert wie eigene: Priorität, dann angelegt", () => {
    const own: Task = { id: "t-1", username: "alice", project_id: null, session_id: null, title: "Eigen",
      description: "", status: "open", priority: "medium", created_at: "2026-11-25T00:00:00Z",
      updated_at: "2026-11-25T00:00:00Z" }
    const merged = mergeSorted([own], [foreign({ item_id: "f-low", priority: "low" }), foreign({ item_id: "f-high", priority: "high" })])
    expect(merged.map((t) => ("item_id" in t ? t.item_id : t.id))).toEqual(["f-high", "t-1", "f-low"])
  })
})

describe("Detailansicht", () => {
  const render = (f: ForeignTaskFull) =>
    renderToStaticMarkup(<ForeignTaskRow task={foreign()} initialOpen initialFull={f} />)

  it("live: Volltext ohne Hinweis", () => {
    const h = render(full())
    expect(detailState(full())).toBe("live")
    expect(h).toContain('data-state="live"')
    expect(h).toContain("Der ganze Text")
  })
  it("Ursprung offline mit Snapshot: „Stand vom …“", () => {
    const f = full({ source: "snapshot", origin_offline: true, snapshot_at: "2026-11-21T08:00:00Z" })
    const h = render(f)
    expect(h).toContain('data-state="snapshot"')
    expect(h).toMatch(/Stand vom \d/)
    expect(h).toContain("Der ganze Text")
  })
  it("Ursprung offline ohne Snapshot: „hydrahome zuletzt gesehen am …“", () => {
    const h = render(full({ source: "none", origin_offline: true, content: null }))
    expect(h).toContain('data-state="origin_offline"')
    expect(h).toMatch(/hydrahome zuletzt gesehen am \d/)
  })
  it("Hub nicht erreichbar: Metadaten mit Hinweis", () => {
    const h = render(full({ source: "metadata", origin_offline: true, content: null, hub_unreachable: true }))
    expect(h).toContain('data-state="hub_unreachable"')
    expect(h).toContain("Hub nicht erreichbar")
  })
  it("englisch: Hub unreachable", () => {
    setLang("en")
    const h = renderToStaticMarkup(<ForeignDetail task={foreign()} initial={full({ source: "metadata", content: null, hub_unreachable: true })} />)
    expect(h).toContain("Hub unreachable")
  })
  it("lädt noch: Ladehinweis", () => {
    const h = renderToStaticMarkup(<ForeignDetail task={foreign()} initial={null} />)
    expect(h).toContain("Volltext wird geladen")
  })
})
