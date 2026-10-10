// Ghostwriter G4 – offene Vorschläge des Agenten nachfragen (Text, Szenen-Infos, Steckbriefe, Gliederung, C2: Umbau),
// solange ein Chat offen ist: Modus „Im Chat“ und Chat-Fenster im Storyteller (G4e). Alle 10 s, sofort beim Start.
// C2: Hat der Autor die Gliederung direkt geändert (Version auf dem Server höher) und ist lokal nichts ungespeichert,
// wird das Buch neu geholt und die Gliederung samt neuer Szenen übernommen; sonst greift beim Speichern der Konflikt-Dialog.
import { useCallback, useEffect } from "react"
import { storyApi } from "./api"
import { chatApi, proposalMarks } from "./chatApi"
import { infoMarks } from "./infoProposal"
import { needsStructureReload, restructureApi } from "./restructure"
import { notesApi } from "./teamNotes"
import type { BookState } from "./useBook"

export const POLL_MS = 10_000

export function useProposalPoll(state: BookState, active: boolean) {
  const { projectId, book, markProposals, setInfoProposals, setEntityProposals, setOutlineProposal, setNotes,
    setRestructureProposal, structureVersion, isDirty, adoptStructure } = state
  const poll = useCallback(async () => {
    try { markProposals(proposalMarks(await chatApi.proposals(projectId, book.id))) } catch { /* nächste Abfrage */ }
    try { setInfoProposals(infoMarks(await chatApi.infoProposals(projectId, book.id))) } catch { /* nächste Abfrage */ }
    try { setEntityProposals(await chatApi.entityProposals(projectId, book.id)) } catch { /* nächste Abfrage */ }
    try { setOutlineProposal(await chatApi.outlineProposal(projectId, book.id)) } catch { /* nächste Abfrage */ }
    try { setRestructureProposal(await restructureApi.get(projectId, book.id)) } catch { /* nächste Abfrage */ }   // C2
    try { setNotes(await notesApi.list(projectId, book.id)) } catch { /* nächste Abfrage */ }   // T1d
    try {   // C2: erst nur die Gliederung; das ganze Buch (mit neuen Szenen) nur, wenn der Autor umgebaut hat
      const st = await storyApi.getStructure(projectId, book.id)
      if (needsStructureReload(structureVersion(), st.version, isDirty())) {
        const full = await storyApi.openBook(projectId, book.id)
        if (needsStructureReload(structureVersion(), full.structure.version, isDirty())) {
          adoptStructure(full.structure, Object.values(full.scenes))
        }
      }
    } catch { /* nächste Abfrage */ }
  }, [projectId, book.id, markProposals, setInfoProposals, setEntityProposals, setOutlineProposal, setNotes,
    setRestructureProposal, structureVersion, isDirty, adoptStructure])

  useEffect(() => {
    if (!active) return
    void poll()
    const timer = window.setInterval(() => { void poll() }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [active, poll])
  return poll
}
