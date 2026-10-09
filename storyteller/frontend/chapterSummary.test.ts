import { describe, expect, it } from "vitest"
import { isDirty } from "./chapterSummary"

describe("Kapitel-Zusammenfassung (A5c)", () => {
  it("geändert nur, wenn sich der Inhalt ändert – Leerraum am Rand zählt nicht", () => {
    expect(isDirty("Kurz.", "Kurz.")).toBe(false)
    expect(isDirty("  Kurz.\n", "Kurz.")).toBe(false)
    expect(isDirty("Kurz!", "Kurz.")).toBe(true)
    expect(isDirty("", "Kurz.")).toBe(true)
  })
})
