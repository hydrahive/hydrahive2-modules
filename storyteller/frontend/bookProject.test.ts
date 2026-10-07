// T1c: „Neues Buch“ – Ort wählen (eigenes Projekt mit Team / aktuelles Projekt) und danach dorthin wechseln.
import { describe, expect, it } from "vitest"
import { StoryApiError } from "./api"
import { afterCreate, defaultPlace, errorText, isBookProject, placesFor } from "./bookProject"

describe("bookProject", () => {
  it("bietet „eigenes Projekt“ nur mit Recht an und wählt es dann vor", () => {
    expect(placesFor(true)).toEqual(["own", "current"])
    expect(defaultPlace(true)).toBe("own")
    expect(placesFor(false)).toEqual(["current"])
    expect(defaultPlace(false)).toBe("current")
  })
  it("ohne aktuelles Projekt (Nutzer in keinem Projekt) bleibt nur das eigene – oder nichts", () => {
    expect(placesFor(true, false)).toEqual(["own"])
    expect(defaultPlace(true, false)).toBe("own")
    expect(placesFor(false, false)).toEqual([])
  })
  it("nach dem Anlegen: in das neue Projekt wechseln und das Buch öffnen", () => {
    expect(afterCreate({ project_id: "p-neu", book: { id: "b1" } })).toEqual({ projectId: "p-neu", bookId: "b1" })
  })
  it("Fehlertexte: bekannter Code → Text, sonst Meldung", () => {
    const t = (k: string, o?: { defaultValue?: string }) => (k === "err_no_model" ? "Kein Modell" : (o?.defaultValue ?? k))
    expect(errorText(t, new StoryApiError(409, "no_model"))).toBe("Kein Modell")
    expect(errorText(t, new StoryApiError(500, "boom", undefined, "Serverfehler"))).toBe("Serverfehler")
    expect(errorText(t, new Error("x"))).toBe("x")
    expect(errorText(t, "y")).toBe("y")
  })
  it("erkennt Buch-Projekte am Kennzeichen", () => {
    expect(isBookProject({ metadata: { storyteller: { book_id: "b1", team_version: 1 } } })).toBe(true)
    expect(isBookProject({ metadata: {} })).toBe(false)
    expect(isBookProject({})).toBe(false)
    expect(isBookProject({ metadata: { storyteller: "x" } })).toBe(false)
  })
})
