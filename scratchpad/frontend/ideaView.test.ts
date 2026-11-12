import { describe, expect, it } from "vitest"
import {
  countByStatus, filterIdeas, formatStamp, groupByProject, linkedIdea, openCount, parseStamp, projectShowing, relativeTime,
  sortIdeas, statusShowing, toListItem, upsertIdea, validProject,
} from "./ideaView"
import type { Idea, IdeaListItem } from "./types"

function item(id: string, over: Partial<IdeaListItem> = {}): IdeaListItem {
  return {
    id, project_id: null, title: `Idee ${id}`, status: "new", origin: "user", task_id: null, board_id: null,
    created_at: "2026-11-12T08:00:00.000000Z", updated_at: "2026-11-12T08:00:00.000000Z",
    body_preview: "", note_count: 0, ...over,
  }
}

const PROJECTS = [{ id: "p-zebra", name: "Zebra" }, { id: "p-alpha", name: "alpha" }]

describe("sortIdeas", () => {
  it("zeigt die neueste Änderung zuerst und ändert die Eingabe nicht", () => {
    const list = [
      item("a", { updated_at: "2026-11-12T08:00:00.000001Z" }),
      item("b", { updated_at: "2026-11-12T09:00:00.000000Z" }),
      item("c", { updated_at: "2026-11-12T08:00:00.000002Z" }),
    ]
    expect(sortIdeas(list).map((i) => i.id)).toEqual(["b", "c", "a"])
    expect(list.map((i) => i.id)).toEqual(["a", "b", "c"])
  })
})

describe("filterIdeas", () => {
  const list = [
    item("a", { project_id: "p-alpha" }),
    item("b", { project_id: "p-zebra", status: "done" }),
    item("c", { status: "parked" }),
    item("d", { status: "planned" }),
  ]
  const ids = (project: string, status: Parameters<typeof filterIdeas>[2]) =>
    filterIdeas(list, project, status).map((i) => i.id)

  it("filtert nach Projekt, ohne Projekt und allen", () => {
    expect(ids("all", "all")).toEqual(["a", "b", "c", "d"])
    expect(ids("p-alpha", "all")).toEqual(["a"])
    expect(ids("none", "all")).toEqual(["c", "d"])
  })
  it("offen heißt Neu, Wird geprüft und Geplant", () => {
    expect(ids("all", "open")).toEqual(["a", "d"])
    expect(ids("all", "parked")).toEqual(["c"])
    expect(ids("p-zebra", "open")).toEqual([])
  })
})

describe("countByStatus", () => {
  const list = [item("a", { project_id: "p-alpha" }), item("b", { status: "done" }), item("c"), item("d", { status: "review" })]

  it("zählt je Status innerhalb des Projektfilters und kennt jeden Status", () => {
    const all = countByStatus(list, "all")
    expect(all).toEqual({ new: 2, review: 1, planned: 0, parked: 0, done: 1, dropped: 0 })
    expect(countByStatus(list, "p-alpha").new).toBe(1)
    expect(countByStatus(list, "none")).toMatchObject({ new: 1, review: 1, done: 1 })
  })
  it("zählt offene zusammen", () => {
    expect(openCount(countByStatus(list, "all"))).toBe(3)
  })
})

describe("groupByProject", () => {
  it("ordnet Projekte nach Name, unbekannte danach, ohne Projekt zuletzt", () => {
    const groups = groupByProject([
      item("frei"), item("z", { project_id: "p-zebra" }), item("weg", { project_id: "p-geloescht" }),
      item("a1", { project_id: "p-alpha" }), item("a2", { project_id: "p-alpha" }),
    ], PROJECTS)
    expect(groups.map((g) => [g.projectId, g.name, g.known])).toEqual([
      ["p-alpha", "alpha", true], ["p-zebra", "Zebra", true], ["p-geloescht", null, false], [null, null, true],
    ])
    expect(groups[0].ideas.map((i) => i.id)).toEqual(["a1", "a2"])
  })
  it("liefert keine leeren Gruppen", () => {
    expect(groupByProject([], PROJECTS)).toEqual([])
    expect(groupByProject([item("frei")], PROJECTS)).toHaveLength(1)
  })
})

describe("upsertIdea", () => {
  it("ersetzt eine vorhandene Idee und sortiert neu", () => {
    const list = [item("a", { updated_at: "2026-11-12T09:00:00.000000Z" }), item("b")]
    const next = upsertIdea(list, item("b", { title: "Neu", updated_at: "2026-11-12T10:00:00.000000Z" }))
    expect(next.map((i) => [i.id, i.title])).toEqual([["b", "Neu"], ["a", "Idee a"]])
  })
  it("fügt eine neue Idee hinzu", () => {
    expect(upsertIdea([item("a")], item("b", { updated_at: "2026-11-12T10:00:00.000000Z" })).map((i) => i.id)).toEqual(["b", "a"])
  })
})

