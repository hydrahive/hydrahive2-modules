import { ChevronDown, ChevronUp, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { moveIndex, type QueueItem } from "./programLogic"
import { BOX, BTN_ICON } from "./ui"

interface Props { items: QueueItem[]; canModerate: boolean; busy: boolean; onMove: (id: number, pos: number) => void; onRemove: (id: number) => void }

/** Warteschlange „Als Nächstes“ – läuft vor dem Programm. Hoch/runter/entfernen per Knopf (geht auch am Handy). */
export function QueueBox({ items, canModerate, busy, onMove, onRemove }: Props) {
  const { t } = useTranslation("radiostream")
  return (
    <section className={BOX} data-radiostream-queue>
      <h3 className="text-sm font-semibold text-[#e8eef8]">{t("queue.heading")}</h3>
      {items.length === 0 ? <p className="text-sm text-[#9aa7bc]">{t("queue.empty")}</p> : (
        <ol className="space-y-1">
          {items.map((q, i) => (
            <li key={q.id} className="flex items-center gap-2 text-sm text-[#c8d2df]">
              <span className="min-w-0 flex-1 break-words">{[q.artist, q.title].filter(Boolean).join(" – ")}</span>
              {canModerate && <>
                <button type="button" className={BTN_ICON} aria-label={`queue.up ${q.title}`} title={t("queue.up")}
                  disabled={busy || moveIndex(items.length, i, -1) === null} onClick={() => onMove(q.id, i - 1)}><ChevronUp size={14} /></button>
                <button type="button" className={BTN_ICON} aria-label={`queue.down ${q.title}`} title={t("queue.down")}
                  disabled={busy || moveIndex(items.length, i, 1) === null} onClick={() => onMove(q.id, i + 1)}><ChevronDown size={14} /></button>
                <button type="button" className={BTN_ICON} aria-label={`queue.remove ${q.title}`} title={t("queue.remove")}
                  disabled={busy} onClick={() => onRemove(q.id)}><X size={14} /></button>
              </>}
            </li>))}
        </ol>)}
      <p className="text-xs text-[#9aa7bc]">{t("queue.hint")}</p>
    </section>
  )
}
