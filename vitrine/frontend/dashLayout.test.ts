import { describe, expect, it } from "vitest"
import { AREAS, DEFAULT_DASHBOARD, byPage, layoutErrors, moveArea, moveInPage, normalizeDashboard, parseRepos, toggleIn } from "./dashLayout"

describe("Anordnung der Statuszentrale", () => {
  it("ergänzt alte S2-Einstellung um Standards", () => {
    const d = normalizeDashboard({ tasks_user: "anna", github_project: "P", github_repos: [] })
    expect(d.tasks_user).toBe("anna")
    expect(d.order).toEqual([...AREAS])
    expect(d.messages_max).toBe(3)
    expect(d.mining_in_machine).toBe(true)
  })

  it("hängt fehlende Bereiche hinten an", () => {
    expect(normalizeDashboard({ order: ["machine", "messages"] }).order.slice(0, 2)).toEqual(["machine", "messages"])
    expect(normalizeDashboard({ order: ["machine"] }).order).toHaveLength(AREAS.length)
  })

  it("prüft wie der Server", () => {
    const ok = { ...DEFAULT_DASHBOARD }
    expect(layoutErrors(ok)).toEqual([])
    expect(layoutErrors({ ...ok, messages_max: 0 })).toContain("messages_max")
    expect(layoutErrors({ ...ok, messages_max: 6 })).toContain("messages_max")
    expect(layoutErrors({ ...ok, messages_max: 2.5 })).toContain("messages_max")
    expect(layoutErrors({ ...ok, order: ["messages", "messages"] })).toContain("order")
    expect(layoutErrors({ ...ok, home_rooms: ["<b>"] })).toContain("home_rooms")
    expect(layoutErrors({ ...ok, home_rooms: ["a\u0001b"] })).toContain("home_rooms")
    expect(layoutErrors({ ...ok, home_rooms: ["x".repeat(61)] })).toContain("home_rooms")
    expect(layoutErrors({ ...ok, home_rooms: ["Alex Zimmer", "Küche"] })).toEqual([])
    expect(layoutErrors({ ...ok, home_rooms: Array(21).fill("a") })).toContain("home_rooms")
    expect(layoutErrors({ ...ok, tasks_user: "a b" })).toContain("tasks_user")
    expect(layoutErrors({ ...ok, github_repos: ["a/.."] })).toContain("github_repos")
  })

  it("Seiten: Voreinstellung, Ergänzung, Prüfung", () => {
    expect(normalizeDashboard({}).pages).toEqual({ messages: 1, home: 1, hydra: 1, tasks: 2, github: 2, machine: 2, mining: 2 })
    expect(normalizeDashboard({ pages: { home: 3 } as never }).pages.home).toBe(3)
    expect(normalizeDashboard({ pages: { home: 3 } as never }).pages.messages).toBe(1)
    const ok = normalizeDashboard({})
    expect(layoutErrors({ ...ok, pages: { ...ok.pages, home: 4 } })).toContain("pages")
    expect(layoutErrors({ ...ok, pages: { ...ok.pages, home: 0 } })).toContain("pages")
    expect(layoutErrors({ ...ok, pages: { ...ok.pages, home: 1.5 } })).toContain("pages")
    expect(layoutErrors({ ...ok, pages: { ...ok.pages, laser: 1 } as never })).toContain("pages")
    expect(layoutErrors({ ...ok, pages: { ...ok.pages, mining: 3 } })).toEqual([])
  })

  it("Cockpit-Liste nach Seite, Pfeile innerhalb der Seite", () => {
    const d = normalizeDashboard({ order: ["machine", "messages", "tasks", "home", "hydra", "github", "mining"] })
    expect(byPage(d)).toEqual(["messages", "home", "hydra", "machine", "tasks", "github", "mining"])
    const up = moveInPage(d, "home", -1)
    expect(byPage({ ...d, order: up })).toEqual(["home", "messages", "hydra", "machine", "tasks", "github", "mining"])
    expect(moveInPage(d, "messages", -1)).toBe(d.order)
    expect(moveInPage(d, "hydra", 1)).toBe(d.order)
    expect(moveInPage(d, "machine", -1)).toBe(d.order)
  })

  it("Chat ist standardmäßig an und bleibt beim Ergänzen erhalten", () => {
    expect(normalizeDashboard({}).chat_enabled).toBe(true)
    expect(normalizeDashboard({ chat_enabled: false }).chat_enabled).toBe(false)
  })

  it("verschiebt und bleibt an den Rändern", () => {
    const o = [...AREAS]
    expect(moveArea(o, "home", -1).slice(0, 2)).toEqual(["home", "messages"])
    expect(moveArea(o, "messages", -1)).toBe(o)
    expect(moveArea(o, "mining", 1)).toBe(o)
  })

  it("schaltet ein und aus", () => {
    expect(toggleIn(["github"], "github")).toEqual([])
    expect(toggleIn([] as string[], "github")).toEqual(["github"])
  })

  it("liest Repos", () => { expect(parseRepos(" a/b,\nc/d ")).toEqual(["a/b", "c/d"]) })
})
