import { useState } from "react"
import { useTranslation } from "react-i18next"
import { draftApi, type Draft, type DraftBook, type IdeaLength } from "./draftApi"
import { toggleId } from "./draftLogic"
import { errorText } from "./planLogic"
import type { PlanState } from "./usePlan"

type Step =
  | { kind: "idea" }
  | { kind: "book"; books: DraftBook[] | null }
  | { kind: "preview"; draft: Draft; truncated: number; fromBook: boolean }
  | null

/** Drehbuch-Entwurf (B2): Idee oder Buch → Vorschau → Übernehmen. Erst „Übernehmen“ speichert etwas. */
export function useDraft(p: PlanState, projectId: string, onDecompose: () => void) {
  const { t } = useTranslation("studio")
  const [step, setStep] = useState<Step>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [idea, setIdea] = useState("")
  const [length, setLength] = useState<IdeaLength>("60")
  const [style, setStyle] = useState("")
  const [bookId, setBookId] = useState("")
  const [chapters, setChapters] = useState<string[]>([])
  const [decompose, setDecompose] = useState(false)

  const pickBook = (books: DraftBook[], id: string) => {
    setBookId(id)
    setChapters(books.find((b) => b.id === id)?.chapters.map((c) => c.id) ?? [])     // Standard: alle Kapitel
  }

  const ask = async <T,>(fn: () => Promise<T>, then: (r: T) => void) => {
    setBusy(true); setError(null)
    try { then(await fn()) } catch (e) { setError(errorText(t, e)) } finally { setBusy(false) }
  }

  const close = () => { if (!busy) { setStep(null); setError(null) } }
  return {
    step, busy: busy || p.busy, error, idea, length, style, bookId, chapters, decompose,
    setIdea, setLength, setStyle, setDecompose, close,
    toggleChapter: (id: string) => setChapters((c) => toggleId(c, id)),
    selectBook: (id: string) => { if (step?.kind === "book" && step.books) pickBook(step.books, id) },
    openIdea: () => { setError(null); setStep({ kind: "idea" }) },
    openBook: () => {
      setError(null); setStep({ kind: "book", books: null })
      void ask(() => draftApi.books(projectId), (r) => { setStep({ kind: "book", books: r.books }); if (r.books[0]) pickBook(r.books, r.books[0].id) })
    },
    runIdea: () => void ask(() => draftApi.idea(projectId, idea, length, style),
      (r) => setStep({ kind: "preview", draft: r.draft, truncated: 0, fromBook: false })),
    runBook: () => void ask(() => draftApi.book(projectId, bookId, chapters), (r) => {
      setDecompose(false)
      setStep({ kind: "preview", draft: r.draft, truncated: r.truncated, fromBook: true })
    }),
    apply: () => {
      if (step?.kind !== "preview") return
      const { draft, fromBook } = step
      const then = fromBook && decompose
      void p.act(() => draftApi.apply(projectId, draft), () => t("notice_draft_applied"), () => {
        setStep(null); setIdea(""); setStyle("")
        if (then) onDecompose()                       // Sammelauftrag-Dialog mit Anzahl und Modell, startet erst dort
      }, (e) => { setError(errorText(t, e)); return true })
    },
  }
}

export type DraftState = ReturnType<typeof useDraft>
