import { useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import type { FreeFormState } from "./freeLogic"
import type { Job, Plan, Shot } from "./planApi"
import type { Timeline } from "./timelineApi"
import type { PlanState } from "./usePlan"

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}`

/** „Einzelbild (ohne Szene)“ in „Erzeugen“ (B3, C4): Formular, Auftrag starten, zuweisen, auf die Zeitleiste legen. */
export function useFree(p: PlanState, projectId: string, plan: Plan | null, onChanged: () => void) {
  const { t } = useTranslation("studio")
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<FreeFormState>({ prompt: "", model: "", aspect: "", count: 1, refs: [] })
  const aspect = form.aspect || plan?.screenplay.aspect_ratio || "16:9"        // Standard: Format des Drehbuchs

  return {
    open, form: { ...form, aspect }, setForm,
    toggle: () => setOpen((o) => !o),
    close: () => setOpen(false),
    run: () => p.act(() => api.post<Job>(`${base(projectId)}/plan/free-images`, {
      prompt: form.prompt, count: form.count, aspect_ratio: aspect, references: form.refs, ...(form.model ? { model: form.model } : {}),
    }), t("notice_free_started"), onChanged),
    assign: (sceneId: string, shotId: string, rel: string) => p.act(
      () => api.put<Shot>(`${base(projectId)}/plan/scenes/${encodeURIComponent(sceneId)}/shots/${encodeURIComponent(shotId)}/assign`, { image_rel: rel }),
      t("notice_free_assigned"), onChanged),
    timeline: (rel: string) => p.act(() => api.post<Timeline>(`${base(projectId)}/timeline/append`, { media_rel: rel }),
      t("notice_free_timeline"), onChanged),
  }
}

export type FreeState = ReturnType<typeof useFree>
