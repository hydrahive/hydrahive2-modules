// Ghostwriter G3 – Interview bearbeiten ohne React (interviewModel.test.ts). Alles gibt neue Listen zurück.
import { newId } from "./model"

export const MAX_QUESTIONS = 20
export interface Question { id: string; question: string; answer: string }
export interface Interview { chapter_id: string; version: number; questions: Question[]; updated_at: string }

/** Vorgeschlagene Fragen hinten anhängen; leere und schon vorhandene (gleicher Text) fallen weg. */
export function addQuestions(list: Question[], texts: string[]): Question[] {
  const seen = new Set(list.map((x) => x.question.trim().toLowerCase()))
  const out = [...list]
  for (const t of texts) {
    const text = t.trim()
    if (!text || seen.has(text.toLowerCase()) || out.length >= MAX_QUESTIONS) continue
    seen.add(text.toLowerCase())
    out.push({ id: newId(), question: text, answer: "" })
  }
  return out
}

export const editAnswer = (list: Question[], id: string, answer: string): Question[] =>
  list.map((x) => (x.id === id ? { ...x, answer } : x))

export const editQuestion = (list: Question[], id: string, question: string): Question[] =>
  list.map((x) => (x.id === id ? { ...x, question } : x))

export const removeQuestion = (list: Question[], id: string): Question[] => list.filter((x) => x.id !== id)

/** Diktierten Text an die Antwort anhängen (mit Leerzeichen), nie ersetzen. */
export function appendDictation(list: Question[], id: string, spoken: string): Question[] {
  const add = spoken.trim()
  if (!add) return list
  return list.map((x) => (x.id === id ? { ...x, answer: x.answer.trim() ? `${x.answer.trimEnd()} ${add}` : add } : x))
}

export const answeredCount = (list: Question[]): number => list.filter((x) => x.answer.trim()).length
