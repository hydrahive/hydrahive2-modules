// Ghostwriter G4 – Modus „Im Chat“: Projekt-Agent + fehlende Werkzeuge laden, Chat-Sitzung anlegen und im neuen
// Tab öffnen, solange der Modus offen ist alle 10 s nach neuen Vorschlägen des Agenten fragen (Spec §11.3).
import { useCallback, useEffect, useState } from "react"
import { StoryApiError } from "./api"
import { chatApi, type ChatInfo, type ChatStart } from "./chatApi"
import type { BookState } from "./useBook"
import { useProposalPoll } from "./useProposalPoll"

export { POLL_MS } from "./useProposalPoll"

export function useChatMode(state: BookState, sceneId: string) {
  const { projectId, book } = state
  const [info, setInfo] = useState<ChatInfo | null>(null)
  const [started, setStarted] = useState<ChatStart | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<StoryApiError | null>(null)

  const loadInfo = useCallback(async () => {
    try { setInfo(await chatApi.info(projectId, book.id)); setError(null) } catch (e) { setError(e as StoryApiError) }
  }, [projectId, book.id])

  const poll = useProposalPoll(state, true)

  useEffect(() => {
    let alive = true
    chatApi.info(projectId, book.id)
      .then((x) => { if (alive) { setInfo(x); setError(null) } })
      .catch((e: unknown) => { if (alive) setError(e as StoryApiError) })
    return () => { alive = false }
  }, [projectId, book.id])

  /** G4e: im Chat-Fenster des Storytellers öffnen (dieselbe Sitzung je Buch, Verlauf bleibt). */
  const openHere = useCallback(async () => {
    setBusy(true); setError(null)
    try { return await chatApi.start(projectId, book.id, sceneId, true) }
    catch (e) { setError(e as StoryApiError); return null } finally { setBusy(false) }
  }, [projectId, book.id, sceneId])

  const start = useCallback(async () => {
    setBusy(true); setError(null)
    // Tab sofort öffnen (sonst blockt der Browser das Popup nach dem await), Adresse danach setzen.
    const tab = window.open("", "_blank")
    try {
      const s = await chatApi.start(projectId, book.id, sceneId)
      setStarted(s)
      if (tab) tab.location.href = s.url
    } catch (e) {
      tab?.close()
      setError(e as StoryApiError)
    } finally { setBusy(false) }
  }, [projectId, book.id, sceneId])

  const addTools = useCallback(async () => {
    if (!info?.agent) return
    setBusy(true); setError(null)
    try { await chatApi.addTools(info.agent.id, info.tools_missing); await loadInfo() }
    catch (e) { setError(e as StoryApiError) } finally { setBusy(false) }
  }, [info, loadInfo])

  return { info, started, busy, error, start, openHere, addTools, refresh: poll }
}
