import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Paperclip, Send, Trash2, X } from "lucide-react"
import type { Account } from "./api"
import type { Draft } from "./composeFormat"
import { size } from "./mailFormat"
import { useCompose, type ComposeStatus } from "./useCompose"

interface Props {
  accounts: Account[]
  initial: Draft
  draftId: string | null
  originalAttachments?: string[]
  onClose: (sent: boolean) => void
}

const FIELD = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1 text-sm text-[#e8eef8]"

/** Schreibfenster (Spec §6): Absenderkonto, An/Cc/Bcc, Betreff, Text, Anhänge. Entwurf speichert sich selbst.
 *  Text nur als Text (Server baut Text- + maskierten HTML-Teil). Signatur hängt der Server an. */
export function Composer({ accounts, initial, draftId, originalAttachments = [], onClose }: Props) {
  const { t } = useTranslation("mailbox")
  const c = useCompose(initial, draftId)
  const [showCc, setShowCc] = useState(Boolean(initial.cc || initial.bcc))
  const d = c.draft
  const busy = c.status.kind === "sending"
  const sent = c.status.kind === "sent"
  const reply = d.mode === "reply" || d.mode === "reply_all"

  async function discard() {
    if (!window.confirm(t("compose.confirmDiscard"))) return
    await c.discard()
    onClose(false)
  }

  return (
    <section className="flex h-full min-h-0 flex-col gap-2 rounded-[4px] border border-[#2a364b] bg-[#0b1220] p-3"
      aria-label={t(`compose.${d.mode === "new" ? "new" : d.mode === "reply_all" ? "replyAll" : d.mode}`)} data-mbx-composer="1">
      <header className="flex items-center gap-2">
        <h2 className="flex-1 text-sm font-bold text-[#e8eef8]">
          {t(`compose.${d.mode === "new" ? "new" : d.mode === "reply_all" ? "replyAll" : d.mode}`)}</h2>
        <button type="button" onClick={() => onClose(sent)} aria-label={t("compose.close")}
          className="rounded p-1 text-[#8d9ab0] hover:bg-[#1c2638]"><X size={14} /></button>
      </header>
      <label className="grid grid-cols-[4rem_1fr] items-center gap-2 text-xs text-[#8d9ab0]">{t("compose.from")}
        <select value={d.account_id} onChange={(e) => c.set("account_id", e.target.value)} disabled={reply || sent}
          className={FIELD} data-mbx-from="1">
          {accounts.map((a) => <option key={a.id} value={a.id}>{a.sender_name ? `${a.sender_name} <${a.address}>` : a.address}</option>)}
        </select>
      </label>
      {(["to", ...(showCc ? ["cc", "bcc"] : [])] as const).map((k) => (
        <label key={k} className="grid grid-cols-[4rem_1fr] items-center gap-2 text-xs text-[#8d9ab0]">{t(`compose.${k}`)}
          <input value={d[k as "to" | "cc" | "bcc"]} onChange={(e) => c.set(k as "to", e.target.value)} disabled={sent}
            className={FIELD} data-mbx-field={k} autoComplete="email" />
        </label>
      ))}
      {!showCc && <button type="button" onClick={() => setShowCc(true)} className="self-start text-xs text-[#69d7ff] hover:underline">
        {t("compose.showCc")}</button>}
      <label className="grid grid-cols-[4rem_1fr] items-center gap-2 text-xs text-[#8d9ab0]">{t("compose.subject")}
        <input value={d.subject} onChange={(e) => c.set("subject", e.target.value)} disabled={sent || reply}
          className={FIELD} data-mbx-field="subject" maxLength={998} />
      </label>
      <textarea value={d.body} onChange={(e) => c.set("body", e.target.value)} disabled={sent} aria-label={t("compose.body")}
        className={`${FIELD} min-h-40 flex-1 resize-none font-sans`} data-mbx-field="body" autoFocus />
      {d.mode === "forward" && originalAttachments.length > 0 && (
        <label className="flex items-center gap-2 text-xs text-[#c8d2df]">
          <input type="checkbox" checked={d.with_attachments} onChange={(e) => c.set("with_attachments", e.target.checked)} />
          {t("compose.withOriginal")} <span className="text-[#718097]">({originalAttachments.join(", ")})</span>
        </label>
      )}
      <FileList files={c.files} onRemove={(i) => c.setFiles(c.files.filter((_, j) => j !== i))} />
      <footer className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => void c.send()} disabled={busy || sent} data-mbx-send="1"
          className="inline-flex items-center gap-1 rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1 text-sm font-semibold text-[#69d7ff] disabled:opacity-50">
          <Send size={13} />{busy ? t("compose.sending") : t("compose.send")}</button>
        <label className="inline-flex cursor-pointer items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-xs text-[#c8d2df] hover:bg-[#1c2638]">
          <Paperclip size={12} />{t("compose.attach")}
          <input type="file" multiple className="hidden" disabled={sent} data-mbx-attach="1"
            onChange={(e) => { c.setFiles([...c.files, ...Array.from(e.target.files ?? [])]); e.target.value = "" }} />
        </label>
        {!sent && <button type="button" onClick={() => void discard()} className="inline-flex items-center gap-1 text-xs text-[#8d9ab0] hover:text-rose-300">
          <Trash2 size={12} />{t("compose.discard")}</button>}
        <span className="ml-auto text-[11px] text-[#718097]" data-mbx-saved="1">
          {c.saved && !sent && (c.saved.local ? t("compose.savedLocal") : t("compose.savedAt", { time: c.saved.at }))}</span>
      </footer>
      <StatusLine status={c.status} />
    </section>
  )
}

