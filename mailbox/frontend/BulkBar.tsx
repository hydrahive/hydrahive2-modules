import { useTranslation } from "react-i18next"
import { Archive, Flag, Mail, MailOpen, ShieldAlert, Trash2, X } from "lucide-react"
import type { MailAction, MailItem } from "./api"
import { selectionFlags } from "./listLogic"

interface Props {
  items: MailItem[]
  selected: Set<number>
  busy: boolean
  onAct: (action: MailAction) => void
  onClear: () => void
}

const BTN = "inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-0.5 text-xs text-[#c8d2df] hover:bg-[#1c2638] disabled:opacity-40"

/** Leiste über der Liste, sobald Mails angehakt sind (Spec §6: Mehrfachauswahl). Nur-Archiv-Mails zählen nicht. */
export function BulkBar({ items, selected, busy, onAct, onClear }: Props) {
  const { t } = useTranslation("mailbox")
  if (selected.size === 0) return null
  const f = selectionFlags(items, selected)
  const off = busy || f.onServer === 0
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-b border-[#2a364b] bg-[#111a2b] px-2 py-1.5" data-mbx-bulk="1">
      <span className="text-xs font-semibold text-[#e8eef8]">{t("bulk.selected", { n: selected.size })}</span>
      <button type="button" className={BTN} disabled={off} onClick={() => onAct(f.anyUnseen ? "seen" : "unseen")} data-mbx-bulk-act="seen">
        {f.anyUnseen ? <MailOpen size={12} /> : <Mail size={12} />}{t(f.anyUnseen ? "action.markRead" : "action.markUnread")}</button>
      <button type="button" className={BTN} disabled={off} onClick={() => onAct(f.anyUnflagged ? "flag" : "unflag")} data-mbx-bulk-act="flag">
        <Flag size={12} />{t(f.anyUnflagged ? "action.flag" : "action.unflag")}</button>
      <button type="button" className={BTN} disabled={off} onClick={() => onAct("archive")} data-mbx-bulk-act="archive">
        <Archive size={12} />{t("action.archive")}</button>
      <button type="button" className={BTN} disabled={off} onClick={() => onAct("junk")} data-mbx-bulk-act="junk">
        <ShieldAlert size={12} />{t("action.junk")}</button>
      <button type="button" className={`${BTN} hover:text-rose-300`} disabled={off} onClick={() => onAct("delete")} data-mbx-bulk-act="delete">
        <Trash2 size={12} />{t("action.delete")}</button>
      {f.onServer < selected.size && (
        <span className="text-[11px] text-[#718097]">{t("bulk.archiveOnly", { n: selected.size - f.onServer })}</span>)}
      <button type="button" onClick={onClear} aria-label={t("bulk.clear")} className="ml-auto rounded p-0.5 text-[#8d9ab0] hover:bg-[#1c2638]">
        <X size={12} /></button>
    </div>
  )
}
