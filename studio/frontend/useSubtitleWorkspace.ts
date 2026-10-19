import { useCallback, useEffect, useRef } from "react"
import type { Plan } from "./planApi"
import type { Viewport } from "./timeline"
import { useHear } from "./useHear"
import { useSubtitleTab } from "./useSubtitleTab"
import { useSubtitles } from "./useSubtitles"
import { useTranslate } from "./useTranslate"

/** Reiter „Untertitel“ gebündelt (6a–6c): gewählte Sprache, Untertitel dieser Sprache, Heraushören, Übersetzen.
 *  Die Sprachwahl braucht das Speichern der Untertitel (vor dem Wechsel), die Untertitel brauchen die Sprache –
 *  deshalb geht `flush` über eine Ref. */
export function useSubtitleWorkspace(projectId: string, active: boolean, plan: Plan | null,
  o: { time: number; view: Viewport; onSeek: (t: number) => void }, notice: (text: string) => void) {
  const film = plan?.screenplay.language ?? ""
  const flushRef = useRef<() => Promise<void> | undefined>(() => undefined)
  const flush = useCallback(() => flushRef.current(), [])
  const tr = useTranslate(projectId, film, active, flush, notice)
  const sub = useSubtitles(projectId, tr.lang, active, o.time, notice)
  useEffect(() => { flushRef.current = sub.flush })
  const hear = useHear(projectId, film, active, sub.flush, () => { void sub.reload(); void tr.reload() }, notice)
  const st = useSubtitleTab(sub, hear, tr, { ...o, plan })
  return { st, sub }
}
