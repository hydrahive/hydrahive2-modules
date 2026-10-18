import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { finishedHear, hearApi, type HearInfo } from "./hearLogic"
import { planApi, type Job } from "./planApi"
import { errorText } from "./planLogic"

const POLL_MS = 2000

/** „Aus dem Ton heraushören“ (Spec 6b): Dialog, Auftrag starten, nachfragen bis fertig; dann neu laden (`onDone`).
 *  Nachgefragt wird nur im Reiter „Untertitel“ (`active`); kommt man zurück, wird nachgeholt. */
export function useHear(projectId: string, lang: string, active: boolean, flush: () => Promise<void> | undefined,
  onDone: () => void, onNotice: (text: string) => void) {
  const { t } = useTranslation("studio")
  const [open, setOpen] = useState(false)
  const [info, setInfo] = useState<HearInfo | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<Set<string>>(new Set())
  const latest = useRef({ onDone, onNotice })
  useEffect(() => { latest.current = { onDone, onNotice } })

  const show = useCallback(async () => {
    setOpen(true)
    setInfo(null)
    try {
      await flush()                                     // erst eigene Änderungen speichern, dann zählt „vorhanden“ richtig
      setInfo(await hearApi.info(projectId, lang))
    } catch (e) { setOpen(false); latest.current.onNotice(errorText(t, e)) }
  }, [projectId, lang, flush, t])

  const run = useCallback(async () => {
    if (!info) return
    setBusy(true)
    try {
      const j = await hearApi.start(projectId, lang, info.existing > 0)
      setJob(j)
      setPending((s) => new Set(s).add(j.id))
      setOpen(false)
      latest.current.onNotice(t("hear_started"))
    } catch (e) { latest.current.onNotice(errorText(t, e)) }
    finally { setBusy(false) }
  }, [projectId, lang, info, t])

  const check = useCallback(async () => {
    let list: Job[]
    try { list = (await planApi.jobs(projectId)).jobs } catch { return }
    const mine = list.find((j) => pending.has(j.id))
    if (mine) setJob(mine)
    const done = finishedHear(list, pending)
    if (!done) return
    setPending((s) => { const n = new Set(s); n.delete(done.id); return n })
    latest.current.onDone()
    if (done.status === "done") latest.current.onNotice(t("hear_done", { count: Number(done.result?.count ?? 0) }))
    else void show()                                            // Fehler steht im Dialog
  }, [projectId, pending, t, show])

  useEffect(() => {
    if (!active || pending.size === 0) return
    const id = window.setInterval(() => { void check() }, POLL_MS)
    return () => window.clearInterval(id)
  }, [active, pending, check])

  return { open, info, job: open ? job : null, busy, running: pending.size > 0, show: () => void show(), run: () => void run(), close: () => setOpen(false) }
}
