import { Crown } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { moduleIcon } from "@/shared/module-icon"
import { BoardGameOverlay } from "./BoardGameOverlay"
import { BOARD_GAMES } from "../games/_registry"
import type { BoardGameModule } from "../types"

interface Props {
  onPrompt: (text: string) => void
}

/** Buddy-Box: Brettspiel-Liste zum Schnellstart. Klick öffnet Overlay. */
export function BoardGamesBuddyBox(_: Props) {
  const { t } = useTranslation("boardgames")
  const [active, setActive] = useState<BoardGameModule | null>(null)

  return (
    <CollapsibleBox
      boxId="buddy-boardgames"
      icon={<Crown size={14} className="text-amber-300" />}
      title={t("bg_title")}
      color="234 179 8"
      defaultCollapsed={false}
      className="w-60"
      headerRight={<span className="text-[10px] text-zinc-600">{BOARD_GAMES.length}</span>}
    >
      <div className="p-2 space-y-1">
        {BOARD_GAMES.map((g) => {
          const Icon = moduleIcon(g.meta.icon)
          return (
            <button key={g.meta.id} onClick={() => setActive(g)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg border border-white/[6%] hover:border-amber-400/20 hover:bg-amber-400/[4%] text-zinc-300 hover:text-amber-200 transition-all">
              <span style={{ color: `rgb(${g.meta.accent})` }}><Icon size={15} /></span>
              <span className="text-xs">{t(g.meta.titleKey)}</span>
              <span className="ml-auto text-[10px] text-zinc-600">▶</span>
            </button>
          )
        })}
      </div>
      {active && <BoardGameOverlay game={active} onClose={() => setActive(null)} />}
    </CollapsibleBox>
  )
}
