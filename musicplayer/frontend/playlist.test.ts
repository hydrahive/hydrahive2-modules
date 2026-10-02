import { describe, expect, it } from "vitest"
import { afterEnded, currentOf, nextId, prevId } from "./playlist"

const t = (id: number) => ({ id })
const list = [t(1), t(2), t(3)]
const noShuffle = { shuffle: false, random: () => 0 }

describe("Playlist nach ID", () => {
  it("findet das laufende Lied über die ID, nicht über die Position", () => {
    expect(currentOf(list, 2)?.id).toBe(2)
    // Neues Lied kommt vorne dazu (Liste ist nach Datum absteigend): laufendes bleibt 2.
    expect(currentOf([t(9), ...list], 2)?.id).toBe(2)
  })

  it("liefert kein Lied, wenn das laufende gelöscht wurde oder nichts gewählt ist", () => {
    expect(currentOf([t(1), t(3)], 2)).toBeNull()
    expect(currentOf(list, null)).toBeNull()
  })

  it("weiter und zurück laufen ringsum", () => {
    expect(nextId(list, 1, noShuffle)).toBe(2)
    expect(nextId(list, 3, noShuffle)).toBe(1)
    expect(prevId(list, 1, noShuffle)).toBe(3)
    expect(prevId(list, 2, noShuffle)).toBe(1)
  })

  it("ein neues Lied vorne ändert nicht, was als nächstes kommt", () => {
    expect(nextId([t(9), ...list], 1, noShuffle)).toBe(2)
  })

  it("ohne Auswahl startet weiter beim ersten Lied, leere Liste liefert nichts", () => {
    expect(nextId(list, null, noShuffle)).toBe(1)
    expect(nextId([], 1, noShuffle)).toBeNull()
    expect(prevId([], 1, noShuffle)).toBeNull()
  })

  it("Shuffle wählt nie dasselbe Lied, wenn es mehr als eins gibt", () => {
    const rolls = [0.4, 0.4, 0.9] // erst zweimal Lied 2 (= aktuell), dann Lied 3
    const random = () => rolls.shift() ?? 0
    expect(nextId(list, 2, { shuffle: true, random })).toBe(3)
    expect(nextId([t(5)], 5, { shuffle: true, random: () => 0 })).toBe(5)
  })

  it("am Ende: Repeat eins wiederholt, Repeat aus stoppt nach dem letzten, sonst weiter", () => {
    expect(afterEnded(list, 2, "one", noShuffle)).toEqual({ kind: "repeat" })
    expect(afterEnded(list, 3, "off", noShuffle)).toEqual({ kind: "stop" })
    expect(afterEnded(list, 2, "off", noShuffle)).toEqual({ kind: "play", id: 3 })
    expect(afterEnded(list, 3, "all", noShuffle)).toEqual({ kind: "play", id: 1 })
  })

  it("am Ende eines gelöschten Lieds wird gestoppt", () => {
    expect(afterEnded([t(1), t(3)], 2, "all", noShuffle)).toEqual({ kind: "stop" })
  })
})
