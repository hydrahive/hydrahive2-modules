import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { planApi, type ElementKind, type ImportPreview, type Plan, type Selection } from "./planApi"
import { latestOnly } from "./latestOnly"
import { errorText, moveScene } from "./planLogic"

type Dialog = { kind: "import" } | { kind: "delete"; target: "scene" | "element" | "shot"; id: string; name: string; sceneId?: string } | null

/** Zustand für „Planen“: Planungsdaten des Projekts laden und speichern, Auswahl, Dialoge, Rückmeldungen. */
export function usePlan(projectId: string, active: boolean) {
  const { t } = useTranslation("studio")
  const [plan, setPlan] = useState<Plan | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [rev, setRev] = useState(0)                         // Formulare neu aufsetzen, sobald frische Daten da sind
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [dialog, setDialog] = useState<Dialog>(null)

  const loadedFor = useRef("")                              // Projekt der geladenen Daten
  const [guard] = useState(latestOnly)                       // späte Antworten eines vorigen Projekts verwerfen

  const load = useCallback(async (pid: string) => {
    if (!pid) { setPlan(null); setPreview(null); return }
    setError(null)
    try {
      const r = await guard.run(pid, () => Promise.all([planApi.get(pid), planApi.importPreview(pid)]))
      if (!r.current) return
      const [p, pre] = r.value
      setPlan(p); setPreview(pre); setRev((x) => x + 1)
      // anderes Projekt → Auswahl weg; beim ersten Laden bleibt eine schon gesetzte Auswahl (Sprung aus „Schneiden“)
      if (loadedFor.current && loadedFor.current !== pid) setSelection(null)
      loadedFor.current = pid
    } catch (e) { setPlan(null); setError(errorText(t, e)) }
  }, [t, guard])

  useEffect(() => {
    if (!active) return
    const id = window.setTimeout(() => { void load(projectId) }, 0)
    return () => window.clearTimeout(id)
  }, [projectId, active, load])

  useEffect(() => {
    if (!notice) return
    const id = window.setTimeout(() => setNotice(null), 2200)
    return () => window.clearTimeout(id)
  }, [notice])

  /** Eine Änderung ausführen: sperren, danach neu laden, Rückmeldung oder Fehler zeigen. `onError` kann einen Fehler
   *  selbst behandeln (true = keine Fehlermeldung). Liefert true bei Erfolg. */
  const act = useCallback(async (fn: () => Promise<unknown>, done: string | (() => string), after?: (r: unknown) => void,
    onError?: (e: unknown) => boolean): Promise<boolean> => {
    setBusy(true); setError(null)
    try {
      const r = await fn()
      after?.(r)
      await load(projectId)
      setNotice(typeof done === "function" ? done() : done)
      return true
    } catch (e) {
      if (!onError?.(e)) setError(errorText(t, e))
      return false
    } finally { setBusy(false) }
  }, [load, projectId, t])

  const pid = projectId
  return {
    plan, preview, selection, select: setSelection, rev, busy, error, notice, setNotice, dialog, setDialog, act, projectId: pid,
    reload: () => load(pid),
    saveHead: (h: Parameters<typeof planApi.saveHead>[1]) => act(() => planApi.saveHead(pid, h), t("notice_saved")),
    saveScene: (id: string, s: Parameters<typeof planApi.saveScene>[2]) => act(() => planApi.saveScene(pid, id, s), t("notice_saved")),
    saveElement: (id: string, e: Parameters<typeof planApi.saveElement>[2]) => act(() => planApi.saveElement(pid, id, e), t("notice_saved")),
    addScene: () => act(() => planApi.addScene(pid, { title: t("new_scene") }), t("notice_added"),
      (r) => setSelection({ kind: "scene", id: (r as { id: string }).id })),
    addElement: (kind: ElementKind) => act(() => planApi.addElement(pid, { kind, name: t(`new_${kind}`) }), t("notice_added"),
      (r) => setSelection({ kind: "element", id: (r as { id: string }).id })),
    move: (id: string, dir: -1 | 1) => plan && act(() => planApi.order(pid, moveScene(plan.scenes.map((s) => s.id), id, dir)), t("notice_moved")),
    confirmDelete: () => {
      if (dialog?.kind !== "delete") return
      const { target, id, sceneId } = dialog
      const run = target === "scene" ? () => planApi.deleteScene(pid, id)
        : target === "shot" && sceneId ? () => planApi.deleteShot(pid, sceneId, id) : () => planApi.deleteElement(pid, id)
      void act(run, t("notice_deleted"),
        () => { setSelection(target === "shot" && sceneId ? { kind: "scene", id: sceneId } : null); setDialog(null) })
    },
    runImport: () => act(() => planApi.importRun(pid), t("notice_imported"), () => { setDialog(null); setSelection({ kind: "head" }) }),
  }
}

export type PlanState = ReturnType<typeof usePlan>
