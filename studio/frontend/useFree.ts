import { useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import type { FreeFormState } from "./freeLogic"
import type { Job, Plan, Shot } from "./planApi"
import type { Timeline } from "./timelineApi"
import type { PlanState } from "./usePlan"

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}`

/** „Freies Bild“ und „+ Shot“ in „Erzeugen“ (B3): Formular, Auftrag starten, zuweisen, auf die Zeitleiste legen. */
export function useFree(p: PlanState, projectId: string, plan: Plan | null, onChanged: () => void) {
  const { t } = useTranslation("studio")
  const [open, setOpen] = useState(false)
  const [pickScene, setPickScene] = useState(false)
  const [form, setForm] = useState<FreeFormState>({ prompt: "", model: "", aspect: "", count: 1, refs: [] })
  const aspect = form.aspect || plan?.screenplay.aspect_ratio || "16:9"        // Standard: Format des Drehbuchs

  return {
    open, pickScene, form: { ...form, aspect }, setForm,
    toggle: () => { setOpen((o) => !o); setPickScene(false) },
    close: () => setOpen(false),
    run: () => p.act(() => api.post<Job>(`${base(projectId)}/plan/free-images`, {
      prompt: form.prompt, count: form.count, aspect_ratio: aspect, references: form.refs, ...(form.model ? { model: form.model } : {}),
    }), t("notice_free_started"), onChanged),
    addShot: (sceneId?: string) => {
      if (!sceneId) { setPickScene((x) => !x); return }
      setPickScene(false); setOpen(false)
      void p.act(() => api.post<Shot>(`${base(projectId)}/plan/scenes/${encodeURIComponent(sceneId)}/shots`, {}), t("notice_added"),
        (r) => p.select({ kind: "shot", sceneId, id: (r as Shot).id }))
    },
    assign: (sceneId: string, shotId: string, rel: string) => p.act(
      () => api.put<Shot>(`${base(projectId)}/plan/scenes/${encodeURIComponent(sceneId)}/shots/${encodeURIComponent(shotId)}/assign`, { image_rel: rel }),
      t("notice_free_assigned"), onChanged),
    timeline: (rel: string) => p.act(() => api.post<Timeline>(`${base(projectId)}/timeline/append`, { media_rel: rel }),
      t("notice_free_timeline"), onChanged),
  }
}

export type FreeState = ReturnType<typeof useFree>
