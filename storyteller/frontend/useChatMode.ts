// Ghostwriter G4 – Modus „Im Chat“: Projekt-Agent + fehlende Werkzeuge laden, Chat-Sitzung anlegen und im neuen
// Tab öffnen, solange der Modus offen ist alle 10 s nach neuen Vorschlägen des Agenten fragen (Spec §11.3).
import { useCallback, useEffect, useState } from "react"
import { StoryApiError } from "./api"
import { chatApi, proposalMarks, type ChatInfo, type ChatStart } from "./chatApi"
import { infoMarks } from "./infoProposal"
import type { BookState } from "./useBook"

export const POLL_MS = 10_000

export function useChatMode(state: BookState, sceneId: string) {
  const { projectId, book, markProposals, setInfoProposals, setEntityProposals } = state
  const [info, setInfo] = useState<ChatInfo | null>(null)
  const [started, setStarted] = useState<ChatStart | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<StoryApiError | null>(null)

  const loadInfo = useCallback(async () => {
    try { setInfo(await chatApi.info(projectId, book.id)); setError(null) } catch (e) { setError(e as StoryApiError) }
  }, [projectId, book.id])

  const poll = useCallback(async () => {
    try { markProposals(proposalMarks(await chatApi.proposals(projectId, book.id))) } catch { /* nächste Abfrage */ }
    try { setInfoProposals(infoMarks(await chatApi.infoProposals(projectId, book.id))) } catch { /* nächste Abfrage */ }
    try { setEntityProposals(await chatApi.entityProposals(projectId, book.id)) } catch { /* nächste Abfrage */ }
  }, [projectId, book.id, markProposals, setInfoProposals, setEntityProposals])

  useEffect(() => {
    let alive = true
    chatApi.info(projectId, book.id)
      .then((x) => { if (alive) { setInfo(x); setError(null) } })
      .catch((e: unknown) => { if (alive) setError(e as StoryApiError) })
    void poll()
    const timer = window.setInterval(() => { void poll() }, POLL_MS)
    return () => { alive = false; window.clearInterval(timer) }
  }, [projectId, book.id, poll])

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

  return { info, started, busy, error, start, addTools, refresh: poll }
}
