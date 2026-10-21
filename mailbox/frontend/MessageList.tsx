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
}

/** Mittlere Spalte: Liste der Mails (neueste zuerst). Ungelesene fett. Nur Text, nie HTML. */
export function MessageList({ items, total, selected, onSelect, onMore, showAccount }: Props) {
  if (items.length === 0) {
    return <p className="p-4 text-center text-sm text-[#718097]">Keine Mails</p>
  }
  return (
    <div className="flex h-full min-h-0 flex-col">
      <ul className="min-h-0 flex-1 divide-y divide-[#1c2638] overflow-y-auto">
        {items.map((m) => (
          <li key={m.id}>
            <button type="button" onClick={() => onSelect(m.id)} data-mbx-mail={m.id}
              className={`block w-full px-3 py-2 text-left ${selected === m.id ? "bg-[#1d3a52]" : "hover:bg-[#151c2b]"}`}>
              <span className="flex items-center gap-2">
                <span className={`min-w-0 flex-1 truncate text-sm ${m.seen ? "text-[#c8d2df]" : "font-bold text-[#e8eef8]"}`}>
                  {senderName(m.from_addr)}</span>
                {m.flagged === 1 && <Flag size={12} className="shrink-0 text-amber-300" aria-label="markiert" />}
                {m.has_attachments && <Paperclip size={12} className="shrink-0 text-[#8d9ab0]" aria-label="Anhang" />}
                {m.deleted_on_server === 1 && <Archive size={12} className="shrink-0 text-amber-200" aria-label="nur im Archiv" />}
                <span className="shrink-0 text-[11px] text-[#8d9ab0]">{shortDate(m.date)}</span>
              </span>
              <span className={`block truncate text-sm ${m.seen ? "text-[#aab6c8]" : "font-semibold text-[#d7deea]"}`}>
                {m.subject || "(ohne Betreff)"}</span>
              <span className="block truncate text-xs text-[#718097]">
                {showAccount ? `${m.account} · ` : ""}{m.snippet}</span>
            </button>
          </li>
        ))}
      </ul>
      {items.length < total && (
        <button type="button" onClick={onMore} data-mbx-more="1"
          className="border-t border-[#2a364b] py-2 text-xs text-[#69d7ff] hover:bg-[#151c2b]">
          Weitere laden ({items.length} von {total})</button>
      )}
    </div>
  )
}
