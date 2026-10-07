// Interview speichern mit Version (Ghostwriter G3) – ohne React (interviewSync.ts).
// Gleiche Regel wie BookSync: veraltete Version → Konflikt, eigene Fassung bleibt, nichts geht still verloren.
import { describe, expect, it, vi } from "vitest"
import { StoryApiError } from "./api"
import type { Interview, Question } from "./interviewModel"
import { InterviewSync } from "./interviewSync"

const q = (answer: string): Question[] => [{ id: "a".repeat(32), question: "F?", answer }]

function server(start = 0) {
  const db = { version: start, questions: [] as Question[] }
  const save = vi.fn(async (base: number, questions: Question[]): Promise<Interview> => {
    if (base !== db.version) {
      throw new StoryApiError(409, "version_conflict", { chapter_id: "c", version: db.version, questions: db.questions, updated_at: "" })
    }
    db.version += 1
    db.questions = questions
    return { chapter_id: "c", version: db.version, questions, updated_at: "" }
  })
  return { db, save }
}

describe("InterviewSync", () => {
  it("speichert die neueste Fassung mit der aktuellen Version", async () => {
    const s = server()
    const sync = new InterviewSync(0, s.save)
    sync.change(q("eins"))
    sync.change(q("zwei"))
    await sync.flush()
    expect(s.save).toHaveBeenCalledTimes(1)
    expect(s.db).toMatchObject({ version: 1, questions: q("zwei") })
    sync.change(q("drei"))
    await sync.flush()
    expect(s.db.version).toBe(2)
  })
  it("nichts geändert → nichts gesendet", async () => {
    const s = server()
    const sync = new InterviewSync(0, s.save)
    await sync.flush()
    expect(s.save).not.toHaveBeenCalled()
  })
  it("Konflikt: eigene Fassung bleibt; „behalten“ speichert sie auf der fremden Version", async () => {
    const s = server(3)
    s.db.questions = q("fremd")
    const sync = new InterviewSync(2, s.save)
    sync.change(q("meins"))
    await sync.flush()
    expect(sync.state).toBe("conflict")
    expect(sync.conflict?.questions).toEqual(q("fremd"))
    expect(sync.questions).toEqual(q("meins"))
    await sync.resolve("keep")
    expect(s.db).toMatchObject({ version: 4, questions: q("meins") })
    expect(sync.state).toBe("saved")
  })
  it("Konflikt: „neu laden“ übernimmt den Server-Stand und sendet nichts", async () => {
    const s = server(3)
    s.db.questions = q("fremd")
    const sync = new InterviewSync(2, s.save)
    sync.change(q("meins"))
    await sync.flush()
    s.save.mockClear()
    await sync.resolve("reload")
    expect(sync.questions).toEqual(q("fremd"))
    await sync.flush()                              // die verworfene eigene Fassung darf nicht nachträglich gehen
    expect(s.save).not.toHaveBeenCalled()
    expect(s.db.questions).toEqual(q("fremd"))
    sync.change(q("weiter"))
    await sync.flush()
    expect(s.db).toMatchObject({ version: 4, questions: q("weiter") })
  })
  it("während Konflikt wird nicht automatisch gespeichert", async () => {
    const s = server(1)
    const sync = new InterviewSync(0, s.save)
    sync.change(q("a"))
    await sync.flush()
    sync.change(q("b"))
    await sync.flush()
    expect(s.save).toHaveBeenCalledTimes(1)
    expect(sync.questions).toEqual(q("b"))
  })
  it("Netzfehler: Zustand failed, Änderung bleibt für „nochmal“", async () => {
    const save = vi.fn().mockRejectedValueOnce(new StoryApiError(0, "network")).mockResolvedValue({ chapter_id: "c", version: 1, questions: q("x"), updated_at: "" })
    const sync = new InterviewSync(0, save)
    sync.change(q("x"))
    await sync.flush()
    expect(sync.state).toBe("failed")
    await sync.flush()
    expect(sync.state).toBe("saved")
    expect(save).toHaveBeenCalledTimes(2)
  })
})
