import { useEffect, useMemo, useState } from "react"
import type { Edge } from "@xyflow/react"
import { blueprintApi } from "./api"
import { parseGraph, proposalDiff } from "./boardGraph"
import { errorText } from "./boardView"
import type { T } from "./texts.de"
import type { Board, BoardVersion, BPNode } from "./types"
import type { BoardActions } from "./useBoard"

/** Der offene Vorschlag des Agenten: Vergleich mit der eigenen Fassung, Vorschau, Übernehmen, Verwerfen. */
export function useProposal(board: Board | null, nodes: BPNode[], edges: Edge[], actions: BoardActions, t: T) {
  const [previewOn, setPreviewOn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const raw = board?.proposal_json ?? null
  const graph = useMemo(() => (raw === null ? null : parseGraph(raw)), [raw])
  const diff = useMemo(() => (graph ? proposalDiff({ nodes, edges }, graph) : null), [graph, nodes, edges])

  async function run(step: () => Promise<boolean>) {
    setBusy(true)
    setError(null)
    try {
      if (await step()) setPreviewOn(false)
      else setError(t("proposal_unsaved"))
    } catch (problem) {
      setError(errorText(problem, t))
      void actions.poll()  // der Vorschlag kann sich geändert haben: gleich nachsehen
    } finally {
      setBusy(false)
    }
  }

  return {
    open: board !== null && raw !== null,
    graph, diff, busy, error,
    /** Vorschau nur, solange es einen lesbaren Vorschlag gibt. */
    preview: previewOn && graph !== null,
    togglePreview: () => { setError(null); setPreviewOn((on) => !on) },
    accept: () => board && run(() => actions.apply(() => blueprintApi.acceptProposal(board.id, board.proposal_at))),
    discard: () => board && run(async () => { actions.adopt(await blueprintApi.discardProposal(board.id)); return true }),
  }
}

/** Frühere Fassungen: laden, solange die Liste offen ist, und nach jeder neuen Fassung erneut. */
export function useVersions(boardId: number, open: boolean, revision: number | undefined, actions: BoardActions, t: T) {
  const [versions, setVersions] = useState<BoardVersion[] | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    blueprintApi.versions(boardId)
      .then((list) => { if (!cancelled) { setVersions(list); setLoadFailed(false) } })
      .catch(() => { if (!cancelled) setLoadFailed(true) })
    return () => { cancelled = true }
  }, [boardId, open, revision])

  async function restore(versionId: number) {
    setBusy(true)
    setMessage(null)
    try {
      const done = await actions.apply(() => blueprintApi.restoreVersion(boardId, versionId))
      if (!done) setMessage(t("proposal_unsaved"))
    } catch (problem) {
      setMessage(errorText(problem, t))
    } finally {
      setBusy(false)
    }
  }

  return { versions, loadFailed, busy, message, restore }
}
