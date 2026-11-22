// Review #456: Scheitert nur das Laden der fremden Tasks, bleiben die eigenen sichtbar.
import { describe, expect, it, vi } from "vitest"

const list = vi.hoisted(() => vi.fn())
vi.mock("./api", () => ({ tasksApi: { list } }))
import { loadForeign } from "./useTasks"

describe("loadForeign", () => {
  it("liefert nur fremde Zeilen mit Projekt-Zuordnung", async () => {
    list.mockResolvedValueOnce([{ id: "t-1" }, { foreign: true, item_id: "f-1" }])
    expect(await loadForeign("open", "p-dev")).toEqual([{ foreign: true, item_id: "f-1" }])
    expect(list).toHaveBeenLastCalledWith({ status: "open", project_id: "p-dev", include_foreign: true })
  })
  it("Fehler beim Laden der fremden → leer statt Ausnahme", async () => {
    list.mockRejectedValueOnce(new Error("Hub langsam"))
    await expect(loadForeign(undefined, null)).resolves.toEqual([])
  })
})
