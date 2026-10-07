// Interview (Ghostwriter G3) bearbeiten ohne React: Fragen hinzufügen/ändern/löschen, Diktat anhängen, zählen.
import { describe, expect, it } from "vitest"
import { addQuestions, answeredCount, appendDictation, editAnswer, editQuestion, MAX_QUESTIONS, removeQuestion,
  type Question } from "./interviewModel"

const q = (id: string, question = "Frage?", answer = ""): Question => ({ id, question, answer })

describe("interviewModel", () => {
  it("neue Fragen bekommen eigene IDs (32 hex) und hängen hinten an; doppelte Texte werden ausgelassen", () => {
    const out = addQuestions([q("a".repeat(32), "Wie kamst du an?")], ["Wer half dir?", "Wie kamst du an?", "  "])
    expect(out.map((x) => x.question)).toEqual(["Wie kamst du an?", "Wer half dir?"])
    expect(out[1].id).toMatch(/^[a-f0-9]{32}$/)
    expect(out[1].answer).toBe("")
  })
  it("nie mehr als MAX_QUESTIONS", () => {
    const many = Array.from({ length: 30 }, (_, i) => `Frage ${i}?`)
    expect(addQuestions([], many)).toHaveLength(MAX_QUESTIONS)
  })
  it("ändern und löschen sind unveränderlich", () => {
    const a = [q("1".repeat(32)), q("2".repeat(32))]
    const b = editAnswer(a, "2".repeat(32), "Antwort")
    expect(b[1].answer).toBe("Antwort")
    expect(a[1].answer).toBe("")
    expect(editQuestion(b, "1".repeat(32), "Neu?")[0].question).toBe("Neu?")
    expect(removeQuestion(b, "1".repeat(32)).map((x) => x.id)).toEqual(["2".repeat(32)])
  })
  it("Diktat wird mit Leerzeichen angehängt, nicht ersetzt", () => {
    const a = [q("1".repeat(32), "F?", "Ich kam 1987.")]
    expect(appendDictation(a, "1".repeat(32), "Mit dem Zug.")[0].answer).toBe("Ich kam 1987. Mit dem Zug.")
    expect(appendDictation([q("1".repeat(32))], "1".repeat(32), " Hallo ")[0].answer).toBe("Hallo")
    expect(appendDictation(a, "1".repeat(32), "   ")[0].answer).toBe("Ich kam 1987.")
  })
  it("zählt beantwortete Fragen (Leerraum zählt nicht)", () => {
    expect(answeredCount([q("1".repeat(32), "F", "ja"), q("2".repeat(32), "F", "  "), q("3".repeat(32))])).toBe(1)
  })
})
