import { foreignStamp } from "../foreign"
import type { T } from "../texts.de"
import type { ForeignIdea } from "../types"

// Herkunftsabzeichen einer fremden Idee: Instanzname, Tooltip „Stand vom …, zuletzt gesehen am …“,
// grau mit „nicht aktuell“, wenn die Idee stale ist (Spec federation-shared-tasks.md §Oberfläche).
export function ForeignBadge({ idea, locale, t }: { idea: ForeignIdea; locale: string; t: T }) {
  const name = idea.origin_name || idea.origin_fp.slice(0, 12)
  const tip = t("foreign_badge_tip", { stand: foreignStamp(idea.updated_at, locale), seen: foreignStamp(idea.origin_last_seen, locale) })
  const color = idea.stale
    ? "border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-innen,36_48_71))] text-[#9aa7bc]"
    : "border-[#69d7ff]/40 bg-[#69d7ff]/10 text-[#9fe6ff]"
  return (
    <span title={tip} data-testid="foreign-badge" data-stale={idea.stale ? "1" : "0"}
      className={`inline-flex items-center gap-1 rounded-[4px] border px-1.5 py-px text-[10px] font-semibold ${color}`}>
      {name}
      {idea.stale && <span>· {t("foreign_stale")}</span>}
    </span>
  )
}
