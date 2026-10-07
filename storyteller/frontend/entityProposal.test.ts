// Ghostwriter G4c – Steckbrief-Vorschläge ohne React.
import { describe, expect, it } from "vitest"
import { changeFor, entityRows, newProposals, proposalIdOf, proposalKey, type EntityProposal } from "./entityProposal"
import type { Entity } from "./model"

const prop = (over: Partial<EntityProposal>): EntityProposal => ({
  id: "p1", entity_id: "", kind: "character", changes: {}, base_structure_version: 2, source: "agent", session_id: "s",
  note: "", at: "", ...over,
})
const mia: Entity = { id: "m", kind: "character", name: "Mia", aliases: ["Mi"], description: "Zwölf.", fields: [{ key: "Augen", value: "grün" }] }

describe("entityProposal", () => {
  it("Kennung für neue Vorschläge hin und zurück", () => {
    expect(proposalKey(prop({ id: "abc" }))).toBe("proposal:abc")
    expect(proposalIdOf("proposal:abc")).toBe("abc")
    expect(proposalIdOf("m")).toBeNull()
    expect(proposalIdOf(null)).toBeNull()
  })
  it("neue nach Art, Änderung je Steckbrief", () => {
    const list = [prop({ id: "a", kind: "place" }), prop({ id: "b" }), prop({ id: "c", entity_id: "m" })]
    expect(newProposals(list, "place").map((p) => p.id)).toEqual(["a"])
    expect(newProposals(list, "character").map((p) => p.id)).toEqual(["b"])
    expect(changeFor(list, "m")?.id).toBe("c")
    expect(changeFor(list, "x")).toBeUndefined()
  })
  it("Vergleich: nur vorgeschlagene Felder, Listen lesbar, neu = alt leer", () => {
    const change = prop({ entity_id: "m", changes: { aliases: ["Mi", "Mimi"], fields: [{ key: "Augen", value: "grün" }, { key: "Haare", value: "rot" }] } })
    expect(entityRows(change, mia)).toEqual([
      { key: "aliases", old: "Mi", proposed: "Mi, Mimi" },
      { key: "fields", old: "Augen: grün", proposed: "Augen: grün\nHaare: rot" },
    ])
    expect(entityRows(prop({ changes: { name: "Hinnerk", description: "Wärter." } }))).toEqual([
      { key: "name", old: "", proposed: "Hinnerk" },
      { key: "description", old: "", proposed: "Wärter." },
    ])
  })
})
