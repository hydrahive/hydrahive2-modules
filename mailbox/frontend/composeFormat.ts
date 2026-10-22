/** Reine Logik des Schreibfensters (testbar ohne DOM). Empfänger/Zitat baut der Server (gleiche Regeln wie beim Senden). */

export type ComposeMode = "new" | "reply" | "reply_all" | "forward"

export interface Draft {
  account_id: string
  to: string
  cc: string
  bcc: string
  subject: string
  body: string
  mode: ComposeMode
  ref_message: number | null
  with_attachments: boolean
}

export interface Prefill {
  to: string
  cc: string
  subject: string
  quote: string
  attachments: string[]
}

export const MAX_ATTACH = 25 * 1024 * 1024
/** Starlette nimmt je Formularfeld höchstens 1 MiB (Bytes) – etwas Luft für den Formular-Rahmen. */
export const MAX_TEXT_BYTES = 1000 * 1024

export function emptyDraft(accountId: string): Draft {
  return { account_id: accountId, to: "", cc: "", bcc: "", subject: "", body: "", mode: "new", ref_message: null,
    with_attachments: false }
}

export function fromPrefill(accountId: string, mode: ComposeMode, ref: number, p: Prefill): Draft {
  return { ...emptyDraft(accountId), mode, ref_message: ref, to: p.to, cc: p.cc, subject: p.subject,
    body: `\n\n${p.quote}`, with_attachments: mode === "forward" }
}

/** Antworten kennen ihre Empfänger aus dem Original; sonst braucht es mindestens einen. */
export function recipientsOk(d: Draft): boolean {
  if ((d.mode === "reply" || d.mode === "reply_all") && d.ref_message != null) return true
  return [d.to, d.cc, d.bcc].some((v) => v.trim() !== "")
}

export function attachmentsTooBig(files: { size: number }[]): boolean {
  return files.reduce((n, f) => n + f.size, 0) > MAX_ATTACH
}

export function buildSendForm(d: Draft, files: File[], draftId: string | null): FormData {
  const f = new FormData()
  f.set("account_id", d.account_id)
  for (const k of ["to", "cc", "bcc", "subject", "body", "mode"] as const) f.set(k, d[k])
  if (d.ref_message != null) f.set("ref_message", String(d.ref_message))
  f.set("with_attachments", d.with_attachments ? "true" : "false")
  if (draftId) f.set("draft_id", draftId)
  for (const file of files) f.append("files", file)
  return f
}

export function draftKey(d: Draft): string {
  return JSON.stringify([d.account_id, d.to, d.cc, d.bcc, d.subject, d.body, d.mode, d.ref_message, d.with_attachments])
}

export function isDirty(now: Draft, saved: Draft): boolean {
  return draftKey(now) !== draftKey(saved)
}

/** Welche Aktionen vorher bestätigt werden müssen (Löschen – auch wenn die Mail im Archiv bleibt). */
export function needsConfirm(action: string): boolean {
  return action === "delete"
}

export function textTooLong(text: string): boolean {
  return new TextEncoder().encode(text).length > MAX_TEXT_BYTES
}

/** Hinweis nach einer Aktion (Text-Schlüssel). Löschen außerhalb des Papierkorbs = nur verschoben – sonst wundert man
 *  sich, dass die Mail nicht unter „Nur im Archiv“ steht (Befund Till 22.10.2026). */
export function afterActionNote(action: string, folderRole: string, done: number): string | null {
  if (action !== "delete" || done === 0) return null
  return folderRole === "trash" ? "action.deletedForever" : "action.movedToTrash"
}
