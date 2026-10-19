/** G1: Zustand des geführten Wegs mit echten Daten – Projekt, Plan, Schritt „Idee“. Schritte 2–5 folgen (G2–G5). */
import { useCallback, useEffect, useState } from "react"
import { studioApi, type StudioProject } from "../api"
import { draftApi } from "../draftApi"
import { PROJECT_KEY, pickProject } from "../libraryView"
import { planApi, type Plan } from "../planApi"
import { errorText } from "../planLogic"
import { ideaBody, sceneFromText, sceneTextPatch, type FilmKind, type StepId } from "./guidedLogic"

type T = (k: string, o?: Record<string, unknown>) => string
const remembered = () => { try { return globalThis.localStorage?.getItem(PROJECT_KEY) ?? null } catch { return null } }

export function useGuided(t: T) {
  const [projects, setProjects] = useState<StudioProject[] | null>(null)
  const [pid, setPidRaw] = useState("")
  const [plan, setPlan] = useState<Plan | null>(null)
  const [step, setStep] = useState<StepId>(1)
  const [idea, setIdea] = useState("")
  const [kind, setKind] = useState<FilmKind>("trailer")
  const [length, setLength] = useState(1)
  const [busy, setBusy] = useState(false)
  const [writing, setWriting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)
  const [deleting, setDeleting] = useState<{ id: string; n: number } | null>(null)

  useEffect(() => {
    studioApi.projects().then(({ projects }) => { setProjects(projects); setPidRaw(pickProject(projects, remembered())) })
      .catch((e) => { setProjects([]); setError(errorText(t, e)) })
  }, [t])

  const reload = useCallback(async (id: string) => {
    if (!id) { setPlan(null); return }
    try {
      const p = await planApi.get(id)
      setPlan(p); setIdea((cur) => cur || p.screenplay.description)
    } catch (e) { setError(errorText(t, e)) }
  }, [t])
  useEffect(() => { const h = window.setTimeout(() => { void reload(pid) }, 0); return () => window.clearTimeout(h) }, [pid, reload])

  const setPid = (id: string) => {
    setPidRaw(id); setPlan(null); setIdea(""); setError(null); setSaved(null)
    try { globalThis.localStorage?.setItem(PROJECT_KEY, id) } catch { /* nicht merken */ }
  }

  /** Eine Aktion mit Sperre, Fehlertext und neu geladenem Plan */
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(null)
    try { await fn(); await reload(pid) } catch (e) { setError(errorText(t, e)) } finally { setBusy(false) }
  }

  /** Idee → Geschichte → gleich übernehmen (G1: kein Vorschau-Zwischenschritt) */
  const write = async (replace: boolean) => {
    setAsking(false); setWriting(true)
    await run(async () => {
      await planApi.saveHead(pid, { description: idea.trim() })
      const { draft } = await draftApi.ideaGuided(pid, ideaBody(idea, kind, length))
      await draftApi.apply(pid, draft, replace)
    })
    setWriting(false)
  }
  const startSuggest = () => { if (plan?.scenes.length) setAsking(true); else void write(false) }

  const setFormat = (aspect_ratio: string) => void run(() => planApi.saveHead(pid, { aspect_ratio }))

  const changeText = (id: string, text: string) => {
    const sc = plan?.scenes.find((s) => s.id === id)
    if (!sc) return
    const patch = sceneTextPatch(sc, text)
    void run(async () => {
      await planApi.saveScene(pid, id, patch.scene)
      if (patch.shot) await planApi.saveShot(pid, id, patch.shot.id, { prompt: patch.shot.prompt })
      setSaved(id)
    })
  }

  const addScene = (text = "") => void run(async () => {
    const n = sceneFromText(text)
    const sc = await planApi.addScene(pid, text ? n.scene : {})
    await planApi.addShot(pid, sc.id, n.shot)
  })

  const move = (id: string, dir: -1 | 1) => {
    const order = plan?.scenes.map((s) => s.id) ?? []
    const i = order.indexOf(id); const j = i + dir
    if (i < 0 || j < 0 || j >= order.length) return
    const next = [...order]; [next[i], next[j]] = [next[j], next[i]]
    void run(() => planApi.order(pid, next))
  }

  const confirmDelete = () => {
    const d = deleting
    if (!d) return
    void run(() => planApi.deleteScene(pid, d.id)).then(() => setDeleting(null))
  }

  return {
    projects, pid, setPid, plan, step, setStep, idea, setIdea, kind, setKind, length, setLength,
    busy, writing, error, saved, asking, setAsking, deleting, setDeleting,
    startSuggest, write, setFormat, changeText, addScene, move, confirmDelete,
  }
}

export type GuidedState = ReturnType<typeof useGuided>
