// Ghostwriter G4 – offene Vorschläge des Agenten nachfragen (Text, Szenen-Infos, Steckbriefe, Gliederung), solange
// ein Chat offen ist: Modus „Im Chat“ und Chat-Fenster im Storyteller (G4e). Alle 10 s, sofort beim Start.
import { useCallback, useEffect } from "react"
import { chatApi, proposalMarks } from "./chatApi"
import { infoMarks } from "./infoProposal"
import { notesApi } from "./teamNotes"
import type { BookState } from "./useBook"

export const POLL_MS = 10_000

export function useProposalPoll(state: BookState, active: boolean) {
  const { projectId, book, markProposals, setInfoProposals, setEntityProposals, setOutlineProposal, setNotes } = state
  const poll = useCallback(async () => {
    try { markProposals(proposalMarks(await chatApi.proposals(projectId, book.id))) } catch { /* nächste Abfrage */ }
    try { setInfoProposals(infoMarks(await chatApi.infoProposals(projectId, book.id))) } catch { /* nächste Abfrage */ }
    try { setEntityProposals(await chatApi.entityProposals(projectId, book.id)) } catch { /* nächste Abfrage */ }
    try { setOutlineProposal(await chatApi.outlineProposal(projectId, book.id)) } catch { /* nächste Abfrage */ }
    try { setNotes(await notesApi.list(projectId, book.id)) } catch { /* nächste Abfrage */ }   // T1d
  }, [projectId, book.id, markProposals, setInfoProposals, setEntityProposals, setOutlineProposal, setNotes])

  useEffect(() => {
    if (!active) return
    void poll()
    const timer = window.setInterval(() => { void poll() }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [active, poll])
  return poll
}
