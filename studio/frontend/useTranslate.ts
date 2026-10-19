import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { planApi, type Job } from "./planApi"
import { errorText } from "./planLogic"
import { finishedTranslate, translateApi, type LanguageList } from "./translateLogic"

const POLL_MS = 2000

/** Sprachen der Untertitel und „Übersetzen“ (Spec 6c): welche Sprache bearbeitet wird, Dialog, Auftrag verfolgen.
 *  Nach dem Übersetzen springt die Auswahl auf die neue Sprache. */
export function useTranslate(projectId: string, film: string, active: boolean, flush: () => Promise<void> | undefined,
  onNotice: (text: string) => void) {
  const { t } = useTranslation("studio")
  const [list, setList] = useState<LanguageList | null>(null)
  const [chosen, setChosen] = useState<{ pid: string; lang: string } | null>(null)
  const [open, setOpen] = useState(false)
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<Set<string>>(new Set())
  const say = useRef(onNotice)
  useEffect(() => { say.current = onNotice })
  const lang = chosen?.pid === projectId ? chosen.lang : film                   // anderes Projekt → wieder Filmsprache

  const load = useCallback(async () => {
    if (!projectId) return
    try { setList(await translateApi.languages(projectId)) } catch { setList(null) }
  }, [projectId])

  useEffect(() => {
    if (!active) return
    const id = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(id)
  }, [active, load])

  const pick = useCallback((l: string) => { void flush(); setChosen({ pid: projectId, lang: l }) }, [projectId, flush])

  const run = useCallback(async (to: string, replace: boolean) => {
    setBusy(true)
    try {
      await flush()
      const j = await translateApi.start(projectId, to, lang, replace)
      setJob(j)
      setPending((s) => new Set(s).add(j.id))
      say.current(t("translate_started", { name: t(`lang.${to}`) }))
    } catch (e) { say.current(errorText(t, e)) }
    finally { setBusy(false) }
  }, [projectId, lang, flush, t])

  const check = useCallback(async () => {
    let jobs: Job[]
    try { jobs = (await planApi.jobs(projectId)).jobs } catch { return }
    const mine = jobs.find((j) => pending.has(j.id))
    if (mine) setJob(mine)
    const done = finishedTranslate(jobs, pending)
    if (!done) return
    setPending((s) => { const n = new Set(s); n.delete(done.id); return n })
    await load()
    if (done.status === "done") {
      const to = String(done.result?.language ?? "")
      setOpen(false)
      if (to) setChosen({ pid: projectId, lang: to })
      say.current(t("translate_done", { name: t(`lang.${to}`), count: Number(done.result?.count ?? 0) }))
    }
  }, [projectId, pending, load, t])

  useEffect(() => {
    if (!active || pending.size === 0) return
    const id = window.setInterval(() => { void check() }, POLL_MS)
    return () => window.clearInterval(id)
  }, [active, pending, check])

  return { list, lang, pick, open, show: () => setOpen(true), close: () => setOpen(false), job: open ? job : null, busy,
    running: pending.size > 0, run: (to: string, replace: boolean) => void run(to, replace), reload: load }
}