describe("toListItem", () => {
  it("macht aus der Vollansicht eine Listenzeile", () => {
    const idea: Idea = {
      ...item("a"), body: "Erste Zeile\n\n  zweite   Zeile " + "x".repeat(300),
      notes: [{ id: 1, idea_id: "a", author: "agent", agent_name: "Buddy", body: "Hinweis", created_at: "" }],
      task: { id: "t-1", short_id: "t-1", title: "Task", status: "open", missing: false },
    }
    const row = toListItem(idea)
    expect(row.note_count).toBe(1)
    expect(row.body_preview.startsWith("Erste Zeile zweite Zeile x")).toBe(true)
    expect(row.body_preview.length).toBe(160)
    expect("body" in row).toBe(false)
    expect("notes" in row).toBe(false)
    expect("task" in row).toBe(false)
  })
})

describe("validProject", () => {
  it("lässt nur Projekte zu, die es noch gibt", () => {
    expect(validProject("p-alpha", PROJECTS)).toBe("p-alpha")
    expect(validProject("p-geloescht", PROJECTS)).toBe("")
    expect(validProject(null, PROJECTS)).toBe("")
    expect(validProject("", PROJECTS)).toBe("")
  })
})

describe("parseStamp", () => {
  it("liest Zeitstempel mit Mikrosekunden", () => {
    expect(parseStamp("2026-11-12T08:15:30.123456Z")?.toISOString()).toBe("2026-11-12T08:15:30.123Z")
    expect(parseStamp("2026-11-12T08:15:30Z")?.toISOString()).toBe("2026-11-12T08:15:30.000Z")
  })
  it("liefert bei Unsinn null", () => {
    expect(parseStamp("")).toBeNull()
    expect(parseStamp("gestern")).toBeNull()
  })
})

describe("relativeTime", () => {
  const now = Date.parse("2026-11-12T10:00:00Z")
  const at = (stamp: string, locale = "de") => relativeTime(stamp, locale, now)

  it("nennt Minuten, Stunden und Tage", () => {
    expect(at("2026-11-12T09:58:00.000000Z")).toBe("vor 2 Minuten")
    expect(at("2026-11-12T08:00:00.000000Z")).toBe("vor 2 Stunden")
    expect(at("2026-11-11T10:00:00.000000Z")).toBe("gestern")
    expect(at("2026-11-09T10:00:00.000000Z")).toBe("vor 3 Tagen")
    expect(at("2026-11-12T08:00:00.000000Z", "en-US")).toBe("2 hours ago")
  })
  it("zeigt ab 30 Tagen das Datum", () => {
    expect(at("2026-09-26T18:05:00.000000Z")).toContain("2026")
    expect(at("2026-09-26T18:05:00.000000Z")).not.toContain("vor")
  })
  it("zeigt bei Unsinn einen Strich", () => {
    expect(at("")).toBe("—")
  })
})

describe("formatStamp", () => {
  it("zeigt Datum und Uhrzeit, bei Unsinn einen Strich", () => {
    expect(formatStamp("2026-11-12T08:15:30.123456Z", "de")).toMatch(/2026.*\d{2}:\d{2}/)
    expect(formatStamp("2026-11-12T08:15:30.123456Z", "en")).toContain("2026")
    expect(formatStamp("gestern", "de")).toBe("—")
  })
})

describe("Direktlink /scratchpad?idea=<id>", () => {
  it("nimmt eine ID aus der Adresse", () => {
    expect(linkedIdea("aaaa1111-0000-4000-8000-000000000001")).toBe("aaaa1111-0000-4000-8000-000000000001")
    expect(linkedIdea("  aaaa1111  ")).toBe("aaaa1111")
  })

  it("verwirft Leeres und alles, was keine ID sein kann", () => {
    for (const bad of [null, "", "   ", "kurz", "../../etc/passwd", "a".repeat(65), "aaaa1111?x=1"]) {
      expect(linkedIdea(bad)).toBeNull()
    }
  })

  it("lässt Filter stehen, die die Idee schon zeigen", () => {
    const idea = item("a", { project_id: "p-alpha", status: "planned" })
    expect(projectShowing(idea, "p-alpha")).toBe("p-alpha")
    expect(projectShowing(idea, "all")).toBe("all")
    expect(statusShowing(idea, "open")).toBe("open")
    expect(statusShowing(idea, "planned")).toBe("planned")
    expect(statusShowing(idea, "all")).toBe("all")
  })

  it("öffnet Filter, die die Idee verstecken würden", () => {
    const idea = item("a", { project_id: "p-alpha", status: "done" })
    expect(projectShowing(idea, "none")).toBe("all")
    expect(projectShowing(idea, "p-beta")).toBe("all")
    expect(statusShowing(idea, "open")).toBe("all")
    expect(statusShowing(idea, "parked")).toBe("all")
    expect(statusShowing(item("b", { status: "review" }), "done")).toBe("open")
  })
})
