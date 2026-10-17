import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { planApi, type ElementKind, type ImportPreview, type Plan, type Selection } from "./planApi"
import { errorText, moveScene } from "./planLogic"

type Dialog = { kind: "import" } | { kind: "delete"; target: "scene" | "element"; id: string; name: string } | null

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

  const load = useCallback(async (pid: string) => {
    if (!pid) { setPlan(null); setPreview(null); return }
    setError(null)
    try {
      const [p, pre] = await Promise.all([planApi.get(pid), planApi.importPreview(pid)])
      setPlan(p); setPreview(pre); setRev((r) => r + 1)
      if (loadedFor.current !== pid) { setSelection(null); loadedFor.current = pid }   // anderes Projekt → Auswahl weg
    } catch (e) { setPlan(null); setError(errorText(t, e)) }
  }, [t])

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

  /** Eine Änderung ausführen: sperren, danach neu laden, Rückmeldung oder Fehler zeigen. */
  const act = useCallback(async (fn: () => Promise<unknown>, done: string, after?: (r: unknown) => void) => {
    setBusy(true); setError(null)
    try {
      const r = await fn()
      after?.(r)
      await load(projectId)
      setNotice(done)
    } catch (e) { setError(errorText(t, e)) } finally { setBusy(false) }
  }, [load, projectId, t])

  const pid = projectId
  return {
    plan, preview, selection, select: setSelection, rev, busy, error, notice, dialog, setDialog,
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
      const { target, id } = dialog
      void act(() => (target === "scene" ? planApi.deleteScene(pid, id) : planApi.deleteElement(pid, id)), t("notice_deleted"),
        () => { setSelection(null); setDialog(null) })
    },
    runImport: () => act(() => planApi.importRun(pid), t("notice_imported"), () => { setDialog(null); setSelection({ kind: "head" }) }),
  }
}

export type PlanState = ReturnType<typeof usePlan>
