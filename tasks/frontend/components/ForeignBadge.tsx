import { useTranslation } from "react-i18next"
import { formatStamp } from "../foreign"
import type { ForeignTask } from "../types"

// Herkunftsabzeichen einer fremden Zeile: Instanzname, Tooltip „Stand vom …, zuletzt gesehen am …“,
// grau mit „nicht aktuell“, wenn der Eintrag stale ist (Spec federation-shared-tasks.md §Oberfläche).
export function ForeignBadge({ task }: { task: ForeignTask }) {
  const { t, i18n } = useTranslation("tasks")
  const name = task.origin_name || task.origin_fp.slice(0, 12)
  const tip = t("foreign_badge_tip", {
    stand: formatStamp(task.updated_at, i18n.language),
    seen: formatStamp(task.origin_last_seen, i18n.language),
  })
  const color = task.stale
    ? "text-[#9aa7bc] bg-[rgb(var(--hh-s-hebung,27_37_54)/0.4)] border-[rgb(var(--hh-s-rand,42_54_75))]"
    : "text-[#69d7ff] bg-[#69d7ff]/10 border-[#69d7ff]/30"
  return (
    <span
      title={tip}
      data-testid="foreign-badge"
      data-stale={task.stale ? "1" : "0"}
      className={`inline-flex items-center gap-1 px-1 rounded border text-[9px] whitespace-nowrap ${color}`}
    >
      {name}
      {task.stale && <span>· {t("foreign_stale")}</span>}
    </span>
  )
}
