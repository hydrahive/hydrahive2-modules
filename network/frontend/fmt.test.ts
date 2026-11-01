import { describe, expect, it } from "vitest"
import { bytes, countNodes, signalLevel, speed, uptime } from "./fmt"

const t = (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k)

describe("Anzeige-Helfer", () => {
  it("Datenmengen", () => {
    expect(bytes(null)).toBe("–")
    expect(bytes(999)).toBe("999 B")
    expect(bytes(1500)).toBe("1,5 KB")
    expect(bytes(1010)).toBe("1,0 KB")
    expect(bytes(65016436549)).toBe("65,0 GB")
    expect(bytes(150_000_000)).toBe("150 MB")
    expect(bytes(2e15)).toBe("2000 TB")
  })
  it("Laufzeit", () => {
    expect(uptime(null, t)).toBe("–")
    expect(uptime(603730, t)).toBe('dur.dh:{"d":6,"h":23}')
    expect(uptime(41055, t)).toBe('dur.hm:{"h":11,"m":24}')
    expect(uptime(120, t)).toBe('dur.m:{"m":2}')
  })
  it("Geschwindigkeit", () => {
    expect(speed(null)).toBe("–")
    expect(speed(0)).toBe("–")
    expect(speed(100)).toBe("100 Mbit/s")
    expect(speed(1000)).toBe("1 Gbit/s")
    expect(speed(2500)).toBe("2.5 Gbit/s")
  })
  it("Signal", () => {
    expect(signalLevel(null)).toBeNull()
    expect(signalLevel(-60)).toBe("good")
    expect(signalLevel(-61)).toBe("ok")
    expect(signalLevel(-70)).toBe("ok")
    expect(signalLevel(-80)).toBe("weak")
    expect(signalLevel(-81)).toBe("bad")
  })
  it("Knoten zählen", () => {
    expect(countNodes({ children: [{ children: [] }, { children: [{ children: [] }] }] })).toBe(4)
  })
})
