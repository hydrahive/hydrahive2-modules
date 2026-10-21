import { describe, expect, it } from "vitest"
import { caseFormErrors, deadlineLight, daysUntil, modelState, nextOpenDeadline, partyRoleLabel } from "./caseFormat"

const today = new Date("2026-10-20T10:00:00")

describe("daysUntil", () => {
  it("zählt Kalendertage ab heute (lokal, ohne Uhrzeit)", () => {
    expect(daysUntil("2026-10-20", today)).toBe(0)
    expect(daysUntil("2026-10-21", today)).toBe(1)
    expect(daysUntil("2026-10-19", today)).toBe(-1)
    expect(daysUntil("2026-11-02", today)).toBe(13)
  })
})

describe("deadlineLight", () => {
  it("rot: überschritten oder ≤ 3 Tage, gelb: ≤ 14 Tage, grün: später, grau: erledigt/keine", () => {
    expect(deadlineLight({ due_date: "2026-10-19", status: "open" }, today)).toBe("red")
    expect(deadlineLight({ due_date: "2026-10-23", status: "open" }, today)).toBe("red")
    expect(deadlineLight({ due_date: "2026-10-24", status: "open" }, today)).toBe("yellow")
    expect(deadlineLight({ due_date: "2026-11-03", status: "open" }, today)).toBe("yellow")
    expect(deadlineLight({ due_date: "2026-11-04", status: "open" }, today)).toBe("green")
    expect(deadlineLight({ due_date: "2026-10-19", status: "done" }, today)).toBe("none")
    expect(deadlineLight(null, today)).toBe("none")
  })
})

describe("nextOpenDeadline", () => {
  it("nimmt die früheste offene Frist", () => {
    const list = [
      { due_date: "2026-11-10", status: "open", label: "B" },
      { due_date: "2026-10-30", status: "done", label: "A" },
      { due_date: "2026-11-02", status: "open", label: "C" },
    ]
    expect(nextOpenDeadline(list)?.label).toBe("C")
    expect(nextOpenDeadline([])).toBeNull()
  })
})

describe("caseFormErrors", () => {
  it("verlangt Titel und Bundesland, prüft Längen", () => {
    expect(caseFormErrors({ title: "", state: "" })).toEqual({ title: "Bitte einen kurzen Titel angeben.", state: "Bitte das Bundesland wählen (für Feiertage bei Fristen)." })
    expect(caseFormErrors({ title: "Miete", state: "NW" })).toEqual({})
    expect(caseFormErrors({ title: "x".repeat(201), state: "NW" }).title).toMatch(/200/)
    expect(caseFormErrors({ title: "  ", state: "NW" }).title).toBeTruthy()
  })
})

describe("partyRoleLabel", () => {
  it("übersetzt Rollen, unbekannt bleibt", () => {
    expect(partyRoleLabel("opponent")).toBe("Gegenseite")
    expect(partyRoleLabel("lawyer")).toBe("Anwalt/Anwältin")
    expect(partyRoleLabel("xyz")).toBe("xyz")
  })
})

describe("modelState", () => {
  const list = ["openai-codex/gpt-5.6-luna", "claude-sonnet-4-6"]
  it("Standard aus der Liste → vorausgewählt, keine Wahl nötig", () => {
    expect(modelState({ standard: "openai-codex/gpt-5.6-luna", selected: "openai-codex/gpt-5.6-luna", ids: list }, ""))
      .toEqual({ effective: "openai-codex/gpt-5.6-luna", mustChoose: false, warning: null })
  })
  it("Standard fehlt im Katalog → muss wählen, Hinweis nennt das Modell (Fund hydratest 20.10.)", () => {
    const s = modelState({ standard: "claude-sonnet-4-6", selected: "", ids: ["openai-codex/gpt-5.6-luna"] }, "")
    expect(s.mustChoose).toBe(true)
    expect(s.effective).toBe("")
    expect(s.warning).toMatch(/claude-sonnet-4-6/)
  })
  it("kein Standard eingestellt → muss wählen", () => {
    expect(modelState({ standard: "", selected: "", ids: list }, "").mustChoose).toBe(true)
  })
  it("eigene Wahl gewinnt und hebt die Pflicht auf", () => {
    expect(modelState({ standard: "claude-sonnet-4-6", selected: "", ids: list }, "openai-codex/gpt-5.6-luna"))
      .toEqual({ effective: "openai-codex/gpt-5.6-luna", mustChoose: false, warning: null })
  })
  it("Katalog nicht geladen → nicht blockieren (Server entscheidet)", () => {
    expect(modelState(null, "")).toEqual({ effective: "", mustChoose: false, warning: null })
  })
})

describe("caseFormErrors mit Modell", () => {
  it("meldet fehlendes Modell nur, wenn gewählt werden muss", () => {
    expect(caseFormErrors({ title: "Miete", state: "NW" }, { mustChoose: true }).model).toBeTruthy()
    expect(caseFormErrors({ title: "Miete", state: "NW" }, { mustChoose: false })).toEqual({})
  })
})
