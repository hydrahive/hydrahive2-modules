// C1 – Kapitel und Szenen/Abschnitte löschen (Spec loeschen-c1.md): Rückfrage, Server, neue Gliederung übernehmen.
// Gelöschtes landet im Papierkorb des Buchs. Ist die offene Szene weg, zeigt der Arbeitsplatz von selbst die erste.
import { useCallback, useState } from "react"
import { useTranslation } from "react-i18next"
import { storyApi, StoryApiError } from "./api"
import { isFiction } from "./bookFactory"
import type { Chapter, Scene } from "./model"
import { canDeleteChapter, sceneDeleteKind, trashApi } from "./trashApi"
import type { BookState } from "./useBook"

export function useDeleteNode(state: BookState) {
  const { t } = useTranslation("storyteller")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const { book } = state
  const unit = isFiction(book.kind) ? "scene" : "section"
  const chapters = book.parts.reduce((n, p) => n + p.chapters.length, 0)

  /** true = gelöscht. */
  const run = useCallback(async (call: () => Promise<Parameters<BookState["adoptStructure"]>[0]>): Promise<boolean> => {
    setBusy(true); setError("")
    try {
      await state.flush()   // ungespeicherte Änderungen zuerst, sonst gingen sie mit dem Löschen verloren
      state.adoptStructure(await call())   // Papierkorb lädt von selbst neu (Szenenzahl ändert sich)
      return true
    } catch (e) {
      setError(e instanceof StoryApiError ? t(`delete_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))
      return false
    } finally { setBusy(false) }
  }, [state, t])

  const deleteChapter = useCallback(async (c: Chapter): Promise<boolean> => {
    if (!canDeleteChapter(chapters)) return false
    if (!confirm(t(`delete_chapter_confirm_${unit}`, { title: c.title, count: c.scenes.length }))) return false
    return run(() => trashApi.deleteChapter(state.projectId, book.id, c.id))
  }, [book.id, chapters, run, state.projectId, t, unit])

  const deleteScene = useCallback(async (s: Scene, c: Chapter): Promise<boolean> => {
    const kind = sceneDeleteKind(chapters, c.scenes.length)
    if (kind === "blocked") return false
    const ask = kind === "chapter" ? t(`delete_scene_with_chapter_${unit}`, { title: s.title, chapter: c.title })
      : t(`delete_scene_confirm_${unit}`, { title: s.title })
    if (!confirm(ask)) return false
    return run(() => storyApi.deleteScene(state.projectId, book.id, s.id))
  }, [book.id, chapters, run, state.projectId, t, unit])

  return { busy, error, unit, deleteChapter, deleteScene,
    chapterBlocked: !canDeleteChapter(chapters),
    sceneBlocked: (c: Chapter) => sceneDeleteKind(chapters, c.scenes.length) === "blocked" }
}
