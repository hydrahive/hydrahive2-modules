import { describe, expect, it, vi } from "vitest"
import { beginSave, persistUserText, saveStateForError } from "./saveState"

describe("Scratchpad-Speicherstatus", () => {
  it("wechselt beim Start zu speichert", () => {
    expect(beginSave()).toBe("saving")
  })

  it("wechselt nach erfolgreichem Speichern zu gespeichert", async () => {
    await expect(persistUserText(vi.fn().mockResolvedValue(undefined), "Notiz")).resolves.toBe("saved")
  })

  it("wechselt bei einem Speicherfehler zu nicht gespeichert", async () => {
    await expect(persistUserText(vi.fn().mockRejectedValue(new Error("offline")), "Notiz")).resolves.toBe("error")
  })

  it("erkennt die Backend-Antwort scratchpad_too_large als zu groß", async () => {
    const error = Object.assign(new Error("scratchpad_too_large"), { status: 400 })
    await expect(persistUserText(vi.fn().mockRejectedValue(error), "Notiz")).resolves.toBe("too_large")
  })

  it("erkennt die Zeichenlimit-Validierung ebenfalls als zu groß", () => {
    expect(saveStateForError({ status: 422 })).toBe("too_large")
  })
})
