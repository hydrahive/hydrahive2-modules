import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { finishedMusic, musicApi, type MusicDefaults, type MusicRequest, type MusicResult } from "./musicLogic"
import { planApi, type Job } from "./planApi"
import { errorText } from "./planLogic"

const POLL_MS = 3000

/** „Musik erzeugen“ (Spec „Nachtrag 5c-2“): Formular, Auftrag starten, nachfragen, bis er fertig ist; dann legt
 *  `place` die Musik auf die Zeitleiste. Nachgefragt wird nur, solange der Reiter offen ist (`active`) – kommt man
 *  zurück, wird nachgeholt. */
export function useMusic(projectId: string, active: boolean, place: (r: MusicResult) => boolean, onNotice: (text: string) => void,
  onDone: () => void) {
  const { t } = useTranslation("studio")
  const [open, setOpen] = useState(false)
  const [defaults, setDefaults] = useState<MusicDefaults | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<Set<string>>(new Set())
  const latest = useRef({ place, onNotice, onDone })
  useEffect(() => { latest.current = { place, onNotice, onDone } })

  const show = useCallback(() => {
    setOpen(true)
    setDefaults(null)
    musicApi.defaults(projectId).then(setDefaults, (e) => { setOpen(false); latest.current.onNotice(errorText(t, e)) })
  }, [projectId, t])

  const run = useCallback(async (r: MusicRequest) => {
    setBusy(true)
    try {
      const j = await musicApi.start(projectId, r)
      setJob(j)
      setPending((s) => new Set(s).add(j.id))
      setOpen(false)
      onNotice(t("music_started"))
    } catch (e) { onNotice(errorText(t, e)) }
    finally { setBusy(false) }
  }, [projectId, onNotice, t])

  const check = useCallback(async () => {
    let list: Job[]
    try { list = (await planApi.jobs(projectId)).jobs } catch { return }
    const mine = list.find((j) => pending.has(j.id))
    if (mine) setJob(mine)
    const done = finishedMusic(list, pending)
    if (!done) return
    setPending((s) => { const n = new Set(s); n.delete(done.id); return n })
    const { place: put, onNotice: say, onDone: after } = latest.current
    after()
    if (done.status !== "done") { show(); return }                                       // Fehler steht im Formular
    say(t(put(done.result as unknown as MusicResult) ? "music_placed" : "music_started"))
  }, [projectId, pending, t, show])

  useEffect(() => {
    if (!active || pending.size === 0) return
    const id = window.setInterval(() => { void check() }, POLL_MS)
    return () => window.clearInterval(id)
  }, [active, pending, check])

  const running = pending.size > 0
  return { open, defaults, job: open ? job : null, busy, running, show, run, close: () => setOpen(false) }
}
