import { useTranslation } from "react-i18next"
import { Archive, Flag, Paperclip } from "lucide-react"
import type { MailItem } from "./api"
import { senderName, shortDate } from "./mailFormat"

interface Props {
  items: MailItem[]
  total: number
  selected: number | null
  onSelect: (id: number) => void
  onMore: () => void
  showAccount: boolean
  checked?: Set<number>
  onCheck?: (id: number) => void
  onCheckAll?: () => void
}

/** Mittlere Spalte: Liste der Mails (neueste zuerst). Ungelesene fett. Nur Text, nie HTML. */
export function MessageList({ items, total, selected, onSelect, onMore, showAccount, checked, onCheck, onCheckAll }: Props) {
  const { t } = useTranslation("mailbox")
  if (items.length === 0) {
    return <p className="p-4 text-center text-sm text-[#9aa7bc]">Keine Mails</p>
  }
  return (
    <div className="flex h-full min-h-0 flex-col">
      {onCheckAll && (
        <label className="flex items-center gap-2 border-b border-[rgb(var(--hh-s-rand,28_38_56))] px-3 py-1 text-[11px] text-[#9aa7bc]">
          <input type="checkbox" checked={items.length > 0 && items.every((m) => checked?.has(m.id))} onChange={onCheckAll}
            data-mbx-check-all="1" aria-label={t("bulk.all")} />{t("bulk.all")}</label>)}
      <ul className="min-h-0 flex-1 divide-y divide-[rgb(var(--hh-s-rand,28_38_56))] overflow-y-auto">
        {items.map((m) => (
          <li key={m.id} className="flex items-start">
            {onCheck && (
              <input type="checkbox" checked={checked?.has(m.id) ?? false} onChange={() => onCheck(m.id)}
                className="ml-2 mt-3 shrink-0" data-mbx-check={m.id} aria-label={t("bulk.one")} />)}
            <button type="button" onClick={() => onSelect(m.id)} data-mbx-mail={m.id}
              className={`block min-w-0 flex-1 px-3 py-2 text-left ${selected === m.id ? "bg-[#1d3a52]" : "hover:bg-[rgb(var(--hh-s-hebung,21_28_43))]"}`}>
              <span className="flex items-center gap-2">
                <span className={`min-w-0 flex-1 truncate text-sm ${m.seen ? "text-[#c8d2df]" : "font-bold text-[#e8eef8]"}`}>
                  {senderName(m.from_addr)}</span>
                {m.flagged === 1 && <Flag size={12} className="shrink-0 text-amber-300" aria-label="markiert" />}
                {m.has_attachments && <Paperclip size={12} className="shrink-0 text-[#9aa7bc]" aria-label="Anhang" />}
                {m.deleted_on_server === 1 && <Archive size={12} className="shrink-0 text-amber-200" aria-label="nur im Archiv" />}
                <span className="shrink-0 text-[11px] text-[#9aa7bc]">{shortDate(m.date)}</span>
              </span>
              <span className={`block truncate text-sm ${m.seen ? "text-[#aab6c8]" : "font-semibold text-[#d7deea]"}`}>
                {m.subject || "(ohne Betreff)"}</span>
              <span className="block truncate text-xs text-[#9aa7bc]">
                {showAccount ? `${m.account} · ` : ""}{m.snippet}</span>
            </button>
          </li>
        ))}
      </ul>
      {items.length < total && (
        <button type="button" onClick={onMore} data-mbx-more="1"
          className="border-t border-[rgb(var(--hh-s-rand,42_54_75))] py-2 text-xs text-[#69d7ff] hover:bg-[rgb(var(--hh-s-hebung,21_28_43))]">
          Weitere laden ({items.length} von {total})</button>
      )}
    </div>
  )
}
