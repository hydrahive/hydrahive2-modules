import { describe, expect, it, vi } from "vitest"
import { AutoSaver, SAVE_DELAY_MS } from "./cutSave"
import type { Timeline } from "./timelineApi"

const tl = (revision: number, n = 0): Timeline => ({ revision, fps: 25, tracks: [{ id: "V1", kind: "video", clips: Array.from({ length: n }, (_, i) => ({
  id: `c${i}`, kind: "placeholder" as const, start: i, in: 0, out: 1, media_rel: "", scene_id: "", shot_id: "", label: "" })) }] })
const conflict = () => Object.assign(new Error("studio_timeline_conflict"), { code: "studio_timeline_conflict" })

describe("4b – automatisch speichern", () => {
  it("wartet auf Ruhe, speichert dann einmal mit der richtigen revision", async () => {
    vi.useFakeTimers()
    const save = vi.fn(async (t: Timeline) => ({ ...t, revision: t.revision + 1 }))
    const states: string[] = []
    const s = new AutoSaver(save, (st) => states.push(st))
    s.loaded(tl(4))
    s.change(tl(4, 1)); s.change(tl(4, 2))
    expect(states.at(-1)).toBe("dirty")
    await vi.advanceTimersByTimeAsync(SAVE_DELAY_MS - 50)
    expect(save).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(100)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save.mock.calls[0][0].revision).toBe(4)
    expect(save.mock.calls[0][0].tracks[0].clips).toHaveLength(2)                      // der letzte Stand
    expect(states.at(-1)).toBe("saved")
    s.change(tl(4, 3))                                                                   // nächste Änderung nimmt revision 5
    await vi.advanceTimersByTimeAsync(SAVE_DELAY_MS + 10)
    expect(save.mock.calls[1][0].revision).toBe(5)
    vi.useRealTimers()
  })

  it("Änderung während des Speicherns wird danach noch gespeichert", async () => {
    vi.useFakeTimers()
    let release: () => void = () => {}
    const save = vi.fn((t: Timeline) => new Promise<Timeline>((r) => { release = () => r({ ...t, revision: t.revision + 1 }) }))
    const s = new AutoSaver(save, () => {})
    s.loaded(tl(1))
    s.change(tl(1, 1))
    await vi.advanceTimersByTimeAsync(SAVE_DELAY_MS + 10)
    s.change(tl(1, 2))                                                                   // während der erste läuft
    release(); await vi.advanceTimersByTimeAsync(10)                                     // nur der erste ist fertig …
    expect(save).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(SAVE_DELAY_MS + 10)                                // … der zweite folgt nach der Ruhezeit
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1][0]).toMatchObject({ revision: 2 })
    release(); await vi.advanceTimersByTimeAsync(10)
    vi.useRealTimers()
  })

  it("sofort speichern (Reiter verlassen), Konflikt hält an und überschreibt nichts, Fehler meldet „Nicht gespeichert“", async () => {
    const states: string[] = []
    const save = vi.fn(async () => { throw conflict() })
    const s = new AutoSaver(save, (st) => states.push(st))
    s.loaded(tl(2))
    s.change(tl(2, 1))
    await s.flush()
    expect(save).toHaveBeenCalledTimes(1)
    expect(states.at(-1)).toBe("conflict")
    s.change(tl(2, 2))
    await s.flush()
    expect(save).toHaveBeenCalledTimes(1)                                                // nach Konflikt kein weiterer Versuch
    let down = true
    const flaky = vi.fn(async (t: Timeline) => { if (down) throw new Error("netz weg"); return { ...t, revision: t.revision + 1 } })
    const failing = new AutoSaver(flaky, (st) => states.push(st))
    failing.loaded(tl(0)); failing.change(tl(0, 1)); await failing.flush()
    expect(states.at(-1)).toBe("error")
    down = false
    failing.change(tl(0, 2)); await failing.flush()                                      // nächste Änderung versucht es wieder
    expect(flaky).toHaveBeenCalledTimes(2)
    expect(flaky.mock.calls[1][0]).toMatchObject({ revision: 0 })
    expect(flaky.mock.calls[1][0].tracks[0].clips).toHaveLength(2)
    expect(states.at(-1)).toBe("saved")
    const idle = vi.fn(async (t: Timeline) => t)
    const nothing = new AutoSaver(idle, () => {})
    nothing.loaded(tl(0)); await nothing.flush()
    expect(idle).not.toHaveBeenCalled()                                                  // nichts geändert → nichts gespeichert
  })
})
