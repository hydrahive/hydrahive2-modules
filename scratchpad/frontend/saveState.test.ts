import { describe, expect, it, vi } from "vitest"
import { beginSave, draftProblem, errorText, pendingChanges, persist, saveStateForError } from "./saveState"
import { de, type T } from "./texts.de"

const failure = (status: number, code?: string) => Object.assign(new Error(code ?? `HTTP ${status}`), { status, code })

describe("Speicherstatus der Idee", () => {
  it("wechselt beim Start zu speichert", () => {
    expect(beginSave()).toBe("saving")
  })

  it("wechselt nach erfolgreichem Speichern zu gespeichert", async () => {
    await expect(persist(vi.fn().mockResolvedValue({ id: "a" }))).resolves.toBe("saved")
  })

  it("wechselt bei einem Speicherfehler zu nicht gespeichert", async () => {
    await expect(persist(vi.fn().mockRejectedValue(new Error("offline")))).resolves.toBe("error")
    expect(saveStateForError(failure(500))).toBe("error")
    expect(saveStateForError(undefined)).toBe("error")
  })

  it("erkennt eine fehlende Kopfzeile", () => {
    expect(saveStateForError(failure(422, "title_required"))).toBe("title_required")
  })

  it("erkennt zu lange Texte, benannt und aus der Feldprüfung", () => {
    expect(saveStateForError(failure(422, "title_too_long"))).toBe("too_long")
    expect(saveStateForError(failure(422, "body_too_long"))).toBe("too_long")
    expect(saveStateForError(failure(422))).toBe("too_long")
  })

  it("erkennt eine inzwischen gelöschte Idee", () => {
    expect(saveStateForError(failure(404, "idea_not_found"))).toBe("gone")
  })

  it("ein unbekanntes Projekt ist ein gewöhnlicher Fehler, keine gelöschte Idee", () => {
    expect(saveStateForError(failure(404, "project_not_found"))).toBe("error")
  })
})

describe("draftProblem", () => {
  it("meldet eine leere Kopfzeile, bevor gespeichert wird", () => {
    expect(draftProblem("")).toBe("title_required")
    expect(draftProblem("   \n ")).toBe("title_required")
    expect(draftProblem("Admin-Seite")).toBeNull()
  })
})

describe("pendingChanges", () => {
  const stored = { title: "Admin-Seite", body: "alt" }

  it("sendet nur, was sich geändert hat", () => {
    expect(pendingChanges({ title: "Admin-Seite", body: "alt" }, stored)).toEqual({})
    expect(pendingChanges({ title: "Admin-Seite", body: "neu" }, stored)).toEqual({ body: "neu" })
    expect(pendingChanges({ title: "Neu", body: "neu" }, stored)).toEqual({ title: "Neu", body: "neu" })
  })

  it("schickt nie eine leere Kopfzeile, die Beschreibung aber trotzdem", () => {
    expect(pendingChanges({ title: "  ", body: "neu" }, stored)).toEqual({ body: "neu" })
    expect(pendingChanges({ title: "", body: "alt" }, stored)).toEqual({})
  })

  it("Leerraum am Rand der Kopfzeile ist keine Änderung", () => {
    expect(pendingChanges({ title: "  Admin-Seite ", body: "alt" }, stored)).toEqual({})
    expect(pendingChanges({ title: " Neu ", body: "alt" }, stored)).toEqual({ title: "Neu" })
  })

  it("eine geleerte Beschreibung wird gespeichert", () => {
    expect(pendingChanges({ title: "Admin-Seite", body: "" }, stored)).toEqual({ body: "" })
  })
})

describe("errorText", () => {
  const t: T = (key, vars) => de[key].replace(/\{\{(\w+)\}\}/g, (_m, name: string) => String(vars?.[name] ?? ""))

  it("übersetzt benannte Fehler", () => {
    expect(errorText(failure(404, "project_not_found"), t)).toBe(de.project_error)
    expect(errorText(failure(409, "ideas_full"), t)).toBe(de.full_error)
    expect(errorText(failure(404, "idea_not_found"), t)).toBe(de.gone)
    expect(errorText(failure(422, "title_too_long"), t)).toBe(de.too_long)
    expect(errorText(failure(409, "task_already_linked"), t)).toBe(de.task_linked_error)
    expect(errorText(failure(409, "tasks_not_installed"), t)).toBe(de.tasks_missing_error)
    expect(errorText(failure(409, "blueprint_not_installed"), t)).toBe(de.blueprint_missing_error)
    expect(errorText(failure(409, "boards_full"), t)).toBe(de.boards_full_error)
  })

  it("nennt sonst die Meldung des Servers", () => {
    expect(errorText(new Error("HTTP 500"), t)).toBe("Das hat nicht geklappt: HTTP 500")
    expect(errorText("kaputt", t)).toBe("Das hat nicht geklappt: kaputt")
  })
})
