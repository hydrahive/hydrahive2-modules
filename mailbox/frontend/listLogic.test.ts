import { describe, expect, it } from "vitest"
import { keyAction, nextId, selectionFlags, toggle, toggleAll } from "./listLogic"

describe("Mehrfachauswahl", () => {
  it("an/aus je Mail, alle an/aus", () => {
    expect([...toggle(new Set([1]), 2)]).toEqual([1, 2])
    expect([...toggle(new Set([1, 2]), 1)]).toEqual([2])
    expect([...toggleAll(new Set(), [1, 2, 3])].sort()).toEqual([1, 2, 3])
    expect([...toggleAll(new Set([1, 2, 3]), [1, 2, 3])]).toEqual([])
    expect([...toggleAll(new Set([1]), [1, 2])].sort()).toEqual([1, 2])   // teilweise → alle
  })

  it("welche Sammel-Aktionen: gelesen wenn eine ungelesen ist, markieren wenn eine unmarkiert ist", () => {
    const items = [{ id: 1, seen: 1, flagged: 0, deleted_on_server: 0 }, { id: 2, seen: 0, flagged: 1, deleted_on_server: 0 }]
    expect(selectionFlags(items, new Set([1, 2]))).toEqual({ anyUnseen: true, anyUnflagged: true, onServer: 2 })
    expect(selectionFlags(items, new Set([1]))).toEqual({ anyUnseen: false, anyUnflagged: true, onServer: 1 })
    const arch = [{ id: 3, seen: 1, flagged: 0, deleted_on_server: 1 }]
    expect(selectionFlags(arch, new Set([3])).onServer).toBe(0)
  })
})

describe("Tastenkürzel", () => {
  it("j/k bewegen in der Liste, an den Enden bleiben", () => {
    expect(nextId([5, 6, 7], 6, 1)).toBe(7)
    expect(nextId([5, 6, 7], 7, 1)).toBe(7)
    expect(nextId([5, 6, 7], 5, -1)).toBe(5)
    expect(nextId([5, 6, 7], null, 1)).toBe(5)
    expect(nextId([], null, 1)).toBeNull()
  })

  it("Belegung laut Spec §6: j/k r a f e # / c", () => {
    const k = (key: string, extra = {}) => keyAction({ key, ctrlKey: false, metaKey: false, altKey: false, target: null, ...extra })
    expect([k("j"), k("k"), k("r"), k("a"), k("f"), k("e"), k("#"), k("/"), k("c")])
      .toEqual(["next", "prev", "reply", "reply_all", "forward", "archive", "delete", "search", "compose"])
    expect(k("x")).toBeNull()
  })

  it("nicht beim Tippen und nicht mit Strg/Cmd/Alt", () => {
    const input = { tagName: "INPUT", isContentEditable: false }
    const area = { tagName: "TEXTAREA", isContentEditable: false }
    const sel = { tagName: "SELECT", isContentEditable: false }
    const ce = { tagName: "DIV", isContentEditable: true }
    for (const target of [input, area, sel, ce]) {
      expect(keyAction({ key: "r", ctrlKey: false, metaKey: false, altKey: false, target })).toBeNull()
    }
    expect(keyAction({ key: "r", ctrlKey: true, metaKey: false, altKey: false, target: null })).toBeNull()
    expect(keyAction({ key: "c", ctrlKey: false, metaKey: true, altKey: false, target: null })).toBeNull()
    expect(keyAction({ key: "j", ctrlKey: false, metaKey: false, altKey: true, target: null })).toBeNull()
  })
})
