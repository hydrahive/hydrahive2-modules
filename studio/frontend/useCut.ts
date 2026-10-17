import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { errorCode, errorText } from "./planLogic"
import type { Viewport } from "./timeline"
import { clipsOf, timelineApi, type Timeline } from "./timelineApi"

/** Zustand für „Schneiden“ (Etappe 4a): Schnittfassung laden, aus dem Drehbuch übernehmen (mit Rückfrage), Auswahl. */
export function useCut(projectId: string, active: boolean) {
  const { t } = useTranslation("studio")
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [view, setView] = useState<Viewport>({ start: 0, span: 30 })

  const load = useCallback(async () => {
    if (!projectId) { setTimeline(null); return }
    try { setTimeline(await timelineApi.get(projectId)) } catch (e) { setNotice(errorText(t, e)) }
  }, [projectId, t])

  useEffect(() => {
    if (!active) return
    const id = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(id)
  }, [active, load])

  useEffect(() => {
    if (!notice) return
    const id = window.setTimeout(() => setNotice(null), 2600)
    return () => window.clearTimeout(id)
  }, [notice])

  const fromPlan = useCallback(async (replace: boolean) => {
    setBusy(true)
    try {
      setTimeline(await timelineApi.fromPlan(projectId, replace))
      setSelected(null); setConfirm(false)
      setNotice(t("cut_notice_built"))
    } catch (e) {
      if (errorCode(e) === "studio_timeline_not_empty") setConfirm(true)
      else { setConfirm(false); setNotice(errorText(t, e)) }
    } finally { setBusy(false) }
  }, [projectId, t])

  const clips = clipsOf(timeline)
  return {
    timeline, setTimeline, clips, busy, notice, setNotice, confirm, selected, select: setSelected, reload: load, view, setView,
    clip: clips.find((c) => c.id === selected) ?? null,
    fromPlan: () => (clips.length ? setConfirm(true) : void fromPlan(false)),
    confirmReplace: () => void fromPlan(true),
    closeConfirm: () => setConfirm(false),
  }
}
