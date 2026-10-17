import { useState } from "react"
import { useTranslation } from "react-i18next"
import { planApi, type Shot } from "./planApi"
import { errorCode, moveShot, sceneOf } from "./planLogic"
import type { PlanState } from "./usePlan"

/** Shots der gewählten Szene: anlegen, speichern, löschen, sortieren, per Regie-Agent zerlegen (Spec „Bauplan 2b“). */
export function useShots(p: PlanState, projectId: string) {
  const { t } = useTranslation("studio")
  const [busy, setBusy] = useState<"decompose" | null>(null)
  const [confirm, setConfirm] = useState<{ sceneId: string; count: number } | null>(null)
  const scene = sceneOf(p.plan, p.selection)
  const sid = scene?.id ?? ""

  const decompose = async (sceneId: string, replace: boolean) => {
    setBusy("decompose")
    let created = 0
    const ok = await p.act(async () => { created = (await planApi.decompose(projectId, sceneId, replace)).count }, () => t("notice_decomposed", { count: created }),
      () => { setConfirm(null); p.select({ kind: "scene", id: sceneId }) },
      (e) => {
        if (errorCode(e) !== "studio_decompose_has_media") return false
        const sc = p.plan?.scenes.find((s) => s.id === sceneId)
        setConfirm({ sceneId, count: sc?.shots.length ?? 0 })        // Rückfrage statt Fehlermeldung
        return true
      })
    setBusy(null)
    return ok
  }

  return {
    scene, busy, confirm, closeConfirm: () => setConfirm(null),
    add: () => sid && p.act(() => planApi.addShot(projectId, sid, {}), t("notice_added"),
      (r) => p.select({ kind: "shot", sceneId: sid, id: (r as Shot).id })),
    save: (id: string, data: Partial<Shot>) => p.act(() => planApi.saveShot(projectId, sid, id, data), t("notice_saved")),
    remove: (id: string, index: number) => p.setDialog({ kind: "delete", target: "shot", id, sceneId: sid, name: t("shot", { n: index + 1 }) }),
    move: (id: string, dir: -1 | 1) => scene && p.act(() => planApi.orderShots(projectId, sid, moveShot(scene.shots.map((s) => s.id), id, dir)), t("notice_moved")),
    decompose: () => sid && decompose(sid, false),
    confirmReplace: () => confirm && decompose(confirm.sceneId, true),
  }
}

export type ShotsState = ReturnType<typeof useShots>
