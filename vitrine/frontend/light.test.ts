import { describe, expect, it } from "vitest"
import { DEFAULT_LIGHT, lightColor, lightErrors, normalizeLight, toPicker } from "./light"

describe("Licht-Einstellung (S8) – wie der Server", () => {
  it("Vorgaben sind gültig, Helligkeit 80", () => {
    expect(lightErrors(DEFAULT_LIGHT)).toEqual([])
    expect(DEFAULT_LIGHT.brightness).toBe(80)
  })

  it("Farben vereinheitlichen und prüfen", () => {
    expect(lightColor("#ff8800")).toBe("FF8800")
    expect(lightColor("FFF")).toBeNull()
    expect(lightColor("rot")).toBeNull()
    expect(toPicker("FF8800")).toBe("#ff8800")
  })

  it("lehnt falsche Werte ab", () => {
    expect(lightErrors({ ...DEFAULT_LIGHT, brightness: 101 })).toContain("brightness")
    expect(lightErrors({ ...DEFAULT_LIGHT, brightness: 2.5 })).toContain("brightness")
    expect(lightErrors({ ...DEFAULT_LIGHT, error_blink_seconds: 601 })).toContain("error_blink_seconds")
    const bad = normalizeLight({ states: { ...DEFAULT_LIGHT.states, working: { ...DEFAULT_LIGHT.states.working, effect: "wave" as never } } })
    expect(lightErrors(bad)).toContain("states.working")
    const done = normalizeLight({ states: { ...DEFAULT_LIGHT.states, done: { ...DEFAULT_LIGHT.states.done, seconds: 61 } } })
    expect(lightErrors(done)).toContain("states.done")
    const col = normalizeLight({ seasons: { ...DEFAULT_LIGHT.seasons, winter: { effect: "static", color: "#c8e0ff" } } })
    expect(lightErrors(col)).toContain("seasons.winter")
  })

  it("eigene Helligkeit je Zustand: leer oder 0–100", () => {
    const s = (b: number | null) => normalizeLight({ states: { ...DEFAULT_LIGHT.states, error: { ...DEFAULT_LIGHT.states.error, brightness: b } } })
    expect(lightErrors(s(null))).toEqual([])
    expect(lightErrors(s(40))).toEqual([])
    expect(lightErrors(s(140))).toContain("states.error")
  })

  it("alte Einstellung ohne Licht bekommt Vorgaben", () => {
    expect(normalizeLight(undefined)).toEqual(DEFAULT_LIGHT)
    expect(normalizeLight({ brightness: 40 }).states.error.color).toBe("FF0000")
  })
})