function FileList({ files, onRemove }: { files: File[]; onRemove: (i: number) => void }) {
  if (files.length === 0) return null
  return (
    <ul className="flex flex-wrap gap-2" data-mbx-files="1">
      {files.map((f, i) => (
        <li key={`${f.name}-${i}`} className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-0.5 text-xs text-[#d7deea]">
          <Paperclip size={11} />{f.name}<span className="text-[#718097]">{size(f.size)}</span>
          <button type="button" onClick={() => onRemove(i)} aria-label="×" className="text-[#8d9ab0] hover:text-rose-300"><X size={11} /></button>
        </li>
      ))}
    </ul>
  )
}

/** Ergebnis als Text – Server-Meldungen (z. B. abgelehnte Adressen) nur als Text, nie als HTML. */
export function StatusLine({ status }: { status: ComposeStatus }) {
  const { t } = useTranslation("mailbox")
  if (status.kind === "idle" || status.kind === "sending") return null
  if (status.kind === "invalid") {
    const key = { size: "compose.tooBig", text: "compose.textTooLong", recipient: "compose.needRecipient" }[status.reason]
    return <p role="alert" className="text-xs text-rose-300">{t(key)}</p>
  }
  if (status.kind === "error") {
    const key = status.code === "rate_limited" ? "compose.rateLimited" : `compose.error.${status.code}`
    return <p role="alert" className="text-xs text-rose-300" data-mbx-error={status.code}>
      {t(key, { defaultValue: t("compose.error.generic") })}</p>
  }
  const r = status.result
  const head = r.sent_copy === "provider" ? "compose.sentProvider" : r.sent_copy === "archive_only" ? "compose.sentArchiveOnly" : "compose.sent"
  return (
    <div role="status" className="space-y-0.5 text-xs" data-mbx-sent={r.sent_copy}>
      <p className={r.sent_copy === "archive_only" ? "text-amber-200" : "text-emerald-300"}>{t(head)}</p>
      {r.refused.length > 0 && <p className="text-amber-200">{t("compose.refused", { list: r.refused.join(", ") })}</p>}
      {r.warning && <p className="text-amber-200">{t("compose.warning", { text: r.warning })}</p>}
    </div>
  )
}
