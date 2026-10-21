import { useCallback, useState } from "react"
import { mailApi, type Account, type MailDetail, type SavedDraft } from "./api"
import { emptyDraft, fromPrefill, type ComposeMode, type Draft } from "./composeFormat"

export interface OpenCompose {
  initial: Draft
  draftId: string | null
  originalAttachments: string[]
  key: number
}

/** Öffnet das Schreibfenster: neu, als Antwort/Weiterleitung (Vorlage vom Server) oder aus einem Entwurf. */
export function useComposeOpen(accounts: Account[], onError: (msg: string) => void) {
  const [compose, setCompose] = useState<OpenCompose | null>(null)

  const openNew = useCallback(() => {
    const first = accounts[0]
    if (first) setCompose({ initial: emptyDraft(first.id), draftId: null, originalAttachments: [], key: Date.now() })
  }, [accounts])

  const openReply = useCallback(async (mail: MailDetail, mode: Exclude<ComposeMode, "new">) => {
    try {
      const p = await mailApi.prefill(mail.account_id, mode, mail.id)
      setCompose({ initial: fromPrefill(mail.account_id, mode, mail.id, p), draftId: null,
        originalAttachments: p.attachments, key: Date.now() })
    } catch {
      onError("prefill")
    }
  }, [onError])

  const openDraft = useCallback((d: SavedDraft) => {
    const { id, updated_at: _u, server: _s, ...draft } = d
    setCompose({ initial: draft, draftId: id, originalAttachments: [], key: Date.now() })
  }, [])

  return { compose, openNew, openReply, openDraft, close: () => setCompose(null) }
}
