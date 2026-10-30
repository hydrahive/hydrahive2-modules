import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Flag, FolderInput, Forward, Mail, MailOpen, Reply, ReplyAll, Trash2 } from "lucide-react"
import { mailApi, type MailAction, type MailDetail } from "./api"
import { afterActionNote, needsConfirm, type ComposeMode } from "./composeFormat"
import { folderLabel, type FolderRow } from "./mailFormat"

interface Props {
  mail: MailDetail
  folders: FolderRow[]
  onCompose: (mode: Exclude<ComposeMode, "new">) => void
  onChanged: (action: MailAction, note: string | null) => void
}

const BTN = "inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-0.5 text-xs text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,28_38_56))] disabled:opacity-40"

/** Aktionen zur geöffneten Mail. Antworten geht immer (auch aus dem Archiv); Server-Aktionen nur, solange die Mail
 *  noch auf dem Server liegt. Löschen fragt nach und sagt dazu: die Mail bleibt im Archiv. */
export function MessageActions({ mail, folders, onCompose, onChanged }: Props) {
  const { t } = useTranslation("mailbox")
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const onServer = mail.deleted_on_server !== 1
  const targets = folders.filter((f) => f.account_id === mail.account_id && f.gone === 0 && f.id !== mail.folder_id)
  const inTrash = mail.folder_role === "trash"

  async function act(action: MailAction, target?: string) {
    if (needsConfirm(action) && !window.confirm(`${t(inTrash ? "action.deleteForever" : "action.delete")}?\n${t("action.deleteHint")}`)) return
    setBusy(true)
    setNote(null)
    try {
      const r = await mailApi.act([mail.id], action, target)
      setNote(r.skipped ? t("action.skipped", { n: r.skipped }) : null)
      const key = afterActionNote(action, mail.folder_role, r.done)
      if (r.done) onChanged(action, key ? t(key) : null)
    } catch {
      setNote(t("action.failed"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5" data-mbx-actions="1">
      <button type="button" className={BTN} onClick={() => onCompose("reply")} data-mbx-reply="reply"><Reply size={12} />{t("compose.reply")}</button>
      <button type="button" className={BTN} onClick={() => onCompose("reply_all")} data-mbx-reply="reply_all"><ReplyAll size={12} />{t("compose.replyAll")}</button>
      <button type="button" className={BTN} onClick={() => onCompose("forward")} data-mbx-reply="forward"><Forward size={12} />{t("compose.forward")}</button>
      {onServer ? (
        <>
          <span className="mx-1 h-4 w-px bg-[rgb(var(--hh-s-rand,42_54_75))]" />
          <button type="button" className={BTN} disabled={busy} onClick={() => void act(mail.seen ? "unseen" : "seen")} data-mbx-act="seen">
            {mail.seen ? <Mail size={12} /> : <MailOpen size={12} />}{t(mail.seen ? "action.markUnread" : "action.markRead")}</button>
          <button type="button" className={BTN} disabled={busy} onClick={() => void act(mail.flagged ? "unflag" : "flag")} data-mbx-act="flag">
            <Flag size={12} />{t(mail.flagged ? "action.unflag" : "action.flag")}</button>
          {targets.length > 0 && (
            <label className={`${BTN} cursor-pointer`}>
              <FolderInput size={12} />
              <select value="" disabled={busy} aria-label={t("action.move")} data-mbx-act="move"
                onChange={(e) => { if (e.target.value) void act("move", e.target.value) }}
                className="bg-transparent text-xs text-[#c8d2df] outline-none">
                <option value="">{t("action.move")}</option>
                {targets.map((f) => <option key={f.id} value={f.name}>{folderLabel(f)}</option>)}
              </select>
            </label>
          )}
          <button type="button" className={`${BTN} hover:text-rose-300`} disabled={busy} onClick={() => void act("delete")} data-mbx-act="delete">
            <Trash2 size={12} />{t(inTrash ? "action.deleteForever" : "action.delete")}</button>
        </>
      ) : <span className="text-[11px] text-[#9aa7bc]" data-mbx-archive-only="1">{t("action.archiveOnly")}</span>}
      {note && <span role="status" className="text-[11px] text-amber-200">{note}</span>}
    </div>
  )
}
