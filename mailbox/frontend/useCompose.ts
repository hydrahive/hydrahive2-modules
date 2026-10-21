import { useCallback, useEffect, useRef, useState } from "react"
import { mailApi, type SendResult } from "./api"
import { attachmentsTooBig, buildSendForm, isDirty, recipientsOk, type Draft } from "./composeFormat"

export type ComposeStatus =
  | { kind: "idle" } | { kind: "sending" } | { kind: "sent"; result: SendResult }
  | { kind: "error"; code: string } | { kind: "invalid"; reason: "recipient" | "size" }

const AUTOSAVE_MS = 4000

/** Zustand des Schreibfensters: Felder, Anhänge, Entwurf automatisch speichern (nur wenn geändert), Senden.
 *  Nach erfolgreichem Senden wird nichts mehr gespeichert (kein Entwurf einer gesendeten Mail). */
export function useCompose(initial: Draft, initialDraftId: string | null) {
  const [draft, setDraft] = useState<Draft>(initial)
  const [files, setFiles] = useState<File[]>([])
  const [draftId, setDraftId] = useState<string | null>(initialDraftId)
  const [saved, setSaved] = useState<{ at: string; local: boolean } | null>(null)
  const [status, setStatus] = useState<ComposeStatus>({ kind: "idle" })
  const lastSaved = useRef<Draft>(initial)
  const done = useRef(false)
  const saving = useRef<Promise<unknown> | null>(null)

  const set = useCallback(<K extends keyof Draft>(k: K, v: Draft[K]) => setDraft((d) => ({ ...d, [k]: v })), [])

  const save = useCallback(async (d: Draft): Promise<void> => {
    if (done.current || !isDirty(d, lastSaved.current)) return
    const p = mailApi.saveDraft(d, draftId).then((r) => {
      lastSaved.current = d
      setDraftId(r.id)
      setSaved({ at: new Date().toLocaleTimeString(), local: r.server === "local_only" })
    }).catch(() => { /* Speichern ist Komfort – Senden geht trotzdem */ })
    saving.current = p
    await p
  }, [draftId])

  useEffect(() => {
    const t = window.setTimeout(() => void save(draft), AUTOSAVE_MS)
    return () => window.clearTimeout(t)
  }, [draft, save])

  const send = useCallback(async () => {
    if (!recipientsOk(draft)) { setStatus({ kind: "invalid", reason: "recipient" }); return }
    if (attachmentsTooBig(files)) { setStatus({ kind: "invalid", reason: "size" }); return }
    setStatus({ kind: "sending" })
    if (saving.current) await saving.current          // laufendes Speichern abwarten (sonst Entwurf nach dem Senden)
    try {
      const result = await mailApi.send(buildSendForm(draft, files, draftId))
      done.current = true
      setStatus({ kind: "sent", result })
    } catch (e) {
      // api-client gibt nur code + status weiter (keine params) → Grenze ohne Minutenangabe melden
      const err = e as Error & { status?: number; code?: string }
      setStatus({ kind: "error", code: err.status === 429 ? "rate_limited" : (err.code ?? "generic") })
    }
  }, [draft, files, draftId])

  const discard = useCallback(async () => {
    done.current = true
    if (draftId) await mailApi.deleteDraft(draftId).catch(() => {})
  }, [draftId])

  return { draft, set, files, setFiles, draftId, saved, status, send, discard, saveNow: () => save(draft) }
}
