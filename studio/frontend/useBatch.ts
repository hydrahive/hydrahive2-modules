import { useState } from "react"
import { useTranslation } from "react-i18next"
import { activeBatch } from "./jobLogic"
import { planApi, type BatchKind, type BatchPreview, type Job } from "./planApi"
import type { PlanState } from "./usePlan"

/** Sammelaufträge: Rückfrage öffnen (mit Vorschau), starten, abbrechen. Fortschritt kommt aus den Aufträgen. */
export function useBatch(p: PlanState, projectId: string, jobs: Job[], onStarted: () => void) {
  const { t } = useTranslation("studio")
  const [dialog, setDialog] = useState<{ kind: BatchKind; preview: BatchPreview | null } | null>(null)
  const [cancelling, setCancelling] = useState<string | null>(null)
  const active = activeBatch(jobs)

  const open = async (kind: BatchKind) => {
    setDialog({ kind, preview: null })
    try {
      const preview = await planApi.batchPreview(projectId, kind)
      setDialog((d) => (d && d.kind === kind ? { kind, preview } : d))
    } catch {
      setDialog(null)
    }
  }

  return {
    active, dialog, open, close: () => setDialog(null),
    cancelling: !!active && cancelling === active.id,
    run: () => dialog && p.act(() => planApi.batchStart(projectId, dialog.kind), t("notice_batch_started"), () => { setDialog(null); onStarted() }),
    cancel: () => {
      if (!active) return
      setCancelling(active.id)
      void p.act(() => planApi.cancelJob(projectId, active.id), t("notice_batch_cancelling"))
    },
  }
}
