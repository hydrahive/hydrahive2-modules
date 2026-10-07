// Ghostwriter G4b – Infos-Vorschläge ohne React.
import { describe, expect, it } from "vitest"
import { chosenFields, infoMarks, infoRows, type InfoProposal } from "./infoProposal"

const p = (fields: InfoProposal["fields"]): InfoProposal =>
  ({ scene_id: "s", fields, base_version: 3, source: "agent", session_id: "x", note: "", at: "" })
const scene = { title: "Alt", summary: "Alte Zusammenfassung.", pov: "" }

describe("infoProposal", () => {
  it("Markierungen je Szene, leer bei älterem Server", () => {
    expect(infoMarks([p({ title: "N" })])).toEqual({ s: p({ title: "N" }) })
    expect(infoMarks(undefined)).toEqual({})
  })
  it("Zeilen nur für vorgeschlagene Felder, feste Reihenfolge, erkennt inzwischen gleiche Werte", () => {
    expect(infoRows(p({ pov: "Mia", title: "Alt " }), scene)).toEqual([
      { field: "title", old: "Alt", proposed: "Alt ", same: true },
      { field: "pov", old: "", proposed: "Mia", same: false },
    ])
  })
  it("Auswahl: Standard alle unterschiedlichen, abgewählte und gleiche fallen weg", () => {
    const rows = infoRows(p({ title: "Neu", summary: "Neu.", pov: "" }), scene)
    expect(chosenFields(rows, {})).toEqual(["title", "summary"])            // pov "" == "" → gleich
    expect(chosenFields(rows, { title: false })).toEqual(["summary"])
    expect(chosenFields(rows, { title: false, summary: false })).toEqual([])
  })
})
