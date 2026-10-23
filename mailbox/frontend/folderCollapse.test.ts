import { describe, expect, it } from "vitest"
import { loadExpandedAccounts, saveExpandedAccounts, toggleExpandedAccount } from "./folderCollapse"

function store(initial: string | null = null) {
  let value = initial
  return {
    getItem: () => value,
    setItem: (_key: string, next: string) => { value = next },
    value: () => value,
  }
}

describe("aufgeklappte Mailkonten", () => {
  it("startet ohne gespeicherten Zustand vollständig eingeklappt", () => {
    expect([...loadExpandedAccounts(store())]).toEqual([])
  })

  it("liest nur eindeutige Konto-IDs aus dem Speicher", () => {
    const saved = store('["konto-b", 7, "konto-a", "konto-b", null]')
    expect([...loadExpandedAccounts(saved)].sort()).toEqual(["konto-a", "konto-b"])
  })

  it("fällt bei ungültigem oder nicht lesbarem Speicher sicher auf eingeklappt zurück", () => {
    expect([...loadExpandedAccounts(store("kaputt"))]).toEqual([])
    expect([...loadExpandedAccounts({ getItem: () => { throw new Error("gesperrt") } })]).toEqual([])
  })

  it("klappt ein Konto auf und wieder zu, ohne den alten Zustand zu verändern", () => {
    const before = new Set(["konto-a"])
    const opened = toggleExpandedAccount(before, "konto-b")
    const closed = toggleExpandedAccount(opened, "konto-a")
    expect([...before]).toEqual(["konto-a"])
    expect([...opened].sort()).toEqual(["konto-a", "konto-b"])
    expect([...closed]).toEqual(["konto-b"])
  })

  it("speichert deterministisch und ignoriert Schreibfehler", () => {
    const saved = store()
    saveExpandedAccounts(new Set(["konto-b", "konto-a"]), saved)
    expect(saved.value()).toBe('["konto-a","konto-b"]')
    expect(() => saveExpandedAccounts(new Set(["konto-a"]), { setItem: () => { throw new Error("voll") } })).not.toThrow()
  })
})
