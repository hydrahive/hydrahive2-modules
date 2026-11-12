import { describe, expect, it } from "vitest"
import { filterBoards, linkedBoard, mergeBoard, pickBoard, projectName, projectShowing } from "./boardView"
import { de, type T } from "./texts.de"
import type { Board, BoardListItem } from "./types"

const t: T = (key) => de[key]

describe("Direktlink und Projektfilter", () => {
  const board = (id: number, project_id: string | null): BoardListItem =>
    ({ id, name: `Board ${id}`, project_id, created_at: "", updated_at: "", has_proposal: false })

  it("liest nur eine saubere Board-ID aus dem Verweis", () => {
    expect(linkedBoard("12")).toBe(12)
    for (const bad of ["", " ", "abc", "1.5", "-3", "0", "12abc", "99999999999999999999", null, undefined]) {
      expect(linkedBoard(bad), String(bad)).toBeNull()
    }
  })

  it("filtert nach Projekt, „ohne Projekt“ und „alle“", () => {
    const boards = [board(1, "p-a"), board(2, null), board(3, "p-b")]
    expect(filterBoards(boards, "all").map((b) => b.id)).toEqual([1, 2, 3])
    expect(filterBoards(boards, "none").map((b) => b.id)).toEqual([2])
    expect(filterBoards(boards, "p-a").map((b) => b.id)).toEqual([1])
  })

  it("öffnet den Filter nur, wenn er das verlinkte Board ausblenden würde", () => {
    expect(projectShowing(board(1, "p-a"), "p-a")).toBe("p-a")
    expect(projectShowing(board(1, "p-a"), "all")).toBe("all")
    expect(projectShowing(board(1, "p-a"), "p-b")).toBe("all")
    expect(projectShowing(board(2, null), "none")).toBe("none")
    expect(projectShowing(board(2, null), "p-a")).toBe("all")
  })

  it("nennt das Projekt eines Boards", () => {
    const projects = [{ id: "p-a", name: "Alpha" }]
    expect(projectName("p-a", projects, t)).toBe("Alpha")
    expect(projectName(null, projects, t)).toBe(de.no_project)
    expect(projectName("p-weg", projects, t)).toBe(de.unknown_project)
  })

  it("öffnet das verlinkte Board, sonst das erste", () => {
    const boards = [board(4, null), board(2, "p-a")]
    expect(pickBoard(boards, 2)).toBe(2)
    expect(pickBoard(boards, null)).toBe(4)
    expect(pickBoard(boards, 99)).toBe(4)  // das verlinkte Board gibt es nicht
    expect(pickBoard([], 2)).toBeNull()
  })

  it("trägt den Stand eines offenen Boards in die Liste ein", () => {
    const list = [board(1, null), board(2, "p-a")]
    const open: Board = {
      ...list[0], name: "Umbenannt", project_id: "p-a", updated_at: "später", revision: 4, graph_json: "",
      proposal_json: "{}", proposal_note: null, proposal_at: "jetzt",
    }
    const merged = mergeBoard(list, open)
    expect(merged[0]).toMatchObject({ name: "Umbenannt", project_id: "p-a", has_proposal: true, updated_at: "später" })
    expect(merged[1]).toBe(list[1])
    // Ändert sich für die Liste nichts (jedes Speichern meldet den Stand), bleibt es dieselbe Liste.
    expect(mergeBoard(merged, { ...open, revision: 5, updated_at: "noch später" })).toBe(merged)
    expect(mergeBoard(merged, { ...open, id: 99 })).toBe(merged)
  })
})
