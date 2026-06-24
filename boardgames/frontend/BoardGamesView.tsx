import { useState } from "react"
import { useTranslation } from "react-i18next"
import { moduleIcon } from "@/shared/module-icon"
import { BoardGameOverlay } from "./components/BoardGameOverlay"
import { BOARD_GAMES } from "./games/_registry"
import type { BoardGameModule } from "./types"

/** Brettspiele-Tab: Spielauswahl-Grid. Klick öffnet das Spiel als Overlay. */
export function BoardGamesView() {
  const { t } = useTranslation("boardgames")
  const [active, setActive] = useState<BoardGameModule | null>(null)

  return (
    <div className="p-5 max-w-4xl mx-auto">
      <h2 className="text-base font-semibold text-zinc-200 mb-1">{t("bg_title")}</h2>
      <p className="text-xs text-zinc-500 mb-5">{t("bg_subtitle")}</p>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {BOARD_GAMES.map((g) => {
          const Icon = moduleIcon(g.meta.icon)
          return (
            <button key={g.meta.id} onClick={() => setActive(g)}
              className="group flex flex-col items-center gap-2 rounded-xl border border-white/[8%] bg-white/[3%] p-5 hover:bg-white/[6%] hover:border-white/20 transition-all">
              <span className="flex h-14 w-14 items-center justify-center rounded-lg transition-transform group-hover:scale-110"
                style={{ background: `rgb(${g.meta.accent} / 0.12)`, color: `rgb(${g.meta.accent})` }}>
                <Icon size={28} />
              </span>
              <span className="text-sm font-medium text-zinc-200">{t(g.meta.titleKey)}</span>
            </button>
          )
        })}
      </div>

      {active && <BoardGameOverlay game={active} onClose={() => setActive(null)} />}
    </div>
  )
}
