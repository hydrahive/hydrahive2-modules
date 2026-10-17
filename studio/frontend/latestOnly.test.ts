import { describe, expect, it } from "vitest"
import { latestOnly } from "./latestOnly"

const later = <T,>(v: T, ms: number) => new Promise<T>((r) => setTimeout(() => r(v), ms))

describe("Projektwechsel – späte Antworten des alten Projekts werden verworfen", () => {
  it("nur die Antwort des zuletzt gewählten Projekts kommt an", async () => {
    const got: string[] = []
    const guard = latestOnly()
    const a = guard.run("alt", () => later("Daten alt", 30)).then((v) => { if (v.current) got.push(v.value) })
    const b = guard.run("neu", () => later("Daten neu", 5)).then((v) => { if (v.current) got.push(v.value) })
    await Promise.all([a, b])
    expect(got).toEqual(["Daten neu"])
  })

  it("dasselbe Projekt zweimal: die neuere Anfrage gewinnt, auch wenn die ältere später fertig wird", async () => {
    const got: string[] = []
    const guard = latestOnly()
    const a = guard.run("p", () => later("erste", 30)).then((v) => { if (v.current) got.push(v.value) })
    const b = guard.run("p", () => later("zweite", 5)).then((v) => { if (v.current) got.push(v.value) })
    await Promise.all([a, b])
    expect(got).toEqual(["zweite"])
  })

  it("Fehler kommen nur an, wenn die Anfrage noch aktuell ist", async () => {
    const guard = latestOnly()
    const old = guard.run("alt", () => later(null, 20).then(() => { throw new Error("kaputt") }))
    guard.run("neu", () => Promise.resolve("ok"))
    await expect(old).resolves.toEqual({ current: false, value: undefined })
    await expect(guard.run("neu", () => Promise.reject(new Error("weg")))).rejects.toThrow("weg")
  })
})
