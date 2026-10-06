// Schnappschüsse einer Szene liegen auf dem Server (snapshots/<szene>/…, höchstens 50; gleicher
// Text wie der letzte → kein neuer). Die Liste kommt ohne Text; den holt erst „Wiederherstellen“.
import { useCallback, useMemo, useState } from "react"
import { storyApi, type SnapshotInfo } from "./api"
import type { BookSync } from "./bookSync"
import { findScene } from "./model"

export function useSnapshots(projectId: string, bookId: string, sync: BookSync) {
  const [snapshots, setSnapshots] = useState<Record<string, SnapshotInfo[]>>({})
  const [snapError, setSnapError] = useState("")
  const fail = (e: unknown) => setSnapError(e instanceof Error ? e.message : String(e))

  const refresh = useCallback(async (sceneId: string) => {
    try {
      const list = await storyApi.listSnapshots(projectId, bookId, sceneId)
      setSnapshots((all) => ({ ...all, [sceneId]: list }))
      setSnapError("")
    } catch (e) { fail(e) }
  }, [projectId, bookId])

  /** Stand sichern, den der Nutzer gerade sieht (auch wenn das Speichern noch läuft). */
  const snapshot = useCallback(async (sceneId: string): Promise<boolean> => {
    const text = findScene(sync.book, sceneId)?.scene.text ?? ""
    try {
      await storyApi.addSnapshot(projectId, bookId, sceneId, text)
      await refresh(sceneId)
      return true
    } catch (e) { fail(e); return false }
  }, [projectId, bookId, sync, refresh])

  /** Schnappschuss zurückholen: erst den jetzigen Stand sichern, dann den alten Text einsetzen. */
  const restore = useCallback(async (sceneId: string, snapId: string): Promise<boolean> => {
    try {
      const snap = await storyApi.getSnapshot(projectId, bookId, sceneId, snapId)
      if (!(await snapshot(sceneId))) return false
      sync.replaceText(sceneId, snap.text ?? "")
      return true
    } catch (e) { fail(e); return false }
  }, [projectId, bookId, sync, snapshot])

  return useMemo(() => ({ snapshots, snapError, refresh, snapshot, restore }), [snapshots, snapError, refresh, snapshot, restore])
}
