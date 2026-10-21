import { useTranslation } from "react-i18next"
import { FileText } from "lucide-react"
import type { SavedDraft } from "./api"
import { shortDate } from "./mailFormat"

/** Eigene Entwürfe (lokal gespeichert, mit Kopie im Entwürfe-Ordner des Servers). Nur Text, nie HTML. */
export function DraftList({ drafts, onOpen }: { drafts: SavedDraft[]; onOpen: (d: SavedDraft) => void }) {
  const { t } = useTranslation("mailbox")
  if (drafts.length === 0) return <p className="p-4 text-center text-sm text-[#718097]">{t("drafts.empty")}</p>
  return (
    <ul className="h-full min-h-0 divide-y divide-[#1c2638] overflow-y-auto" aria-label={t("drafts.title")}>
      {drafts.map((d) => (
        <li key={d.id}>
          <button type="button" onClick={() => onOpen(d)} data-mbx-draft={d.id}
            className="block w-full px-3 py-2 text-left hover:bg-[#151c2b]">
            <span className="flex items-center gap-2 text-sm text-[#e8eef8]">
              <FileText size={12} className="shrink-0 text-[#8d9ab0]" />
              <span className="min-w-0 flex-1 truncate">{d.subject || t("drafts.untitled")}</span>
              <span className="shrink-0 text-[11px] text-[#718097]">{shortDate(d.updated_at)}</span>
            </span>
            <span className="block truncate text-xs text-[#8d9ab0]">{d.to || "–"}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
