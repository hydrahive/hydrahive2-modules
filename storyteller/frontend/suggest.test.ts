import { describe, expect, it } from "vitest"
import { occurrenceBefore, wordDiff } from "./suggest"

const join = (parts: { kind: string; text: string }[], keep: string[]) =>
  parts.filter((p) => keep.includes(p.kind)).map((p) => p.text).join("")

describe("wordDiff", () => {
  it("setzt alt (same+del) und neu (same+add) wieder exakt zusammen", () => {
    const a = "Es regnete, als Charlie den Schlüssel drehte."
    const b = "Es goss in Strömen, als Charlie langsam den Schlüssel drehte."
    const d = wordDiff(a, b)
    expect(join(d, ["same", "del"])).toBe(a)
    expect(join(d, ["same", "add"])).toBe(b)
    expect(d.some((p) => p.kind === "del" && p.text.includes("regnete,"))).toBe(true)
    expect(d.some((p) => p.kind === "add" && p.text.includes("langsam"))).toBe(true)
  })
  it("gleiche Texte: nur „same“; leere Seiten funktionieren", () => {
    expect(wordDiff("a b", "a b")).toEqual([{ kind: "same", text: "a b" }])
    expect(wordDiff("", "neu")).toEqual([{ kind: "add", text: "neu" }])
    expect(wordDiff("alt", "")).toEqual([{ kind: "del", text: "alt" }])
  })
  it("sehr lange Texte fallen auf „alles alt / alles neu“ zurück statt zu hängen", () => {
    const a = Array.from({ length: 600 }, (_, i) => `w${i}`).join(" ")
    const b = Array.from({ length: 600 }, (_, i) => `v${i}`).join(" ")
    expect(wordDiff(a, b)).toEqual([{ kind: "del", text: a }, { kind: "add", text: b }])
  })
})

describe("occurrenceBefore (A5: richtige Stelle beim Umschreiben)", () => {
  it("zählt, wie oft die Markierung VOR der markierten Stelle schon vorkommt", () => {
    const text = "A. Es regnete. B. Es regnete. C."
    expect(occurrenceBefore(text.slice(0, 3), "Es regnete.")).toBe(0)
    expect(occurrenceBefore(text.slice(0, 18), "Es regnete.")).toBe(1)
  })
  it("überlappende Vorkommen zählen einzeln (gleich wie der Server mit find(at + 1))", () => {
    expect(occurrenceBefore("XX", "X")).toBe(2)
    expect(occurrenceBefore("XXX", "XX")).toBe(2)
  })
  it("leere Markierung oder nichts davor → 0", () => {
    expect(occurrenceBefore("abc", "")).toBe(0)
    expect(occurrenceBefore("", "x")).toBe(0)
  })
})
