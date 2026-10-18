import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { History } from "./cutHistory"
import { AutoSaver, type SaveState } from "./cutSave"
import { errorCode, errorText } from "./planLogic"
import type { SubAction } from "./SubtitleList"
import {
  addCue, download, editCue, joinCues, removeCue, splitCue, subtitleApi, type Cue, type SubtitleFormat, type Subtitles,
} from "./subtitleLogic"

const newId = () => crypto.randomUUID().replace(/-/g, "")

/** Reiter „Untertitel“ (Spec 6a): laden, bearbeiten mit Rückgängig, automatisch speichern, aus den Sprechtexten
 *  erzeugen (bei vorhandenen Untertiteln mit Rückfrage), herunterladen. Eine Textänderung am selben Eintrag ist ein
 *  Rückgängig-Schritt (wie eine Reglerbewegung). */
export function useSubtitles(projectId: string, lang: string, active: boolean, time: number, onNotice: (text: string) => void) {
  const { t } = useTranslation("studio")
  const [subs, setSubs] = useState<Subtitles | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [save, setSave] = useState<SaveState>("saved")
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [flags, setFlags] = useState({ undo: false, redo: false })
  const [hist] = useState(() => new History<Cue[]>([]))
  const saver = useRef<AutoSaver<{ revision: number; cues: Cue[] }> | null>(null)
  const lastText = useRef("")
  const say = useRef(onNotice)
  useEffect(() => { say.current = onNotice })

  useEffect(() => {
    const s = new AutoSaver<{ revision: number; cues: Cue[] }>((x) => subtitleApi.save(projectId, lang, x), setSave, "studio_subtitles_conflict")
    saver.current = s
    return () => { void s.flush() }
  }, [projectId, lang])

  const loaded = useCallback((s: Subtitles) => {
    setSubs(s)
    hist.reset(s.cues)
    lastText.current = ""
    setFlags({ undo: false, redo: false })
    saver.current?.loaded(s)
  }, [hist])

  const load = useCallback(async () => {
    if (!projectId || !lang) return
    try { loaded(await subtitleApi.get(projectId, lang)) } catch (e) { say.current(errorText(t, e)) }
  }, [projectId, lang, loaded, t])

  useEffect(() => {
    if (!active) return
    const id = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(id)
  }, [active, load])

  const apply = useCallback((cues: Cue[], record: "push" | "replace" | "none" = "push") => {
    if (!subs) return
    if (record === "push") hist.push(cues)
    else if (record === "replace") hist.replaceTop(cues)
    if (record !== "replace") lastText.current = ""
    setFlags({ undo: hist.canUndo, redo: hist.canRedo })
    setSubs({ ...subs, cues })
    saver.current?.change({ revision: subs.revision, cues })
  }, [subs, hist])

  const cues = useMemo(() => subs?.cues ?? [], [subs])
  const changeText = useCallback((id: string, text: string) => {
    const same = lastText.current === id && hist.canUndo
    apply(editCue(cues, id, { text }), same ? "replace" : "push")
    lastText.current = id                                          // weiteres Tippen im selben Eintrag ersetzt den Schritt
  }, [cues, apply, hist])

  /** Zeiten im Feld rechts: wie Text – weiteres Tippen im selben Feld ersetzt den Schritt. */
  const setTime = useCallback((id: string, v: { start?: number; end?: number }) => {
    const key = `${id}:${Object.keys(v)[0]}`
    const same = lastText.current === key && hist.canUndo
    apply(editCue(cues, id, v), same ? "replace" : "push")
    lastText.current = key
  }, [cues, apply, hist])

  const action = useCallback((a: SubAction) => {
    if (a === "undo" || a === "redo") {
      if (a === "undo" ? hist.canUndo : hist.canRedo) apply(a === "undo" ? hist.undo() : hist.redo(), "none")
      return
    }
    if (a === "add") {
      const r = addCue(cues, time, t("sub_new_text"), newId)
      if (r.cue) { apply(r.cues); setSelected(r.cue.id) }
      return
    }
    if (!selected) return
    const next = a === "split" ? splitCue(cues, selected, time, newId) : a === "join" ? joinCues(cues, selected) : removeCue(cues, selected)
    if (next !== cues) apply(next)
    if (a === "delete") setSelected(null)
  }, [cues, selected, time, apply, hist, t])

  const fromSpeech = useCallback(async (replace: boolean) => {
    setBusy(true)
    try {
      const r = await subtitleApi.fromSpeech(projectId, lang, replace)
      setConfirm(false)
      loaded(r)
      setSelected(null)
      say.current(r.skipped ? t("sub_built_skipped", { count: r.cues.length, skipped: r.skipped }) : t("sub_built", { count: r.cues.length }))
    } catch (e) {
      if (errorCode(e) === "studio_subtitles_not_empty") setConfirm(true)
      else { setConfirm(false); say.current(errorText(t, e)) }
    } finally { setBusy(false) }
  }, [projectId, lang, loaded, t])

  const exportFile = useCallback(async (format: SubtitleFormat) => {
    try {
      await saver.current?.flush()
      download(await subtitleApi.file(projectId, lang, format))
    } catch (e) { say.current(errorText(t, e)) }
  }, [projectId, lang, t])

  return {
    cues, selected, select: setSelected, save, busy, confirm, canUndo: flags.undo, canRedo: flags.redo,
    changeText, setTime, action, reload: load, flush: () => saver.current?.flush(),
    fromSpeech: () => (cues.length ? setConfirm(true) : void fromSpeech(false)),
    confirmReplace: () => void fromSpeech(true), closeConfirm: () => setConfirm(false),
    exportFile: (f: SubtitleFormat) => void exportFile(f),
  }
}
