import { Gamepad2 } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { moduleIcon } from "@/shared/module-icon"
import { GameOverlay } from "./GameOverlay"
import { GAMES } from "../games/_registry"
import type { GameModule } from "../types"

interface Props {
  onPrompt: (text: string) => void
}

/** Buddy-Box: kleine Spiele-Liste zum Schnellstart. Klick öffnet Vollbild-Overlay. */
export function MinigamesBuddyBox(_: Props) {
  const { t } = useTranslation("minigames")
  const [active, setActive] = useState<GameModule | null>(null)

  return (
    <CollapsibleBox
      boxId="buddy-minigames"
      icon={<Gamepad2 size={14} className="text-emerald-300" />}
      title={t("mg_title")}
      color="52 211 153"
      defaultCollapsed={false}
      className="w-60"
      headerRight={<span className="text-[10px] text-zinc-600">{GAMES.length}</span>}
    >
      <div className="p-2 space-y-1">
        {GAMES.map((g) => {
          const Icon = moduleIcon(g.meta.icon)
          return (
            <button
              key={g.meta.id}
              onClick={() => setActive(g)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg border border-white/[6%] hover:border-emerald-400/20 hover:bg-emerald-400/[4%] text-zinc-300 hover:text-emerald-200 transition-all"
            >
              <span style={{ color: `rgb(${g.meta.accent})` }}><Icon size={15} /></span>
              <span className="text-xs">{t(g.meta.titleKey)}</span>
              <span className="ml-auto text-[10px] text-zinc-600 group-hover:text-emerald-300">▶</span>
            </button>
          )
        })}
      </div>

      {active && <GameOverlay game={active} onClose={() => setActive(null)} />}
    </CollapsibleBox>
  )
}
