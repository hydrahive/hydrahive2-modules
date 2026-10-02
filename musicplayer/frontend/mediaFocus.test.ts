import { describe, expect, it } from "vitest"
import { forget, onVideoStart, shouldResume, type ResumeState } from "./mediaFocus"

const idle: ResumeState = { resume: false }
const moment = { videoPaused: true, pointerDown: false }

describe("Musik nach dem Video fortsetzen", () => {
  it("merkt sich nur, wenn die Musik beim Video-Start lief", () => {
    expect(onVideoStart(idle, true)).toEqual({ resume: true })
    expect(onVideoStart(idle, false)).toEqual({ resume: false })
  })

  it("bleibt gemerkt, wenn ein zweites Video startet (Musik ist da schon aus)", () => {
    const afterFirst = onVideoStart(idle, true)
    expect(onVideoStart(afterFirst, false)).toEqual({ resume: true })
  })

  it("setzt fort, wenn das Video steht und nichts gedrückt ist", () => {
    expect(shouldResume({ resume: true }, moment)).toBe(true)
  })

  it("setzt nicht fort, wenn die Musik vorher nicht lief", () => {
    expect(shouldResume(idle, moment)).toBe(false)
  })

  it("setzt nicht fort, wenn das Video inzwischen wieder läuft (Spulen, nächstes Video)", () => {
    expect(shouldResume({ resume: true }, { ...moment, videoPaused: false })).toBe(false)
  })

  it("setzt nicht fort, solange Maus oder Finger auf dem Video sind (Zeitleiste ziehen)", () => {
    expect(shouldResume({ resume: true }, { ...moment, pointerDown: true })).toBe(false)
  })

  it("vergisst alles, wenn der Nutzer die Musik selbst bedient", () => {
    expect(forget()).toEqual({ resume: false })
    expect(shouldResume(forget(), moment)).toBe(false)
  })
})
